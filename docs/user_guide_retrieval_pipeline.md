# 论文检索与 Pipeline 分析模块使用说明

> 版本: v1.0
> 日期: 2026-05-25
> 适用: 论文知识库 RAG 系统

---

## 目录

1. [模块概述](#一模块概述)
2. [快速开始](#二快速开始)
3. [检索模块](#三检索模块)
4. [Pipeline 分析](#四pipeline-分析)
5. [API 接口](#五api-接口)
6. [常见问题](#六常见问题)

---

## 一、模块概述

### 1.1 架构图

```
用户查询 ──▶ CLI/WebUI ──▶ Pipeline协调器 ──▶ 四阶段Agent协作
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Pipeline 四阶段                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [检索] ──▶ [分析] ──▶ [质量] ──▶ [代码]                        │
│    │           │          │          │                         │
│    ▼           ▼          ▼          ▼                         │
│  混合检索    内容解读    幻觉检测    代码生成                    │
│  Vector+     公式提取    引用验证    测试验证                    │
│  BM25+RRF    概念抽取    支撑度      模块输出                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                              最终输出 + 审计日志
```

### 1.2 核心能力

| 能力 | 说明 | 性能指标 |
|------|------|---------|
| 论文定位 | 混合检索（向量+BM25） | < 10秒 |
| 内容理解 | 公式提取、概念抽取 | 5分钟内 |
| 质量验证 | 幻觉检测、引用验证 | 幻觉率 < 5% |
| 代码复现 | 自动生成可执行代码 | 可运行 |

---

## 二、快速开始

### 2.1 CLI 命令行使用

```bash
# 进入项目目录
cd /home/nvidia/workspace/paper

# 基础查询
python -m vectordb.cli query "Transformer的核心创新是什么"

# 指定检索数量
python -m vectordb.cli query "BERT模型结构" --top-k 5

# 启用代码生成
python -m vectordb.cli query "Attention机制实现" --code

# JSON 格式输出
python -m vectordb.cli query "Self-Attention" --format json

# 查看系统状态
python -m vectordb.cli status

# 查看记忆历史
python -m vectordb.cli memory
```

### 2.2 Python API 使用

```python
from vectordb.agents.specialized_agents import create_orchestrator

# 创建 Pipeline 协调器
orchestrator = create_orchestrator("my-session")

# 运行完整 Pipeline
result = orchestrator.run_pipeline(
    query="Transformer的Self-Attention机制",
    top_k=10,
    need_code=True  # 是否生成代码
)

# 查看结果
print(result["analysis"]["output"])      # 分析输出
print(result["qa"]["quality_score"])     # 质量评分
print(result["code"]["modules"])         # 代码模块
```

---

## 三、检索模块

### 3.1 混合检索原理

```
┌─────────────────────────────────────────────────────────────┐
│                     混合检索流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  用户查询                                                   │
│      │                                                      │
│      ├──────────────────┬──────────────────┐               │
│      │                  │                  │               │
│      ▼                  ▼                  ▼               │
│  向量检索             BM25检索                              │
│  (语义相似)          (关键词匹配)                           │
│      │                  │                                  │
│      │                  │                                  │
│      ▼                  ▼                                  │
│  Top-K结果          Top-K结果                              │
│      │                  │                                  │
│      └──────────────────┴──────────────────┘               │
│                         │                                   │
│                         ▼                                   │
│                    RRF 融合                                 │
│                    (Reciprocal Rank Fusion)                 │
│                         │                                   │
│                         ▼                                   │
│                    综合排序结果                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 检索模式选择

| 模式 | 适用场景 | 优势 |
|------|---------|------|
| **混合检索**（默认） | 通用查询 | 语义+关键词双保险 |
| **向量检索** | 概念性查询 | 理解意图，召回相关概念 |
| **BM25检索** | 精确术语 | 关键词精确匹配 |

### 3.3 检索参数配置

```python
# config.py 中的检索配置
RETRIEVAL_CONFIG = {
    'vector_top_k': 20,      # 向量检索召回数
    'bm25_top_k': 20,        # BM25检索召回数
    'final_top_k': 10,       # 最终融合结果数
    'rrf_k': 60,             # RRF融合参数
}
```

### 3.4 单独调用检索模块

```python
from vectordb.scripts.search import HybridSearcher

# 创建检索器
searcher = HybridSearcher(use_bge=True)

# 混合检索
results = searcher.search("Transformer注意力机制", top_k=10)

# 仅向量检索
vector_results = searcher.vector_search("注意力机制")

# 仅BM25检索
bm25_results = searcher.bm25_search("attention")

# 查看结果格式
for result in results:
    print(f"ID: {result['chunk_id']}")
    print(f"内容: {result['content'][:100]}...")
    print(f"分数: {result['score']}")
    print(f"来源: {result['source']}")
```

---

## 四、Pipeline 分析

### 4.1 四阶段详解

#### 阶段 1: 检索（Retrieval）

| Agent | PaperRetrievalAgent |
|-------|---------------------|
| 输入 | query, top_k |
| 输出 | 论文片段列表 + 相关度评分 |
| 耗时 | 通常 < 2秒 |

**输出示例**：
```json
{
  "results": [
    {
      "chunk_id": "transformer_001",
      "content": "Self-Attention allows the model...",
      "score": 0.95,
      "paper_title": "Attention Is All You Need"
    }
  ],
  "metrics": {
    "total": 10,
    "avg_score": 0.87,
    "sources": {"vector": 6, "bm25": 4}
  }
}
```

#### 阶段 2: 分析（Analysis）

| Agent | PaperAnalysisAgent |
|-------|---------------------|
| 输入 | query, 检索结果 |
| 输出 | 公式列表 + 概念列表 + 餐巾纸摘要 |
| 耗时 | 通常 30-60秒 |

**输出示例**：
```json
{
  "formulas": [
    {
      "latex": "Attention(Q,K,V) = softmax(QK^T/√d_k)V",
      "description": "注意力计算公式"
    }
  ],
  "concepts": [
    {"name": "Self-Attention", "definition": "自注意力机制"},
    {"name": "Multi-Head", "definition": "多头注意力"}
  ],
  "output": "Transformer的核心创新是..."
}
```

#### 阶段 3: 质量验证（Quality）

| Agent | QualityAssuranceAgent |
|-------|----------------------|
| 输入 | 生成的输出, 检索结果 |
| 输出 | 质量评分 + 幻觉风险 + 修正建议 |
| 耗时 | 通常 < 5秒 |

**质量评分逻辑**：
```python
# 幻觉检测：实体支撑度
support_rate = supported_entities / total_entities

# 引用验证：有效引用占比
citation_accuracy = valid_citations / total_citations

# 综合评分
quality_score = 0.6 * support_rate + 0.4 * citation_accuracy
```

**输出示例**：
```json
{
  "quality_score": 0.85,
  "is_passed": true,
  "hallucination": {
    "risk_level": "low",
    "support_rate": 0.92
  },
  "citations": {
    "accuracy": 0.80,
    "valid_count": 4
  },
  "risks": [],
  "suggestions": ["建议补充位置编码说明"]
}
```

#### 阶段 4: 代码复现（Code）

| Agent | CodeReproductionAgent |
|-------|----------------------|
| 输入 | query, 分析结果 |
| 输出 | 代码模块 + 测试验证 |
| 耗时 | 通常 10-30秒 |
| 触发 | `need_code=True` |

**输出示例**：
```json
{
  "modules": [
    {
      "name": "attention.py",
      "code": "class SelfAttention...",
      "description": "自注意力实现"
    }
  ],
  "is_runnable": true,
  "test_passed": true
}
```

### 4.2 Pipeline 状态监控

```python
# CLI 输出示例
Pipeline: [检索] -> [分析] -> [质量] -> [代码]

  [检索] [OK] 检索完成: 10 篇论文
  [分析] [OK] 分析完成: 5 个概念, 3 个公式
  [质量] [OK] 质量评分: 0.85
  [代码] [OK] 生成 2 个模块
```

---

## 五、API 接口

### 5.1 查询接口

```python
# POST /query
{
  "query": "Transformer的注意力机制",
  "top_k": 10,
  "enable_code_review": false,
  "output_format": "markdown"
}

# Response
{
  "pipeline_status": "completed",
  "retrieval": {...},
  "analysis": {...},
  "quality_assurance": {...},
  "code_reproduction": {...},
  "final_output": "..."
}
```

### 5.2 WebSocket 流式接口

```python
# WebSocket /ws/chat

# 客户端发送
{"action": "query", "text": "Self-Attention原理"}

# 服务端流式返回
{"type": "stage_start", "stage": "retrieval"}
{"type": "stage_progress", "stage": "retrieval", "progress": 50}
{"type": "stage_complete", "stage": "retrieval", "result": {...}
...
{"type": "pipeline_complete", "result": {...}}
```

### 5.3 状态查询接口

```python
# GET /status
{
  "vectordb_count": 216,
  "bm25_index": "ready",
  "embedding_model": "nomic-embed-text",
  "agents": {
    "retrieval": "active",
    "analysis": "active",
    "qa": "active",
    "code": "active"
  }
}
```

---

## 六、常见问题

### Q1: 检索结果不准确？

**解决方案**：
1. 增加召回数量：`--top-k 20`
2. 使用更精确的关键词
3. 检查论文是否已入库

### Q2: 幻觉风险告警？

**原因**：实体支撑度低于阈值

**解决方案**：
- 查看修正建议
- 补充更多相关论文入库

### Q3: 代码生成失败？

**原因**：
1. 论文内容不包含算法实现细节
2. 算法复杂度过高

**解决方案**：
- 查看分析结果中的公式提取
- 手动补充实现细节

### Q4: 如何添加新论文？

```bash
# 单篇论文入库
python vectordb/scripts/add_paper.py --pdf path/to/paper.pdf

# 批量入库
python vectordb/scripts/batch_process_papers.py --dir papers/
```

### Q5: 如何查看审计日志？

```python
# 查询审计日志
from vectordb.database.audit_logger import AuditLogger

logger = AuditLogger()
logs = logger.query_session("session-001")
```

---

## 七、附录

### A. 命令参数表

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `query` | 查询文本 | 必填 |
| `--top-k` | 检索数量 | 10 |
| `--code` | 启用代码生成 | False |
| `--format` | 输出格式 | text |
| `--session` | 会话ID | auto |

### B. 输出格式说明

| 格式 | 说明 | 适用场景 |
|------|------|---------|
| `text` | 纯文本 | CLI 阅读 |
| `markdown` | Markdown 格式 | 文档保存 |
| `json` | JSON 结构 | API 调用 |

### C. 性能基准

| 指标 | 目标 | 实测 |
|------|------|------|
| 检索时间 | < 10秒 | ✓ 2-5秒 |
| 分析时间 | < 5分钟 | ✓ 30-60秒 |
| 质量评分 | > 0.7 | ✓ 平均 0.85 |
| 幻觉率 | < 5% | ✓ 3% |

---

## 八、相关文档

| 文档 | 路径 | 内容 |
|------|------|------|
| 项目总结 | `metadata/project_summary.md` | 整体架构 |
| Agent治理 | `metadata/agent_governance.md` | Agent角色分工 |
| 测试报告 | `output/test_report.md` | Pipeline测试 |
| 代码位置 | `vectordb/cli/main.py` | CLI入口 |
| 代码位置 | `vectordb/scripts/search.py` | 检索模块 |
| 代码位置 | `vectordb/agents/specialized_agents.py` | Agent实现 |

---

**文档状态**: v1.0
**更新频率**: 随功能迭代更新
**维护责任**: Development Agent