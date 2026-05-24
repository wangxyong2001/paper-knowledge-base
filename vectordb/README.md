# 论文知识库向量数据库系统

> 高效的学术论文检索系统，基于混合检索架构（向量检索 + BM25 + RRF融合）

## 系统概述

本系统是一个专为学术论文设计的知识库检索系统，核心特性包括：

- **混合检索架构**: 结合向量语义检索与BM25关键词检索，通过RRF算法融合
- **父子切分策略**: 小块精准检索，大块返回完整上下文
- **多模型支持**: BGE-large-zh主选，Ollama备选
- **本地化部署**: 支持完全离线运行，数据安全可控

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                    Paper RAG Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ PDF Papers  │ -> │  Analysis   │ -> │  Chunking   │     │
│  │  (输入层)   │    │  (解读层)   │    │  (切分层)   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                              │              │
│                                              ▼              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Storage Layer                     │   │
│  ├─────────────────────┬───────────────────────────────┤   │
│  │   ChromaDB (向量)   │    Whoosh (BM25)              │   │
│  │   - 子块向量索引    │    - 关键词倒排索引            │   │
│  │   - 语义相似度检索  │    - 精确匹配检索              │   │
│  └─────────────────────┴───────────────────────────────┘   │
│                                              │              │
│                                              ▼              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Retrieval Layer                     │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  1. Vector Search (向量检索)                         │   │
│  │  2. BM25 Search (关键词检索)                         │   │
│  │  3. RRF Fusion (结果融合)                            │   │
│  │  4. Parent Context (上下文扩展)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                              │              │
│                                              ▼              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Output Layer                      │   │
│  │  - 相似度排序结果                                    │   │
│  │  - 完整父块上下文                                    │   │
│  │  - 元数据 (来源、页码、分类等)                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 安装步骤

### 1. 系统要求

- Python 3.10+
- CUDA 11.0+ (GPU加速)
- 8GB+ RAM (推荐16GB)
- 10GB+ 磁盘空间 (模型存储)

### 2. 创建虚拟环境

```bash
cd /home/nvidia/workspace/paper/vectordb
python -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install chromadb sentence-transformers whoosh requests torch jieba
```

**注意**: `jieba` 是中文分词库，BM25检索功能需要它来支持中文关键词搜索。

### 4. 下载BGE模型

首次运行时，系统会自动下载BGE-large-zh模型（约1.3GB）：

```bash
# 预下载模型（可选，首次运行会自动下载）
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-zh-v1.5')"
```

### 5. 初始化数据库

```bash
cd scripts
python init_db.py
```

## 使用指南

### 快速开始

```python
# 1. 初始化数据库
from init_db import init_chroma_db
client, collection = init_chroma_db()

# 2. 添加论文
from add_paper import PaperAdder
adder = PaperAdder(use_bge=True)

paper_metadata = {
    'filename': 'example.pdf',
    'paper_title': 'Example Paper',
    'arxiv_id': '2301.12345',
    'category': 'ai',
    'keywords': ['machine learning', 'deep learning']
}

with open('analysis.md', 'r') as f:
    content = f.read()

adder.add_paper(paper_metadata, content)

# 3. 检索论文
from search import HybridSearcher
searcher = HybridSearcher(use_bge=True)

results = searcher.search("什么是MCP协议?")
for item in results['results'][:5]:
    print(f"分数: {item['rrf_score']:.4f}")
    print(f"内容: {item['content'][:100]}...")
```

### 命令行使用

```bash
# 初始化向量数据库
python scripts/init_db.py

# 批量添加论文（从analyses目录）
python scripts/add_paper.py

# 测试检索
python scripts/search.py
```

## API文档

### config.py - 系统配置

#### 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `BASE_DIR` | str | 项目根目录 | 基础路径 |
| `CHROMA_DB_PATH` | str | `vectordb/chroma_db` | ChromaDB存储路径 |
| `BM25_INDEX_PATH` | str | `vectordb/bm25_index` | BM25索引路径 |
| `CHROMA_COLLECTION_NAME` | str | `"papers"` | ChromaDB集合名称 |
| `EMBEDDING_MODEL` | str | `"BAAI/bge-large-zh-v1.5"` | 主选Embedding模型 |
| `EMBEDDING_DIMENSION` | int | `1024` | 向量维度 |
| `EMBEDDING_DEVICE` | str | `"cuda"` | 计算设备 |

#### 切分策略配置

```python
CHUNK_STRATEGY = {
    "parent_chunk_size": 1500,  # 父块大小（字符）
    "child_chunk_size": 400,    # 子块大小（字符）
    "overlap": 50,              # 重叠字符数
    "separators": ["\n\n", "\n", "。", "；", "，", " "]
}
```

