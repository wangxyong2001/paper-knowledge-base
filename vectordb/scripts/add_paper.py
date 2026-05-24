"""
添加论文到向量数据库
支持父子切分策略
"""
import os
import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Tuple

# 导入本地模块
from config import (
    ANALYSES_PATH, METADATA_PATH, CHUNK_STRATEGY,
    CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR,
    BM25_INDEX_PATH, METADATA_FIELDS
)
from embed_local import LocalEmbedding

import chromadb
from chromadb.config import Settings
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, KEYWORD
from whoosh.qparser import QueryParser

class PaperAdder:
    """论文添加器"""

    def __init__(self, use_bge: bool = True):
        # 初始化ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.collection = self.chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME
        )

        # 初始化Embedding
        self.embedder = LocalEmbedding(use_bge=use_bge)

        # 初始化BM25索引
        self._init_bm25_index()

    def _init_bm25_index(self):
        """初始化Whoosh BM25索引（使用中文分词）"""
        if not os.path.exists(BM25_INDEX_PATH):
            os.makedirs(BM25_INDEX_PATH)

        # 使用ChineseAnalyzer支持中文分词
        try:
            from jieba.analyse import ChineseAnalyzer
            analyzer = ChineseAnalyzer()
        except ImportError:
            # 如果jieba未安装，使用默认分词器（功能受限）
            analyzer = None

        if analyzer:
            schema = Schema(
                chunk_id=ID(stored=True, unique=True),
                content=TEXT(stored=True, analyzer=analyzer),
                paper_title=TEXT(stored=True, analyzer=analyzer),
                category=KEYWORD(stored=True),
                keywords=KEYWORD(stored=True)
            )
        else:
            schema = Schema(
                chunk_id=ID(stored=True, unique=True),
                content=TEXT(stored=True),
                paper_title=TEXT(stored=True),
                category=KEYWORD(stored=True),
                keywords=KEYWORD(stored=True)
            )

        try:
            self.bm25_index = open_dir(BM25_INDEX_PATH)
        except:
            self.bm25_index = create_in(BM25_INDEX_PATH, schema)

    def chunk_text(self, text: str, paper_metadata: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        文本切分 - 父子切分策略
        返回: (child_chunks, parent_chunks)
        """
        parent_chunks = []
        child_chunks = []

        # 按段落分割
        paragraphs = re.split(r'\n\n+', text)

        parent_id_base = hashlib.md5(paper_metadata.get('filename', '').encode()).hexdigest()[:8]

        # 合并段落为父块
        current_parent = ""
        parent_count = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果当前父块超过大小限制，保存并开始新的父块
            if len(current_parent) > CHUNK_STRATEGY['parent_chunk_size']:
                parent_id = f"{parent_id_base}_p{parent_count}"
                parent_chunks.append({
                    'id': parent_id,
                    'content': current_parent.strip(),
                    'metadata': paper_metadata.copy()
                })
                parent_count += 1
                current_parent = para + "\n\n"
            else:
                current_parent += para + "\n\n"

        # 保存最后一个父块
        if current_parent.strip():
            parent_id = f"{parent_id_base}_p{parent_count}"
            parent_chunks.append({
                'id': parent_id,
                'content': current_parent.strip(),
                'metadata': paper_metadata.copy()
            })

        # 从父块生成子块
        child_count = 0
        for parent in parent_chunks:
            parent_id = parent['id']
            parent_content = parent['content']

            # 按句子分割生成子块
            sentences = re.split(f'[{"".join(CHUNK_STRATEGY["separators"])}]', parent_content)

            current_child = ""
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue

                if len(current_child) > CHUNK_STRATEGY['child_chunk_size']:
                    child_id = f"{parent_id}_c{child_count}"
                    child_chunks.append({
                        'id': child_id,
                        'content': current_child.strip(),
                        'parent_id': parent_id,
                        'metadata': parent['metadata'].copy()
                    })
                    child_count += 1
                    current_child = sent + " "
                else:
                    current_child += sent + " "

            # 保存最后一个子块
            if current_child.strip():
                child_id = f"{parent_id}_c{child_count}"
                child_chunks.append({
                    'id': child_id,
                    'content': current_child.strip(),
                    'parent_id': parent_id,
                    'metadata': parent['metadata'].copy()
                })

        return child_chunks, parent_chunks

    def add_to_chroma(self, chunks: List[Dict]):
        """添加到ChromaDB向量库"""
        if not chunks:
            return

        ids = [c['id'] for c in chunks]
        contents = [c['content'] for c in chunks]
        metadatas = [c['metadata'] for c in chunks]

        # 生成向量
        embeddings = self.embedder.encode(contents)

        # 添加到ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )

        print(f"✓ 已添加 {len(chunks)} 个chunk到ChromaDB")

    def add_to_bm25(self, chunks: List[Dict]):
        """添加到BM25索引"""
        from whoosh.writing import AsyncWriter

        writer = AsyncWriter(self.bm25_index)
        for chunk in chunks:
            writer.add_document(
                chunk_id=chunk['id'],
                content=chunk['content'],
                paper_title=chunk['metadata'].get('paper_title', ''),
                category=chunk['metadata'].get('category', ''),
                keywords=','.join(chunk['metadata'].get('keywords', []))
            )
        writer.commit()

        print(f"✓ 已添加 {len(chunks)} 个chunk到BM25索引")

    def add_paper(self, paper_metadata: Dict, analysis_content: str):
        """添加单篇论文"""
        print(f"\n处理论文: {paper_metadata.get('filename', '')}")

        # 切分文本
        child_chunks, parent_chunks = self.chunk_text(analysis_content, paper_metadata)
        print(f"生成 {len(child_chunks)} 个子块, {len(parent_chunks)} 个父块")

        # 添加子块到向量库 (用于检索)
        self.add_to_chroma(child_chunks)

        # 添加子块到BM25 (用于关键词检索)
        self.add_to_bm25(child_chunks)

        # 保存父块关系 (用于返回完整上下文)
        self._save_parent_chunks(parent_chunks, paper_metadata)

        return len(child_chunks), len(parent_chunks)

    def _save_parent_chunks(self, parent_chunks: List[Dict], paper_metadata: Dict):
        """保存父块到文件"""
        parent_file = os.path.join(
            METADATA_PATH,
            f"parent_chunks_{paper_metadata.get('arxiv_id', paper_metadata.get('filename', 'unknown'))}.json"
        )
        with open(parent_file, 'w', encoding='utf-8') as f:
            json.dump(parent_chunks, f, ensure_ascii=False, indent=2)
        print(f"✓ 父块关系已保存")

def load_paper_index():
    """加载论文分类索引"""
    index_file = os.path.join(METADATA_PATH, "paper_index.json")
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_paper_metadata(paper_index: Dict, category_key: str, paper_filename: str) -> Dict:
    """从索引获取论文元数据"""
    for paper in paper_index['categories'][category_key]['papers']:
        if paper['filename'] == paper_filename:
            return paper
    return {}

def main():
    """主函数 - 批量添加论文"""
    print("=" * 60)
    print("论文知识库 - 批量添加论文到向量库")
    print("=" * 60)

    # 加载论文索引
    paper_index = load_paper_index()
    if not paper_index:
        print("✗ 未找到论文索引文件")
        return

    # 初始化添加器
    adder = PaperAdder(use_bge=False)  # 使用Ollama embedding (网络稳定性优先)

    # 遍历analyses目录
    if not os.path.exists(ANALYSES_PATH):
        print(f"⚠ analyses目录不存在，请先运行Paper Agent生成解读文章")
        os.makedirs(ANALYSES_PATH)
        return

    total_child_chunks = 0
    total_parent_chunks = 0
    papers_added = 0

    for analysis_file in os.listdir(ANALYSES_PATH):
        if not analysis_file.endswith('.md'):
            continue

        # 解析文件名获取论文信息
        paper_name = analysis_file.replace('-解读.md', '')

        # 读取解读内容
        analysis_path = os.path.join(ANALYSES_PATH, analysis_file)
        with open(analysis_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 构建元数据 (从索引中查找)
        paper_metadata = {
            'filename': paper_name + '.pdf',
            'paper_title': paper_name,
            'arxiv_id': '',
            'category': 'unknown',
            'priority': 'medium',
            'keywords': ['transformer'],  # ChromaDB不接受空列表，添加默认关键词
            'created_at': datetime.now().isoformat()
        }

        # 添加论文
        child_count, parent_count = adder.add_paper(paper_metadata, content)
        total_child_chunks += child_count
        total_parent_chunks += parent_count
        papers_added += 1

    print("\n" + "=" * 60)
    print("批量添加完成!")
    print("=" * 60)
    print(f"论文数量: {papers_added}")
    print(f"子块总数: {total_child_chunks}")
    print(f"父块总数: {total_parent_chunks}")
    print(f"向量库文档数: {adder.collection.count()}")

if __name__ == "__main__":
    main()