# 论文知识库RAG系统需求描述（一页纸）

> 更新日期: 2026-05-24 | 完成进度: 40%

---

## 一、系统目标

**分析87+论文 → 中文通俗解读 → 向量存储 → 语义检索 → 知识复用 → 透明治理**

核心定位: **个人/团队知识基础设施，全流程透明可控**

---

## 二、当前完成进度

```
████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 40%
```

### ✓ 已完成 (19项)

| # | 任务 | 成果 | 验证 |
|---|-----|------|-----|
| 1 | 论文分类与索引构建 | paper_index.json | ✓ |
| 2 | 向量数据库系统搭建 | ChromaDB + BGE嵌入 | ✓ SIT通过 |
| 3 | Transformer论文深度解读 | 餐巾纸摘要样本 | ✓ |
| 4 | RAG架构设计与技术选型 | 技术栈确定 | ✓ |
| 5 | RAG Agent治理与评估体系 | governance_framework_design.md | ✓ |
| 6 | 评估指标与监测体系 | 30+指标6层 | ✓ |
| 7 | 提示词工程与安全防护 | 注入防御 | ✓ |
| 8 | 向量数据库SIT测试 | 20项100%通过 | ✓ |
| 9 | RAG Agent独立部署架构 | architecture_review_audit.md | ✓ |
| 10 | Agent框架选型与集成 | LangGraph选型 | ✓ |
| 11 | 测试QA体系配套 | test_qa_framework.md | ✓ |
| 12 | Agent工程化管理 | agent_engineering_management.md | ✓ |
| 13 | 审计日志SQLite系统 | 14表Schema | ✓ 集成测试通过 |
| 14 | Prompt重构与注入防御 | 5类攻击检测 | ✓ 单元测试 |
| 15 | 翻译提炼与格式化输出 | Citation + Markdown | ✓ |
| 16 | 监测指标SQLite存储 | Dashboard数据源 | ✓ |
| 17 | hello-agents学习与落地规划 | implementation_plan.md | ✓ |
| 18 | Schema迁移v1→v2 | api_calls/user_feedback扩展 | ✓ |
| 19 | API客户端DashScope | Token估算 + 成本计算 | ✓ |

### ⏳ 待完成 (6项)

| 优先级 | 任务 | 预估工期 |
|-------|------|---------|
| P0 | MemoryManager模块实现 | 3天 |
| P0 | ToolRegistry统一接口 | 2天 |
| P1 | 四角色专用Agent分工 | 5天 |
| P2 | CLI交互界面 | 3天 |
| P3 | WebUI Dashboard | 5天 |
| P3 | 剩余86篇论文处理 | 2周 |

---

## 三、核心模块架构

| 模块 | 状态 | 功能 |
|-----|------|------|
| **记忆系统** | ⏳ | Working/Episodic/Semantic三层，跨会话复用 |
| **审计系统** | ✓ | 输入/Prompt/LLM调用/输出/检索全流程SQLite记录 |
| **提示词模板** | ✓ | CalVer版本控制 + Anti-Lost上下文重组 + 注入防御 |
| **监测系统** | ✓ | 30+指标6层 + 告警阈值 + SQLite持久化 |

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 记忆系统 ⏳  │  │ 审计系统 ✓   │  │ 提示词模板 ✓ │  │ 监测系统 ✓   │
│ MemoryManager│  │ AuditLogger  │  │ PROMPT_TEMPL │  │ MetricsCollector│
│ ─────────────│  │ ─────────────│  │ ─────────────│  │ ─────────────│
│ 工作记忆 ⏳  │  │ 输入记录 ✓   │  │ CalVer版本 ✓ │  │ 30+指标 ✓    │
│ 情景记忆 ⏳  │  │ Prompt重构 ✓ │  │ 模板库管理 ✓ │  │ 6层监测 ✓    │
│ 语义记忆 ✓  │  │ LLM调用 ✓    │  │ 变量注入 ✓   │  │ 告警阈值 ✓   │
│              │  │ 输出格式 ✓   │  │ Anti-Lost ✓  │  │ SQLite ✓     │
│ 跨会话复用 ⏳│  │ 全流程追溯 ✓ │  │ 上下文重组 ✓ │  │ Dashboard ⏳ │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

---

## 四、透明化治理 - RAG/LLM对话全程可追溯 ✓

### 审计日志记录点 (已实现)

| 方法 | 记录内容 |
|-----|---------|
| `log_input()` | 用户原始输入 + 意图解析 |
| `log_prompt()` | 重构后Prompt + 模板版本 + Token数 |
| `log_llm_call()` | API调用 + Provider + 模型 + 延迟 + Token消耗 |
| `log_retrieval()` | 检索结果 + chunk_ids + scores + 精度指标 |
| `log_output()` | 格式化输出 + Citation列表 |
| `log_quality()` | 幻觉风险 + 引用准确率 + 支撑度 |
| `log_error()` | 错误类型 + 详细信息 |

- SQLite存储 ✓: 14表全记录，session_id关联，时间戳排序
- 集成测试 ✓: tests/integration_test.py 全流程验证通过

---

## 五、提示词模板化管理 ✓

