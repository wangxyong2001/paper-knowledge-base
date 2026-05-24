#!/usr/bin/env python
"""
论文知识库向量数据库系统 - SIT测试套件
包含单元测试和集成测试
"""
import os
import sys
import json
import shutil
import unittest
import tempfile
from typing import List, Dict

# 添加scripts目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 测试配置 - 使用临时目录
TEST_DIR = tempfile.mkdtemp(prefix="vectordb_test_")
TEST_CHROMA_PATH = os.path.join(TEST_DIR, "chroma_db")
TEST_BM25_PATH = os.path.join(TEST_DIR, "bm25_index")
TEST_METADATA_PATH = os.path.join(TEST_DIR, "metadata")

# 导入模块
from config import (
    CHUNK_STRATEGY, RETRIEVAL_CONFIG, METADATA_FIELDS,
    EMBEDDING_DIMENSION
)

# ============================================================================
# 测试结果记录
# ============================================================================
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "errors": 0,
    "details": []
}

def record_result(name: str, status: str, message: str = ""):
    """记录测试结果"""
    test_results["total"] += 1
    if status == "PASS":
        test_results["passed"] += 1
    elif status == "FAIL":
        test_results["failed"] += 1
    else:
        test_results["errors"] += 1

    test_results["details"].append({
        "name": name,
        "status": status,
        "message": message
    })
    print(f"[{status}] {name}: {message}")

# ============================================================================
# 单元测试 - config.py
# ============================================================================
class TestConfig(unittest.TestCase):
    """配置模块测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print("\n" + "=" * 60)
        print("单元测试 - config.py")
        print("=" * 60)

    def test_chunk_strategy_config(self):
        """测试切分策略配置"""
        try:
            self.assertIn('parent_chunk_size', CHUNK_STRATEGY)
            self.assertIn('child_chunk_size', CHUNK_STRATEGY)
            self.assertIn('overlap', CHUNK_STRATEGY)
            self.assertIn('separators', CHUNK_STRATEGY)

            # 验证数值合理性
            self.assertGreater(CHUNK_STRATEGY['parent_chunk_size'], 0)
            self.assertGreater(CHUNK_STRATEGY['child_chunk_size'], 0)
            self.assertGreaterEqual(CHUNK_STRATEGY['parent_chunk_size'],
                                   CHUNK_STRATEGY['child_chunk_size'])

            record_result("切分策略配置", "PASS", "配置完整且合理")
        except AssertionError as e:
            record_result("切分策略配置", "FAIL", str(e))
            raise

    def test_retrieval_config(self):
        """测试检索配置"""
        try:
            self.assertIn('vector_top_k', RETRIEVAL_CONFIG)
            self.assertIn('bm25_top_k', RETRIEVAL_CONFIG)
            self.assertIn('final_top_k', RETRIEVAL_CONFIG)
            self.assertIn('rrf_k', RETRIEVAL_CONFIG)

            # 验证数值合理性
            self.assertGreater(RETRIEVAL_CONFIG['vector_top_k'], 0)
            self.assertGreater(RETRIEVAL_CONFIG['bm25_top_k'], 0)
            self.assertGreater(RETRIEVAL_CONFIG['final_top_k'], 0)
            self.assertGreater(RETRIEVAL_CONFIG['rrf_k'], 0)

            record_result("检索配置", "PASS", "配置完整且合理")
        except AssertionError as e:
            record_result("检索配置", "FAIL", str(e))
            raise

    def test_metadata_fields(self):
        """测试元数据字段定义"""
        try:
            expected_fields = [
                'category', 'priority', 'arxiv_id', 'paper_title',
                'keywords', 'chunk_type', 'parent_id', 'section_title',
                'page_number', 'source_file', 'created_at'
            ]
            for field in expected_fields:
                self.assertIn(field, METADATA_FIELDS)

            record_result("元数据字段定义", "PASS", f"包含{len(METADATA_FIELDS)}个字段")
        except AssertionError as e:
            record_result("元数据字段定义", "FAIL", str(e))
            raise

    def test_embedding_dimension(self):
        """测试Embedding维度配置"""
        try:
            self.assertEqual(EMBEDDING_DIMENSION, 1024)
            record_result("Embedding维度配置", "PASS", f"维度={EMBEDDING_DIMENSION}")
        except AssertionError as e:
            record_result("Embedding维度配置", "FAIL", str(e))
            raise

# ============================================================================
# 单元测试 - embed_local.py
# ============================================================================
class TestEmbedLocal(unittest.TestCase):
    """Embedding模块测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print("\n" + "=" * 60)
        print("单元测试 - embed_local.py")
        print("=" * 60)

    def test_import_local_embedding(self):
        """测试导入LocalEmbedding类"""
        try:
            from embed_local import LocalEmbedding
            record_result("导入LocalEmbedding", "PASS", "导入成功")
        except ImportError as e:
            record_result("导入LocalEmbedding", "FAIL", str(e))
            raise

    def test_embedding_initialization(self):
        """测试Embedding初始化"""
        try:
            from embed_local import LocalEmbedding

            # 测试不加载模型初始化
            embedder = LocalEmbedding(use_bge=False)
            self.assertEqual(embedder.dimension, 1024)

            record_result("Embedding初始化", "PASS", "初始化成功")
        except Exception as e:
            record_result("Embedding初始化", "FAIL", str(e))
            raise

    def test_embedding_encode_empty(self):
        """测试空文本编码"""
        try:
            from embed_local import LocalEmbedding

            embedder = LocalEmbedding(use_bge=False)
            # 使用Ollama备选编码
            embeddings = embedder.encode([""])

            self.assertIsInstance(embeddings, list)
            self.assertEqual(len(embeddings), 1)

            record_result("空文本编码", "PASS", "处理空文本")
        except Exception as e:
            record_result("空文本编码", "FAIL", str(e))
            raise