#### 检索配置

```python
RETRIEVAL_CONFIG = {
    "vector_top_k": 20,         # 向量检索返回数
    "bm25_top_k": 20,           # BM25检索返回数
    "final_top_k": 10,          # 最终融合返回数
    "similarity_threshold": 0.75,
    "rrf_k": 60                 # RRF融合参数
}
```

---

### init_db.py - 数据库初始化

#### `init_chroma_db() -> Tuple[Client, Collection]`

初始化ChromaDB数据库。

**返回值**:
- `client`: ChromaDB客户端实例
- `collection`: Collection实例

**示例**:
```python
from init_db import init_chroma_db
client, collection = init_chroma_db()
print(f"当前文档数: {collection.count()}")
```

#### `verify_embedding_model() -> bool`

验证BGE Embedding模型是否可用。

**返回值**:
- `True`: 模型加载成功
- `False`: 模型不可用，需使用Ollama备选

---

### embed_local.py - Embedding服务

#### `class LocalEmbedding`

本地Embedding服务封装类。

**初始化参数**:
- `use_bge` (bool): 是否使用BGE模型，默认True

**方法**:

##### `encode(texts: List[str]) -> List[List[float]]`

生成文本向量。

**参数**:
- `texts`: 文本列表

**返回值**:
- 向量列表，每个向量1024维

**示例**:
```python
from embed_local import LocalEmbedding

embedder = LocalEmbedding(use_bge=True)
vectors = embedder.encode(["你好世界", "机器学习"])
print(f"向量维度: {len(vectors[0])}")  # 1024
```

##### `get_embedding_function() -> Callable`

获取ChromaDB兼容的embedding函数。

---

### add_paper.py - 论文添加

#### `class PaperAdder`

论文添加器类。

**初始化参数**:
- `use_bge` (bool): 是否使用BGE模型，默认True

**方法**:

##### `chunk_text(text: str, paper_metadata: Dict) -> Tuple[List[Dict], List[Dict]]`

文本切分，实现父子切分策略。

**参数**:
- `text`: 论文文本内容
- `paper_metadata`: 论文元数据

**返回值**:
- `(child_chunks, parent_chunks)`: 子块列表和父块列表

##### `add_to_chroma(chunks: List[Dict])`

添加chunks到ChromaDB向量库。

##### `add_to_bm25(chunks: List[Dict])`

添加chunks到BM25索引。

##### `add_paper(paper_metadata: Dict, analysis_content: str) -> Tuple[int, int]`

添加单篇论文。

**参数**:
- `paper_metadata`: 论文元数据
- `analysis_content`: 论文解读内容

**返回值**:
- `(child_count, parent_count)`: 子块数量和父块数量

**示例**:
```python
from add_paper import PaperAdder

adder = PaperAdder(use_bge=True)

metadata = {
    'filename': 'paper.pdf',
    'paper_title': 'My Paper',
    'arxiv_id': '2301.12345',
    'category': 'ai',
    'keywords': ['deep learning'],
    'created_at': '2024-01-01'
}

with open('analysis.md', 'r') as f:
    content = f.read()

child_count, parent_count = adder.add_paper(metadata, content)
```

#### `load_paper_index() -> Dict`

加载论文分类索引。

#### `get_paper_metadata(paper_index: Dict, category_key: str, paper_filename: str) -> Dict`

从索引获取论文元数据。

---

### search.py - 混合检索

#### `class HybridSearcher`

混合检索器类。

**初始化参数**:
- `use_bge` (bool): 是否使用BGE模型，默认True

**方法**:

##### `vector_search(query: str, top_k: int = None) -> List[Dict]`

向量语义检索。

**参数**:
- `query`: 查询文本
- `top_k`: 返回数量，默认使用配置值

**返回值**:
```python
[{
    'chunk_id': str,
    'content': str,
    'metadata': dict,
    'score': float,  # 相似度分数
    'source': 'vector'
}]
```

##### `bm25_search(query: str, top_k: int = None) -> List[Dict]`

BM25关键词检索。

**返回值**:
```python
[{
    'chunk_id': str,
    'content': str,
    'metadata': dict,
    'score': float,  # BM25分数
    'source': 'bm25'
}]
```

##### `rrf_fusion(vector_results: List[Dict], bm25_results: List[Dict]) -> List[Dict]`

RRF（Reciprocal Rank Fusion）融合算法。

**算法公式**:
```
RRF_score(d) = Σ 1/(k + rank(d))
```
其中 k=60（可配置）

##### `get_parent_context(chunk_id: str) -> str`

获取父块完整上下文。

**参数**:
- `chunk_id`: 子块ID

