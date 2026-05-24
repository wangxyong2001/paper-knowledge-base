# 论文知识库 RAG 测试QA体系框架

## 测试分层架构

```
┌─────────────────────────────────────────────────────────┐
│                  测试金字塔                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  E2E Tests (端到端测试)                                 │
│  ├── 用户完整流程测试                                   │
│  ├── 多Agent协作测试                                    │
│  └── 生产环境模拟                                       │
│                                                         │
│  ─────────────────────────────────────────────          │
│                                                         │
│  System Tests (系统测试)                                │
│  ├── RAG完整流程测试                                    │
│  ├── 多组件集成测试                                     │
│  ├── 性能压力测试                                       │
│  └── 安全渗透测试                                       │
│                                                         │
│  ─────────────────────────────────────────────          │
│                                                         │
│  Integration Tests (集成测试)                           │
│  ├── ChromaDB集成                                       │
│  ├── LangGraph节点集成                                  │
│  ├── LLM API集成                                        │
│  └── 沙箱执行集成                                       │
│                                                         │
│  ─────────────────────────────────────────────          │
│                                                         │
│  Unit Tests (单元测试)                                  │
│  ├── 检索模块测试                                       │
│  ├── Embedding测试                                      │
│  ├── 切分策略测试                                       │
│  ├── 工具函数测试                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Agent专项测试

### 1. 工具调用测试
```python
class ToolCallingTests:
    """Agent工具调用测试"""
    
    def test_search_papers_tool(self):
        """测试search_papers工具"""
        result = agent.call_tool("search_papers", {"query": "Transformer"})
        assert result["chunks"] is not None
        assert len(result["chunks"]) > 0
        
    def test_gather_evidence_tool(self):
        """测试gather_evidence工具"""
        result = agent.call_tool("gather_evidence", {"query": "attention"})
        assert result["evidence"] is not None
        assert all(e["source"] for e in result["evidence"])
```

### 2. 状态流转测试
```python
class StateTransitionTests:
    """LangGraph状态流转测试"""
    
    def test_interpret_to_retrieve(self):
        """测试interpret→retrieve流转"""
        state = {"query": "什么是Transformer?"}
        next_node = get_next_node(state, "interpret")
        assert next_node == "retrieve"
        
    def test_grade_docs_routing(self):
        """测试grade_docs条件路由"""
        state = {"grades": ["relevant", "relevant", "irrelevant"]}
        next_node = get_next_node(state, "grade_docs")
        assert next_node == "generate"  # 有足够relevant文档
```

### 3. 自省循环测试
```python
class ReflectionTests:
    """Reflection工作流测试"""
    
    def test_retry_loop(self):
        """测试重试循环"""
        state = {
            "reflection": {"support_score": 0.6, "decision": "retry"},
            "retry_count": 1
        }
        next_node = get_next_node(state, "reflect")
        assert next_node == "retrieve"
        
    def test_fuse_mechanism(self):
        """测试熔断机制"""
        state = {
            "reflection": {"support_score": 0.3},
            "retry_count": 3  # 达到max_retries
        }
        next_node = get_next_node(state, "reflect")
        assert next_node == "escalate"  # 熔断，人工介入
```

## RAG质量评估

### 检索质量指标
| 指标 | 定义 | 计算公式 | 目标值 |
|-----|------|---------|-------|
| Precision@5 | 前5结果准确率 | 相关数/5 | ≥0.80 |
| Recall@10 | 前10结果召回率 | 返回相关/总相关 | ≥0.70 |
| MRR | 平均排名倒数 | Σ1/rank/n | ≥0.85 |
| NDCG | 归一化累积增益 | 标准公式 | ≥0.80 |

### 幻觉检测测试
```python
class HallucinationTests:
    """幻觉检测测试"""
    
    def test_claim_source_matching(self):
        """声明-来源匹配测试"""
        answer = "Transformer使用自注意力机制"
        sources = [{"content": "Transformer employs self-attention"}]
        
        claims = extract_claims(answer)
        for claim in claims:
            matched = find_source(claim, sources)
            assert matched is not None
            
    def test_citation_accuracy(self):
        """引用准确率测试"""
        citations = extract_citations(answer)
        for citation in citations:
            # 验证引用是否指向真实chunk
            chunk = get_chunk(citation["chunk_id"])
            assert chunk is not None
            assert citation["text"] in chunk["content"]
```

## 测试自动化流程

### CI/CD集成
```yaml
# .github/workflows/test.yml
name: RAG System Tests

on:
  push:
    paths:
      - 'vectordb/**'
      - 'agents/**'
  
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Unit Tests
        run: |
          cd vectordb
          .venv/bin/python scripts/tests.py --unit
          
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Integration Tests
        run: |
          cd vectordb
          .venv/bin/python scripts/tests.py --integration
          
  rag-quality-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run RAG Quality Tests
        run: |
          cd vectordb
          .venv/bin/python scripts/tests.py --quality
```

## QA流程

### Bug报告模板
```
## Bug描述
简要描述问题

## 环境信息
- Python版本: 
- ChromaDB版本: 
- 操作系统: 

## 重现步骤
1. 
2. 
3. 

## 预期结果

## 实际结果

## 日志/截图
```

### Bug生命周期
```
New → Assigned → In Progress → Fixed → Verified → Closed
                      ↓
                   Reopened (如果验证失败)
```

### Release Checklist
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] RAG质量指标达标
- [ ] 幻觉率 < 5%
- [ ] Citation准确率 > 95%
- [ ] 性能测试通过
- [ ] 安全测试通过
- [ ] 文档更新完成

## 测试数据集

### 测试论文样本 (10篇)
1. Transformer (Attention Is All You Need)
2. BERT
3. GPT系列
4. ResNet
5. MoE架构论文
6. RAG论文
7. LangChain相关
8. DeepSeek系列
9. Qwen系列
10. MCP协议论文

### 测试查询集 (50条)
| ID | 查询 | 期望结果类型 |
|----|------|-------------|
| Q1 | Transformer的核心创新是什么? | 概念解释 |
| Q2 | 自注意力机制的公式 | 公式解释 |
| Q3 | Transformer Decoder架构 | 架构描述 |
| Q4 | 请生成Transformer代码 | 代码生成 |
| Q5 | Transformer与RNN的区别 | 对比分析 |

---

**创建时间**: 2026-05-24
**状态**: 初版设计