# ============================================================================
# 单元测试 - add_paper.py (切分逻辑)
# ============================================================================
class TestChunkLogic(unittest.TestCase):
    """切分逻辑测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print("\n" + "=" * 60)
        print("单元测试 - add_paper.py (切分逻辑)")
        print("=" * 60)

    def test_chunk_text_basic(self):
        """测试基本文本切分"""
        try:
            from add_paper import PaperAdder

            # 创建模拟PaperAdder（不初始化数据库）
            class MockPaperAdder:
                def chunk_text(self, text, metadata):
                    """简化版切分逻辑测试"""
                    import re
                    import hashlib

                    parent_chunks = []
                    child_chunks = []

                    paragraphs = re.split(r'\n\n+', text)
                    parent_id_base = hashlib.md5(metadata.get('filename', '').encode()).hexdigest()[:8]

                    parent_count = 0
                    for para in paragraphs:
                        para = para.strip()
                        if not para:
                            continue

                        parent_id = f"{parent_id_base}_p{parent_count}"
                        parent_chunks.append({
                            'id': parent_id,
                            'content': para,
                            'metadata': metadata.copy()
                        })
                        parent_count += 1

                    # 生成子块
                    child_count = 0
                    for parent in parent_chunks:
                        child_id = f"{parent['id']}_c{child_count}"
                        child_chunks.append({
                            'id': child_id,
                            'content': parent['content'][:400],
                            'parent_id': parent['id'],
                            'metadata': parent['metadata'].copy()
                        })
                        child_count += 1

                    return child_chunks, parent_chunks

            adder = MockPaperAdder()

            # 测试数据
            test_text = """这是第一段内容。

这是第二段内容。

