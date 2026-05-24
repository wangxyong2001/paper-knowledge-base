# 论文知识库系统需求描述（一页纸）

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

**✓ 已完成 (13项核心模块)**

| 模块 | 成果 | 验证 |
|-----|------|-----|
| 论文分类与索引构建 | paper_index.json | ✓ |
| 向量数据库系统 | ChromaDB + BGE + BM25 + RRF | ✓ SIT通过 |
| Transformer论文深度解读 | 餐巾纸摘要示例 | ✓ |
| RAG架构设计与技术选型 | 技术栈确定 | ✓ |
| Agent治理与评估体系 | governance_framework_design.md | ✓ |
| 审计日志SQLite系统 | 14表Schema + 迁移脚本 | ✓ 集成测试通过 |
| Prompt重构与注入防御 | 5类攻击检测 | ✓ 单元测试 |
| 翻译提炼与格式化输出 | Citation + Markdown | ✓ |
| 监测指标SQLite存储 | 30+指标6层 | ✓ |
| DashScope API客户端 | Token估算 + 成本计算 | ✓ |
| hello-agents学习与落地规划 | paper_rag_agent_implementation_plan.md | ✓ |
| LangGraph Agent框架 | agents/paper_rag_agent.py | ✓ |
| 集成测试全流程验证 | tests/integration_test.py | ✓ 通过 |

**⏳ 待完成 (6项)**

- MemoryManager模块实现
- ToolRegistry统一接口
- 四角色专用Agent分工（检索/解读/质量/复现）
- CLI交互界面
- WebUI Dashboard
- 剩余86篇论文处理

---

## 三、核心模块状态

| 模块 | 状态 | 功能 |
|-----|------|------|
| 审计系统 | ✓ | 输入/Prompt/LLM调用/输出/检索全流程SQLite记录 |
| 提示词模板 | ✓ | CalVer版本控制 + Anti-Lost上下文重组 + 注入防御 |
| 监测系统 | ✓ | 30+指标6层 + 告警阈值 + SQLite持久化 |
| API客户端 | ✓ | DashScope调用 + Token估算 + 成本计算 + 重试机制 |
| 向量检索 | ✓ | ChromaDB + BM25 + RRF融合 + 父子切分 |
| 记忆系统 | ⏳ | Working/Episodic Memory跨会话复用 |
| 工具注册 | ⏳ | ToolRegistry统一接口 |
| 专用Agent | ⏳ | 检索/解读/质量/复现四角色分工 |
| 用户界面 | ⏳ | CLI交互 + WebUI Dashboard |

---

## 四、要解决的具体问题

| 问题 | 表现 | 解决方案 | 状态 |
|-----|------|---------|------|
| 过程不透明 | 不知道Agent做了什么、检索了什么、用了什么Prompt | AuditLogger记录每一步到SQLite | ✓ 已解 |
| 重复劳动 | 同篇论文每次重新解读，浪费时间和Token | MemoryManager存储分析快照，下次直接复用 | ⏳ 待解 |
| 幻觉无验证 | Agent生成内容无来源，用户被误导 | cite_check验证，每句话必须有出处 | ⏳ 待解 |
| Prompt混乱 | 手写Prompt不一致，效果不稳定 | 模板库管理 + 版本控制 + Anti-Lost优化 | ✓ 已解 |
| 表格数据丢失 | 实验结果表无法检索，只能手动翻PDF | pdfplumber提取表格向量化 | ⏳ 待解 |
| 用户焦虑 | 长时间无反馈，不知道进度 | StreamOutput实时推送进度事件 | ⏳ 待解 |
| 无数据支撑优化 | 不知道系统表现如何，无法针对性改进 | 30+指标监测 + SQLite存储 + 告警触发 | ✓ 已解 |

---

## 五、用户可感知价值

| 模块 | 解决的问题 | 用户可感知的变化 |
|-----|----------|----------------|
| 审计系统 | 不知道Agent做了什么 | 可查看每一步：检索了什么、用了什么Prompt<br>可导出审计报告，追溯问题来源 |
| 提示词模板 | Prompt手写不一致 | 模板版本化管理，效果稳定可控<br>Anti-Lost优化，重要内容不丢失 |
| 监测系统 | 不知道系统表现 | Dashboard看30+指标趋势<br>告警自动触发，问题及时发现 |
| 记忆系统 | 重复解读同一论文 | "刚才分析什么"有效，历史直接复用<br>不再每次重新解读，节省等待时间 |

---

## 六、透明治理架构

```
用户输入 → [注入检测] → [Prompt模板化] → LLM调用
    │           │              │               │
    └───────────┴──────────────┴───────────────┘
                    ↓
              [审计日志SQLite]
                    ↓
LLM输出 → [幻觉检测] → [引用验证] → 格式化输出
    │           │              │               │
    └───────────┴──────────────┴───────────────┘
                    ↓
              [30+指标采集] → Dashboard可视化
```

**审计日志记录点（已实现）**

- `log_input()` → 用户原始输入 + 意图解析
- `log_prompt()` → 重构后Prompt + 模板版本 + Token数
- `log_llm_call()` → API调用 + Provider + 模型 + 延迟 + Token消耗
- `log_retrieval()` → 检索结果 + chunk_ids + scores + 精度指标
- `log_output()` → 格式化输出 + Citation列表
- `log_quality()` → 幻觉风险 + 引用准确率 + 支撑度
- `log_error()` → 错误类型 + 详细信息

---

## 七、系统定位

```
从: 被动检索工具 → 黑盒执行 → 无记忆 → 无审计
到: 透明智能助手 → 全流程可追溯 → 历史复用 → 审计日志 → 持续优化
```

**当前阶段**: 基础架构MVP完成 ✓ → 专用Agent落地 ⏳ → 用户界面 ⏳

---

## 八、数据来源说明

| 数据 | 来源 |
|-----|------|
| 14表Schema | database/schema.py 第18-67行 |
| 30+指标 | metrics_collector.py 第17-65行 |
| 告警阈值 | metrics_collector.py 第68-75行 |
| Prompt版本 | prompt_restructurer.py 第227-292行 |
| 注入防御5类 | prompt_restructurer.py 第74-126行 |
| 集成测试验证 | tests/integration_test.py 全流程通过 |

---

*核心定位: 个人/团队知识基础设施，全流程透明可控*