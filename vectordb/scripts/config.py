"""
论文知识库 RAG 系统配置文件
"""
import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER_DIR = "/home/nvidia/workspace/paper"
VECTORDB_DIR = os.path.join(PAPER_DIR, "vectordb")
CHROMA_DB_PATH = os.path.join(VECTORDB_DIR, "chroma_db")
BM25_INDEX_PATH = os.path.join(VECTORDB_DIR, "bm25_index")
METADATA_PATH = os.path.join(PAPER_DIR, "metadata")
ANALYSES_PATH = os.path.join(PAPER_DIR, "analyses")

# ChromaDB配置
CHROMA_COLLECTION_NAME = "papers"
CHROMA_PERSIST_DIR = CHROMA_DB_PATH

# Embedding配置
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"  # 主选：BGE中文优化 (需网络)
EMBEDDING_DIMENSION = 1024
EMBEDDING_DEVICE = "cuda"  # 使用GPU

# 备选Embedding (Ollama) - 当BGE不可用时使用
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3.6:35b"
OLLAMA_EMBED_MODEL = "nomic-embed-text"  # 专用embedding模型 (768维)
OLLAMA_EMBED_DIMENSION = 768

# 切分策略配置
CHUNK_STRATEGY = {
    "parent_chunk_size": 1500,      # 父块：返回完整上下文
    "child_chunk_size": 400,        # 子块：精准检索
    "overlap": 50,                  # 重叠防止语义断裂
    "separators": ["\n\n", "\n", "。", "；", "，", " "],  # 中文优先
}

# 检索配置
RETRIEVAL_CONFIG = {
    "vector_top_k": 20,             # 向量检索返回数量
    "bm25_top_k": 20,               # BM25检索返回数量
    "final_top_k": 10,              # 最终融合返回数量
    "similarity_threshold": 0.75,   # 相似度阈值
    "rrf_k": 60,                    # RRF融合参数
}

# 审计配置
AUDIT_CONFIG = {
    "log_dir": os.path.join(PAPER_DIR, "audit_logs"),
    "log_format": "json",
    "log_level": "INFO",
    "enable_query_logging": True,
    "enable_response_logging": True,
}

# 元数据字段定义
METADATA_FIELDS = [
    "category",         # 论文分类
    "priority",         # 优先级：critical/high/medium/low
    "arxiv_id",         # arXiv编号
    "paper_title",      # 论文标题
    "keywords",         # 关键词列表
    "chunk_type",       # 切分类型：summary/insight/formula/code/section
    "parent_id",        # 关联父块ID
    "section_title",    # 章节标题
    "page_number",      # 页码
    "source_file",      # 原始PDF文件名
    "created_at",       # 创建时间
]

# 评估指标基准值
EVALUATION_THRESHOLDS = {
    "precision_at_5": 0.80,
    "recall_at_5": 0.70,
    "mrr": 0.85,
    "hallucination_rate": 0.05,     # 幻觉率上限
    "fidelity_score": 0.90,         # 忠诚度下限
    "response_time_ms": 2000,       # 响应时间上限
}

# 提示词模板路径
PROMPT_TEMPLATES_PATH = os.path.join(METADATA_PATH, "prompt_templates.md")