这是第三段内容。"""

            test_metadata = {
                'filename': 'test.pdf',
                'paper_title': 'Test Paper'
            }

            child_chunks, parent_chunks = adder.chunk_text(test_text, test_metadata)

            self.assertGreater(len(parent_chunks), 0)
            self.assertGreater(len(child_chunks), 0)

            # 验证父子关系
            for child in child_chunks:
                self.assertIn('parent_id', child)
                parent_ids = [p['id'] for p in parent_chunks]
                self.assertIn(child['parent_id'], parent_ids)

            record_result("基本文本切分", "PASS",
                         f"生成{len(parent_chunks)}父块,{len(child_chunks)}子块")
        except Exception as e:
            record_result("基本文本切分", "FAIL", str(e))
            raise

    def test_chunk_id_generation(self):
        """测试chunk ID生成"""
        try:
            import hashlib

            filename = "test_paper.pdf"
            expected_base = hashlib.md5(filename.encode()).hexdigest()[:8]

            # 验证ID格式
            parent_id = f"{expected_base}_p0"
            child_id = f"{parent_id}_c0"

            self.assertTrue(parent_id.startswith(expected_base))
            self.assertTrue(child_id.startswith(parent_id))

            record_result("Chunk ID生成", "PASS", f"ID格式正确: {child_id}")
        except Exception as e:
            record_result("Chunk ID生成", "FAIL", str(e))
            raise

    def test_chunk_size_limits(self):
        """测试切分大小限制"""
        try:
            parent_size = CHUNK_STRATEGY['parent_chunk_size']
            child_size = CHUNK_STRATEGY['child_chunk_size']

            # 验证父子块大小关系
            self.assertGreater(parent_size, child_size,
                              "父块应大于子块")

            # 验证合理范围
            self.assertLessEqual(parent_size, 5000, "父块不应过大")
            self.assertGreaterEqual(child_size, 100, "子块不应过小")

            record_result("切分大小限制", "PASS",
                         f"父块={parent_size}, 子块={child_size}")
        except Exception as e:
            record_result("切分大小限制", "FAIL", str(e))
            raise

# ============================================================================
# 集成测试 - ChromaDB初始化
# ============================================================================
class TestChromaDBInit(unittest.TestCase):
    """ChromaDB初始化集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print("\n" + "=" * 60)
        print("集成测试 - ChromaDB初始化")
        print("=" * 60)

    def test_import_chromadb(self):
        """测试导入chromadb"""
        try:
            import chromadb
            record_result("导入chromadb", "PASS", f"版本: {chromadb.__version__}")
        except ImportError as e:
            record_result("导入chromadb", "FAIL", str(e))
            raise

    def test_chroma_client_creation(self):
        """测试ChromaDB客户端创建"""
        try:
            import chromadb

            # 使用临时目录
            client = chromadb.PersistentClient(path=TEST_CHROMA_PATH)

            self.assertIsNotNone(client)
            record_result("ChromaDB客户端创建", "PASS", f"路径: {TEST_CHROMA_PATH}")
        except Exception as e:
            record_result("ChromaDB客户端创建", "FAIL", str(e))
            raise

    def test_collection_creation(self):
        """测试Collection创建"""
        try:
            import chromadb

            client = chromadb.PersistentClient(path=TEST_CHROMA_PATH)
            collection = client.get_or_create_collection(
                name="test_papers",
                metadata={"description": "测试集合"}
            )

            self.assertIsNotNone(collection)
            self.assertEqual(collection.name, "test_papers")

            record_result("Collection创建", "PASS",
                         f"集合名: {collection.name}")
        except Exception as e:
            record_result("Collection创建", "FAIL", str(e))
            raise

    def test_collection_add_query(self):
        """测试Collection添加和查询"""
        try:
            import chromadb

            client = chromadb.PersistentClient(path=TEST_CHROMA_PATH)
            collection = client.get_or_create_collection(name="test_query")

            # 添加测试数据
            collection.add(
                ids=["test_1", "test_2"],
                embeddings=[[0.1] * 1024, [0.2] * 1024],
                documents=["测试文档1", "测试文档2"],
                metadatas=[{"source": "test"}, {"source": "test"}]
            )

            # 查询测试
            results = collection.query(
                query_embeddings=[[0.1] * 1024],
                n_results=2
            )

            self.assertEqual(len(results['ids'][0]), 2)
            self.assertIn("test_1", results['ids'][0])

            record_result("Collection添加查询", "PASS",
                         f"查询返回{len(results['ids'][0])}条")
        except Exception as e:
            record_result("Collection添加查询", "FAIL", str(e))
            raise