**返回值**:
- 父块完整文本内容

##### `search(query: str, top_k: int = None) -> Dict`

混合检索主函数。

**返回值**:
```python
{
    'results': [{
        'chunk_id': str,
        'content': str,
        'metadata': dict,
        'rrf_score': float,
        'source': 'hybrid',
        'parent_context': str  # 父块上下文
    }],
    'query': str,
    'stats': {
        'vector_count': int,
        'bm25_count': int,
        'hybrid_count': int
    }
}
```

**示例**:
```python
from search import HybridSearcher

searcher = HybridSearcher(use_bge=True)
result = searcher.search("MCP协议如何实现工具调用?")

print(f"向量检索: {result['stats']['vector_count']} 条")
print(f"BM25检索: {result['stats']['bm25_count']} 条")

for item in result['results'][:5]:
    print(f"\n分数: {item['rrf_score']:.4f}")
    print(f"内容: {item['content'][:100]}")
    print(f"父块上下文: {item['parent_context'][:200]}")
```

## 配置说明

### 环境变量

可选环境变量：

```bash
# 设置Hugging Face镜像（加速模型下载）
export HF_ENDPOINT=https://hf-mirror.com

# 设置CUDA设备
export CUDA_VISIBLE_DEVICES=0
```

### 目录结构

```
vectordb/
├── chroma_db/              # ChromaDB向量存储
│   └── chroma.sqlite3      # SQLite数据库
├── bm25_index/             # Whoosh BM25索引
│   └── MAIN_*
├── scripts/                # 核心脚本
│   ├── config.py           # 配置文件
│   ├── init_db.py          # 数据库初始化
│   ├── embed_local.py      # Embedding服务
│   ├── add_paper.py        # 论文添加
│   └── search.py           # 混合检索
├── .venv/                  # Python虚拟环境
└── README.md               # 本文档
```

### 元数据字段

存储在向量库中的元数据字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `category` | str | 论文分类 |
| `priority` | str | 优先级（critical/high/medium/low） |
| `arxiv_id` | str | arXiv编号 |
| `paper_title` | str | 论文标题 |
| `keywords` | List[str] | 关键词列表 |
| `chunk_type` | str | 切分类型 |
| `parent_id` | str | 关联父块ID |
| `section_title` | str | 章节标题 |
| `page_number` | int | 页码 |
| `source_file` | str | 原始PDF文件名 |
| `created_at` | str | 创建时间 |

## 性能优化

### GPU加速

系统默认使用CUDA进行GPU加速：

```python
# config.py
EMBEDDING_DEVICE = "cuda"
```

### 批量处理

添加论文时自动批量处理：

```python
# 批量添加
adder.add_to_chroma(chunks)  # 内部批量向量化
```

### 索引优化

ChromaDB自动优化索引，无需手动维护。

## 故障排除

### 1. BGE模型加载失败

**症状**: `OSError: Can't load tokenizer`

**解决方案**:
```bash
# 设置镜像
export HF_ENDPOINT=https://hf-mirror.com

# 或使用Ollama备选
# 系统会自动降级
```

### 2. CUDA内存不足

**症状**: `CUDA out of memory`

**解决方案**:
```python
# 修改 config.py
EMBEDDING_DEVICE = "cpu"  # 使用CPU
```

### 3. BM25索引损坏

**症状**: `IndexError: Index is closed`

**解决方案**:
```bash
rm -rf bm25_index/*
python scripts/add_paper.py  # 重建索引
```

## 扩展开发

### 自定义Embedding

```python
from embed_local import LocalEmbedding

class MyEmbedding(LocalEmbedding):
    def _encode_custom(self, texts):
        # 自定义编码逻辑
        pass

    def encode(self, texts):
        return self._encode_custom(texts)
```

### 自定义检索策略

```python
from search import HybridSearcher

class MySearcher(HybridSearcher):
    def custom_search(self, query):
        # 自定义检索逻辑
        vector_results = self.vector_search(query)
        # 添加自定义过滤...
        return filtered_results
```

## 依赖版本

| 包 | 版本 |
|----|------|
| chromadb | >=0.4.0 |
| sentence-transformers | >=2.2.0 |
| whoosh | >=2.7.0 |
| torch | >=2.0.0 |
| requests | >=2.28.0 |
| jieba | >=0.42.0 |

## 许可证

MIT License

## 更新日志

### v1.0.1 (2026-05-24)
- 添加jieba中文分词支持
- BM25索引支持中文关键词检索
- SIT测试100%通过

### v1.0.0 (2024-05-23)
- 初始版本
- 支持混合检索
- 实现父子切分策略
- BGE + Ollama双模型支持