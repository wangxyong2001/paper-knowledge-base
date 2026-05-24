"""
初始化 ChromaDB 向量数据库
"""
import chromadb
from chromadb.config import Settings
from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL

def init_chroma_db():
    """初始化ChromaDB数据库"""
    print(f"初始化 ChromaDB...")
    print(f"存储路径: {CHROMA_PERSIST_DIR}")
    print(f"Collection名称: {CHROMA_COLLECTION_NAME}")

    # 创建ChromaDB客户端
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # 创建collection (如果已存在则获取)
    try:
        collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
        print(f"Collection '{CHROMA_COLLECTION_NAME}' 已存在")
        print(f"当前文档数: {collection.count()}")
    except Exception:
        # 使用默认embedding函数 (后续会替换为BGE)
        collection = client.create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"description": "论文知识库向量索引"}
        )
        print(f"Collection '{CHROMA_COLLECTION_NAME}' 已创建")

    return client, collection

def verify_embedding_model():
    """验证BGE embedding模型是否可用"""
    print(f"\n验证 Embedding 模型: {EMBEDDING_MODEL}")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)
        test_text = "这是一个测试句子"
        embedding = model.encode(test_text)
        print(f"✓ 模型加载成功")
        print(f"✓ Embedding维度: {len(embedding)}")
        print(f"✓ 测试向量生成成功")
        return True
    except Exception as e:
        print(f"✗ 模型加载失败: {e}")
        print(f"将使用Ollama作为备选方案")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("论文知识库 RAG 系统 - 向量数据库初始化")
    print("=" * 60)

    # 初始化ChromaDB
    client, collection = init_chroma_db()

    # 验证Embedding模型
    embedding_available = verify_embedding_model()

    print("\n" + "=" * 60)
    print("初始化完成!")
    print("=" * 60)

    if embedding_available:
        print("状态: ✓ BGE Embedding可用")
    else:
        print("状态: ⚠ 将使用Ollama备选")

    return client, collection

if __name__ == "__main__":
    main()