### PROMPT_TEMPLATES (prompt_restructurer.py 第227-292行)

```python
PROMPT_TEMPLATES = {
    "rag_query": {"version": "2025.12.01", ...},
    "paper_summary": {"version": "2025.12.01", ...},
    "formula_explanation": {"version": "2025.12.01", ...}
}
```

### PromptRestructurer功能

- `restructure_context()` → Anti-Lost-in-Middle上下文重组
- `assemble_prompt()` → 变量注入
- `count_tokens()` → Token估算

### 注入防御 ✓

5类攻击检测：角色劫持/输出操控/数据泄露/上下文注入/论文伪造

---

## 六、记忆系统 ⏳

### 问题

早上解读Transformer，下午重新解读 → Token浪费

### 记忆分层设计

| 层级 | 功能 | 状态 |
|-----|------|------|
| Working Memory | 当前会话上下文(10轮) | ⏳ 待实现 |
| Episodic Memory | 论文分析快照(SQLite) | ⏳ 待实现 |
| Semantic Memory | 向量知识库 | ✓ 已实现 |

### 落地方案

paper/metadata/paper_rag_agent_implementation_plan.md

---

## 七、监测系统 ✓

### 6层指标体系 (metrics_collector.py 第17-65行)

| 层级 | 指标 |
|-----|------|
| L1 运行 | request_count, success_rate, avg_response_time |
| L2 质量 | hallucination_rate, citation_accuracy |
| L3 Agent | tool_call_count, retry_count |
| L4 体验 | task_completion_rate |
| L5 成本 | token_efficiency, cost_per_task |
| L6 安全 | injection_attack_count |

- 告警阈值 ✓: error_rate>0.05, hallucination_rate>0.05
- SQLite存储 ✓: metrics表持久化

---

## 八、价值体现

| 模块 | 状态 | 解决的问题 | 用户可感知价值 |
|-----|------|----------|--------------|
| 记忆系统 | ⏳ | 重复劳动，多轮断裂 | 历史复用，Token↓50%，连贯↑10轮 |
| 审计系统 | ✓ | 过程不透明 | 全流程可查，SQLite持久化 |
| 提示词模板 | ✓ | Prompt混乱 | 版本控制，Anti-Lost优化 |
| 监测系统 | ✓ | 无数据支撑 | 30+指标，告警触发 |
| 反思-修正 | ⏳ | 检索质量差，幻觉风险 | 准确率↑25%，幻觉↓80% |
| 表格提取 | ⏳ | 数据丢失 | 覆盖↑95%，对比秒级完成 |
| 进度推送 | ⏳ | 用户焦虑 | 实时可见，等待有预期 |
| 闲聊检测 | ⏳ | 无效调用 | 响应↓95%，成本节约 |

---

## 九、系统定位

```
从: 被动检索工具 → 黑盒执行 → 无记忆 → 无审计
到: 透明智能助手 → 全流程可追溯 → 历史复用 → 审计日志 → 持续优化
```

**当前阶段**: 基础架构MVP完成 ✓ → 专用Agent落地 ⏳ → 用户界面 ⏳

---

## 十、hello-agents融合改进点

| hello-agents设计 | 融合状态 | 论文知识库落地 | 优先级 |
|-----------------|---------|--------------|-------|
| ReAct循环 | ✓ 已融合 | LangGraph Agent框架 | - |
| Pipeline编排 | ✓ 已融合 | 工作流节点定义 | - |
| 降级策略 | ✓ 已融合 | 双实例架构(DashScope→Ollama) | - |
| **MemoryManager** | ⏳ 待融合 | 三层记忆系统 | **P0** |
| **ToolRegistry** | ⏳ 待融合 | 统一工具接口 | **P0** |
| StreamOutput | ⏳ 待融合 | WebSocket进度推送 | P2 |
| 闲聊检测 | ⏳ 待融合 | CLI智能分流 | P2 |

---

## 十一、下一步实施路线

```
2026-05-24 ──▶ 2026-05-27 ──▶ 2026-05-30 ──▶ 2026-06-03 ──▶ 2026-06-07
    │              │              │              │              │
    ▼              ▼              ▼              ▼              ▼
MemoryManager   ToolRegistry   四角色Agent    CLI交互       Dashboard
(P0 3天)        (P0 2天)       (P1 5天)       (P2 3天)      (P3 5天)
    │              │              │              │              │
    ▼              ▼              ▼              ▼              ▼
  ⏳ 待启动      ⏳ 待启动       ⏳ 待启动       ⏳ 待启动       ⏳ 待启动
```

总计: 18天预估工期

---

## 十二、数据来源说明

| 数据 | 来源 |
|-----|------|
| 14表Schema | database/schema.py 第18-67行 |
| 30+指标定义 | metrics_collector.py 第17-65行 |
| 告警阈值 | metrics_collector.py 第68-75行 |
| Prompt模板版本 | prompt_restructurer.py 第227-292行 |
| 注入防御5类 | prompt_restructurer.py 第74-126行 |
| 集成测试验证 | tests/integration_test.py 全流程通过 |

---

*核心定位: 个人/团队知识基础设施，全流程透明可控*