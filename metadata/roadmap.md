# Agentic RAG 系统实施路线图

## 项目愿景

**从论文公式 → 100%可执行代码成品**

超越传统QA RAG，实现行动与工程型Agentic RAG。

---

## 三阶段实施计划

### Phase 1: 验证期 (Week 1)

**目标**: 验证沙箱自动编译 + 报错自愈闭环

**任务清单**:
- [ ] 创建 TransformerReconstructorPipeline 基础类
- [ ] 测试本地9B模型Debug能力
- [ ] 验证张量维度错误自动修复
- [ ] 设定max_retries=3熔断机制

**验收标准**:
- 能成功将故意写错的张量维度[B,C,T]修正为[B,T,C]
- 测试用例100%通过

### Phase 2: 工程期 (Week 2-3)

**目标**: 搭建生产级Web界面

**任务清单**:
- [ ] FastAPI/Streamlit服务搭建
- [ ] 实时流式日志展示
- [ ] RAG Agent MCP工具开发
- [ ] 审计日志系统集成
- [ ] 评估指标监测Dashboard

**验收标准**:
- 用户可通过Web界面查询论文知识
- 实时看到代码生成和Debug过程
- 完整审计追踪

### Phase 3: 扩展期 (Week 4+)

**目标**: 多模态图文相间

**任务清单**:
- [ ] Qwen3-VL集成
- [ ] Matplotlib图表自动生成
- [ ] 图表嵌入解读文章
- [ ] 完整代码复现流程

**验收标准**:
- 论文 → 解读 → 代码 → 图表 → 完整知识库

---

## 学术基准对标

| 我们的模块 | 学术基准 |
|----------|---------|
| 父子切分 | PaperQA2 Context Tracking |
| 混合检索 | CodeRAG-Bench RRF融合 |
| 自愈Debug | RAG-Reflect Self-Reflection |
| 沙箱执行 | OpenInterpreter/Cline |

---

## 技术栈确认

| 层级 | 技术 | 状态 |
|-----|------|------|
| 向量库 | ChromaDB | ✅ 已搭建 |
| Embedding | BGE-large-zh | ✅ 已配置 |
| 检索 | 混合检索(向量+BM25) | ✅ 已实现 |
| 沙箱 | subprocess/Docker | ⏳ 待实现 |
| DebugLLM | 本地9B Python-Coder | ⏳ 待实现 |
| 生成LLM | 云端GLM-5.1 | ✅ 已有 |
| WebUI | FastAPI/Streamlit | ⏳ 待实现 |

---

## 下一步行动

1. **立即执行**: Transformer复现验证测试
2. **并行准备**: Phase 2工程架构设计
3. **持续学习**: PaperQA2、CodeRAG-Bench源码研究

---

**创建时间**: 2026-05-24
**参考文档**: agentic-rag-architecture.md