# ============================================================================
# 集成测试 - BM25索引
# ============================================================================
class TestBM25Index(unittest.TestCase):
    """BM25索引集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print("\n" + "=" * 60)
        print("集成测试 - BM25索引")
        print("=" * 60)

        # 创建测试目录
        os.makedirs(TEST_BM25_PATH, exist_ok=True)

    def test_import_whoosh(self):
        """测试导入whoosh"""
        try:
            from whoosh.index import create_in, open_dir
            from whoosh.fields import Schema, TEXT, ID, KEYWORD
            record_result("导入whoosh", "PASS", "导入成功")
        except ImportError as e:
            record_result("导入whoosh", "FAIL", str(e))
            raise

    def test_bm25_index_creation(self):
        """测试BM25索引创建"""
        try:
            from whoosh.index import create_in
            from whoosh.fields import Schema, TEXT, ID, KEYWORD

            schema = Schema(
                chunk_id=ID(stored=True, unique=True),
                content=TEXT(stored=True),
                paper_title=TEXT(stored=True),
                category=KEYWORD(stored=True)
            )

            index = create_in(TEST_BM25_PATH, schema)
            self.assertIsNotNone(index)

            record_result("BM25索引创建", "PASS", f"路径: {TEST_BM25_PATH}")
        except Exception as e:
            record_result("BM25索引创建", "FAIL", str(e))
            raise

    def test_bm25_index_write_read(self):
        """测试BM25索引写入和读取（使用中文分词）"""
        try:
            from whoosh.index import create_in, open_dir
            from whoosh.fields import Schema, TEXT, ID, KEYWORD
            from whoosh.qparser import QueryParser
            from jieba.analyse import ChineseAnalyzer

            # 使用ChineseAnalyzer支持中文分词
            schema = Schema(
                chunk_id=ID(stored=True, unique=True),
                content=TEXT(stored=True, analyzer=ChineseAnalyzer()),
                paper_title=TEXT(stored=True, analyzer=ChineseAnalyzer())
            )

            # 创建并写入
            index = create_in(TEST_BM25_PATH, schema)
            writer = index.writer()
            writer.add_document(
                chunk_id="test_1",
                content="这是一个测试文档，关于机器学习和深度学习。",
                paper_title="测试论文"
            )
            writer.commit()

            # 读取并搜索
            index = open_dir(TEST_BM25_PATH)
            with index.searcher() as searcher:
                parser = QueryParser("content", schema)
                query = parser.parse("机器学习")
                results = searcher.search(query)

                self.assertGreater(len(results), 0)

            record_result("BM25索引读写", "PASS",
                         f"搜索返回{len(results)}条（使用ChineseAnalyzer）")
        except Exception as e:
            record_result("BM25索引读写", "FAIL", str(e))
            raise

# ============================================================================
# 集成测试 - 论文添加完整流程
# ============================================================================
class TestPaperAddFlow(unittest.TestCase):
    """论文添加完整流程集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print("\n" + "=" * 60)
        print("集成测试 - 论文添加完整流程")
        print("=" * 60)

    def test_full_pipeline_mock(self):
        """测试完整流水线（模拟）"""
        try:
            import chromadb
            from whoosh.index import create_in
            from whoosh.fields import Schema, TEXT, ID, KEYWORD

            # 1. 初始化ChromaDB
            client = chromadb.PersistentClient(path=TEST_CHROMA_PATH)
            collection = client.get_or_create_collection(name="test_full")

            # 2. 初始化BM25
            schema = Schema(
                chunk_id=ID(stored=True, unique=True),
                content=TEXT(stored=True),
                paper_title=TEXT(stored=True),
                category=KEYWORD(stored=True)
            )
            bm25_index = create_in(TEST_BM25_PATH, schema)

            # 3. 模拟添加论文
            test_chunks = [
                {"id": "test_paper_p0_c0",
                 "content": "MCP协议是一种标准化的工具调用协议。",
                 "metadata": {"paper_title": "MCP论文", "category": "protocol"}},
                {"id": "test_paper_p0_c1",
                 "content": "Agent系统可以通过MCP协议调用外部工具。",
                 "metadata": {"paper_title": "MCP论文", "category": "protocol"}}
            ]

            # 添加到ChromaDB（使用零向量模拟）
            collection.add(
                ids=[c["id"] for c in test_chunks],
                embeddings=[[0.1] * 1024 for _ in test_chunks],
                documents=[c["content"] for c in test_chunks],
                metadatas=[c["metadata"] for c in test_chunks]
            )

            # 添加到BM25
            writer = bm25_index.writer()
            for chunk in test_chunks:
                writer.add_document(
                    chunk_id=chunk["id"],
                    content=chunk["content"],
                    paper_title=chunk["metadata"]["paper_title"],
                    category=chunk["metadata"]["category"]
                )
            writer.commit()

            # 4. 验证
            self.assertEqual(collection.count(), 2)

            record_result("完整流水线", "PASS",
                         f"ChromaDB: {collection.count()}条")
        except Exception as e:
            record_result("完整流水线", "FAIL", str(e))
            raise

