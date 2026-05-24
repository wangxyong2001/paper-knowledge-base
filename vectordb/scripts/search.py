"""
混合检索实现
向量检索 + BM25检索 + RRF融合
"""
import os
import json
from typing import List, Dict, Tuple
from collections import defaultdict

# 导入本地模块
from config import (
    CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR,
    BM25_INDEX_PATH, RETRIEVAL_CONFIG, ANALYSES_PATH, METADATA_PATH
)
from embed_local import LocalEmbedding

import chromadb
from whoosh.index import open_dir
from whoosh.qparser import QueryParser, MultifieldParser

class HybridSearcher:
    """混合检索器"""

    def __init__(self, use_bge: bool = True):
        # 初始化ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.collection = self.chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME
        )

        # 初始化Embedding
        self.embedder = LocalEmbedding(use_bge=use_bge)

        # 初始化BM25索引
        try:
            self.bm25_index = open_dir(BM25_INDEX_PATH)
        except:
            print(f"⚠ BM25索引未找到，请先运行add_paper.py")
            self.bm25_index = None

    def vector_search(self, query: str, top_k: int = None) -> List[Dict]:
        """向量检索"""
        top_k = top_k or RETRIEVAL_CONFIG['vector_top_k']

        # 生成查询向量
        query_embedding = self.embedder.encode([query])[0]

        # ChromaDB检索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )

        # 格式化结果
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    'chunk_id': chunk_id,
                    'content': results['documents'][0][i] if results['documents'] else '',
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'score': 1 - results['distances'][0][i] if results['distances'] else 0,  # 转换为相似度
                    'source': 'vector'
                })

        return formatted_results

    def bm25_search(self, query: str, top_k: int = None) -> List[Dict]:
        """BM25关键词检索"""
        if not self.bm25_index:
            return []

        top_k = top_k or RETRIEVAL_CONFIG['bm25_top_k']

        with self.bm25_index.searcher() as searcher:
            parser = MultifieldParser(["content", "paper_title"], self.bm25_index.schema)
            query_obj = parser.parse(query)
            results = searcher.search(query_obj, limit=top_k)

            formatted_results = []
            for hit in results:
                formatted_results.append({
                    'chunk_id': hit['chunk_id'],
                    'content': hit['content'],
                    'metadata': {
                        'paper_title': hit.get('paper_title', ''),
                        'category': hit.get('category', ''),
                    },
                    'score': hit.score,
                    'source': 'bm25'
                })

            return formatted_results

    def rrf_fusion(self, vector_results: List[Dict], bm25_results: List[Dict]) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法
        """
        k = RETRIEVAL_CONFIG['rrf_k']

        # 计算每个chunk的RRF分数
        scores = defaultdict(float)
        chunk_data = {}

        # 向量检索排名
        for rank, result in enumerate(vector_results):
            chunk_id = result['chunk_id']
            scores[chunk_id] += 1 / (k + rank + 1)
            chunk_data[chunk_id] = result

        # BM25检索排名
        for rank, result in enumerate(bm25_results):
            chunk_id = result['chunk_id']
            scores[chunk_id] += 1 / (k + rank + 1)
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = result

        # 按RRF分数排序
        sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # 格式化最终结果
        final_results = []
        for chunk_id, rrf_score in sorted_chunks[:RETRIEVAL_CONFIG['final_top_k']]:
            result = chunk_data[chunk_id].copy()
            result['rrf_score'] = rrf_score
            result['source'] = 'hybrid'
            final_results.append(result)

        return final_results

    def get_parent_context(self, chunk_id: str) -> str:
        """获取父块完整上下文"""
        # 从chunk_id提取parent_id
        parts = chunk_id.split('_')
        parent_id = parts[0] + '_' + parts[1] if len(parts) > 2 else chunk_id

        # 查找父块文件
        for filename in os.listdir(METADATA_PATH):
            if filename.startswith('parent_chunks_') and filename.endswith('.json'):
                parent_file = os.path.join(METADATA_PATH, filename)
                with open(parent_file, 'r', encoding='utf-8') as f:
                    parent_chunks = json.load(f)
                    for parent in parent_chunks:
                        if parent['id'] == parent_id:
                            return parent['content']

        return ""

    def search(self, query: str, top_k: int = None) -> Dict:
        """
        混合检索主函数
        返回: {
            'results': 检索结果列表,
            'query': 查询文本,
            'stats': 检索统计
        }
        """
        top_k = top_k or RETRIEVAL_CONFIG['final_top_k']

        # Step 1: 向量检索
        vector_results = self.vector_search(query)

        # Step 2: BM25检索
        bm25_results = self.bm25_search(query)

        # Step 3: RRF融合
        hybrid_results = self.rrf_fusion(vector_results, bm25_results)

        # Step 4: 扩展父块上下文
        for result in hybrid_results:
            parent_id = result['metadata'].get('parent_id', '')
            if parent_id:
                result['parent_context'] = self.get_parent_context(result['chunk_id'])

        return {
            'results': hybrid_results[:top_k],
            'query': query,
            'stats': {
                'vector_count': len(vector_results),
                'bm25_count': len(bm25_results),
                'hybrid_count': len(hybrid_results)
            }
        }

def main():
    """测试检索"""
    print("=" * 60)
    print("论文知识库 - 混合检索测试")
    print("=" * 60)

    searcher = HybridSearcher(use_bge=True)

    # 测试查询
    test_queries = [
        "MCP协议是什么?",
        "如何实现Agent的工具调用?",
        "DeepSeek的MoE架构有什么特点?",
        "什么是混合检索?"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 40)

        result = searcher.search(query)

        print(f"向量检索: {result['stats']['vector_count']} 条")
        print(f"BM25检索: {result['stats']['bm25_count']} 条")
        print(f"融合结果: {result['stats']['hybrid_count']} 条")

        for i, item in enumerate(result['results'][:3]):
            print(f"\n[{i+1}] chunk_id: {item['chunk_id']}")
            print(f"    RRF分数: {item['rrf_score']:.4f}")
            print(f"    内容片段: {item['content'][:100]}...")

if __name__ == "__main__":
    main()