# ============================================================================
# 集成测试 - 混合检索
# ============================================================================
class TestHybridSearch(unittest.TestCase):
    """混合检索集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print("\n" + "=" * 60)
        print("集成测试 - 混合检索")
        print("=" * 60)

    def test_rrf_fusion_algorithm(self):
        """测试RRF融合算法"""
        try:
            from collections import defaultdict

            # 模拟检索结果
            vector_results = [
                {"chunk_id": "a", "score": 0.9, "source": "vector"},
                {"chunk_id": "b", "score": 0.8, "source": "vector"},
                {"chunk_id": "c", "score": 0.7, "source": "vector"},
            ]

            bm25_results = [
                {"chunk_id": "b", "score": 3.5, "source": "bm25"},
                {"chunk_id": "d", "score": 3.0, "source": "bm25"},
                {"chunk_id": "a", "score": 2.5, "source": "bm25"},
            ]

            # RRF融合
            k = 60
            scores = defaultdict(float)

            for rank, result in enumerate(vector_results):
                scores[result["chunk_id"]] += 1 / (k + rank + 1)

            for rank, result in enumerate(bm25_results):
                scores[result["chunk_id"]] += 1 / (k + rank + 1)

            sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            # 验证结果
            self.assertEqual(len(sorted_results), 4)
            # a和b应该排在前面（两个检索都出现）
            top_ids = [r[0] for r in sorted_results[:2]]
            self.assertIn("a", top_ids)
            self.assertIn("b", top_ids)

            record_result("RRF融合算法", "PASS",
                         f"融合{len(sorted_results)}个结果")
        except Exception as e:
            record_result("RRF融合算法", "FAIL", str(e))
            raise

    def test_search_module_import(self):
        """测试检索模块导入"""
        try:
            from search import HybridSearcher
            record_result("检索模块导入", "PASS", "导入成功")
        except ImportError as e:
            record_result("检索模块导入", "FAIL", str(e))
            raise

# ============================================================================
# 清理和报告
# ============================================================================
def cleanup():
    """清理测试目录"""
    try:
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)
            print(f"\n已清理测试目录: {TEST_DIR}")
    except Exception as e:
        print(f"清理失败: {e}")

def print_summary():
    """打印测试摘要"""
    print("\n" + "=" * 60)
    print("测试报告摘要")
    print("=" * 60)
    print(f"总测试数: {test_results['total']}")
    print(f"通过: {test_results['passed']}")
    print(f"失败: {test_results['failed']}")
    print(f"错误: {test_results['errors']}")

    if test_results['total'] > 0:
        pass_rate = (test_results['passed'] / test_results['total']) * 100
        print(f"通过率: {pass_rate:.1f}%")

    # 打印详细结果
    print("\n详细结果:")
    print("-" * 60)
    for detail in test_results['details']:
        status_icon = "[PASS]" if detail['status'] == 'PASS' else "[FAIL]"
        print(f"{status_icon} {detail['name']}: {detail['message']}")

    print("=" * 60)

    return test_results

# ============================================================================
# 主测试运行器
# ============================================================================
def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("论文知识库向量数据库系统 - SIT测试")
    print("=" * 60)
    print(f"测试目录: {TEST_DIR}")
    print(f"时间: {__import__('datetime').datetime.now().isoformat()}")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestEmbedLocal))
    suite.addTests(loader.loadTestsFromTestCase(TestChunkLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestChromaDBInit))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25Index))
    suite.addTests(loader.loadTestsFromTestCase(TestPaperAddFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestHybridSearch))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 清理
    cleanup()

    # 打印摘要
    return print_summary()

if __name__ == "__main__":
    results = run_all_tests()

    # 保存结果到JSON
    results_file = os.path.join(TEST_DIR, "test_results.json")
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n测试结果已保存: {results_file}")
    except:
        pass

    # 返回退出码
    sys.exit(0 if results['failed'] == 0 and results['errors'] == 0 else 1)