# 论文知识库系统 - 功能规格文档 (FSD)

> Functional Specification Document
> 版本: v1.0
> 日期: 2026-05-25
> 维护者: Development Agent

---

## 文档目的

本 FSD 定义系统的**技术实现规格**，由 Development Agent 维护。
所有功能变更必须有：
- SOLID 设计原则支撑
- 架构决策记录 (ADR)
- 代码评审依据

---

## SOLID 原则遵循声明

| 原则 | 定义 | 本系统应用 |
|------|------|-----------|
| **S** - Single Responsibility | 每个类只做一件事 | 每个 Agent 只负责一个阶段 |
| **O** - Open/Closed | 对扩展开放，对修改关闭 | 新增方法不改现有代码 |
| **L** - Liskov Substitution | 子类可替换父类 | SpecializedAgent 继承 BaseAgent |
| **I** - Interface Segregation | 接口最小化 | ToolRegistry 统一接口 |
| **D** - Dependency Inversion | 依赖抽象而非具体 | Agent 依赖 ToolRegistry 抽象 |

---

## 一、核心模块功能规格

### 1.1 QA Agent 双模型配置

**FSD-ID**: FSD-QA-001
**版本**: v1.0
**状态**: 设计中

#### 功能概述

QA Agent 支持双模型配置：
- 默认验证任务：云端 glm-5
- Code Review 任务：本地 qwen3.5-9b-reviewer

#### SOLID 依据

| 原则 | 应用说明 |
|------|---------|
| **S** | QA Agent 只负责质量验证，代码生成由 Code Agent 负责 |
| **O** | 新增 `llm_validate()` 和 `code_review()` 方法，不修改现有 `validate()` |
| **D** | QA Agent 依赖 DashScopeClient 抽象接口，不直接依赖具体 API |

#### 接口规格

```python
class QualityAssuranceAgent:
    def __init__(
        self,
        registry: ToolRegistry,
        memory: Optional[PaperMemoryManager] = None,
        cloud_client: Optional[DashScopeClient] = None,  # 新增：云端客户端
        local_model: str = "qwen3.5-9b-reviewer",        # 新增：本地模型
        ollama_base_url: str = "http://localhost:11434"
    ):
        """初始化参数扩展 - Open/Closed 原则"""
        pass
    
    async def llm_validate(self, output: str, chunks: List[Dict]) -> Dict:
        """新增方法 - 云端 LLM 增强验证"""
        pass
    
    async def code_review(self, code: str, paper_context: str, enable_local: bool = True) -> Dict:
        """新增方法 - 本地小 LLM 代码审查"""
        pass
    
    def validate(self, output: str, chunks: List[Dict]) -> Dict:
        """现有方法 - 不修改 (规则工具验证)"""
        pass  # 保持原有实现不变
```

#### ADR 决策记录

**ADR-003**: QA Agent 双模型配置

| 决策项 | 选择 | 依据 |
|-------|------|------|
| 默认验证后端 | 云端 glm-5 | 复杂任务需要大模型推理 |
| Code Review 后端 | 本地 qwen3.5-9b | 代码审查可由小模型完成 |
| 集成方式 | 新增方法 | Open/Closed 原则 |

#### 参考文档

- `qa_agent_dual_model_design.md` - 设计方案
- `specialized_agents.py:440-639` - 现有实现

---

### 1.2 问题追踪系统

**FSD-ID**: FSD-ISSUE-001
**版本**: v1.0
**状态**: 设计中

#### 功能概述

Code Review 发现问题后，自动创建问题记录，分配给 Dev Agent 修复。

#### SOLID 依据

| 原则 | 应用说明 |
|------|---------|
| **S** | IssueTracker 只负责问题记录，修复由 Dev Agent 负责 |
| **O** | 新增 `code_review_issues` 表，不修改现有 `audit_logs` 表 |
| **I** | IssueTracker 提供 `create()`, `assign()`, `close()` 最小接口 |
| **D** | Dev Agent 依赖 IssueTracker 抽象，不直接操作数据库 |

#### 数据库表规格

```sql
-- 新增表 - 不修改现有表
CREATE TABLE IF NOT EXISTS code_review_issues (
    id INTEGER PRIMARY KEY,
    issue_id TEXT UNIQUE,
    issue_type TEXT,
    severity TEXT,
    status TEXT,
    
    -- 5项规范内容
    background TEXT,    -- JSON: 问题背景
    impact TEXT,        -- JSON: 影响评估
    root_cause TEXT,    -- JSON: 根因分析
    corrective TEXT,    -- JSON: 纠正措施
    preventive TEXT,    -- JSON: 预防措施
    
    assigned_to TEXT,
    created_at TEXT,
    metadata TEXT
);
```

#### 参考文档

- `issue_tracker_design.md` - 设计方案
- `schema.py` - 现有表结构

---

### 1.3 Orchestrator 可选参数扩展

**FSD-ID**: FSD-ORCH-001
**版本**: v1.0
**状态**: 设计中

#### 功能概述

Orchestrator 支持可选参数控制新功能启用。

#### SOLID 依据

| 原则 | 应用说明 |
|------|---------|
| **O** | 新参数默认 False，不影响现有调用 |
| **D** | Orchestrator 依赖 Agent 抽象接口 |

#### 接口规格

```python
class SpecializedAgentOrchestrator:
    async def run_pipeline(
        self,
        query: str,
        enable_llm_validate: bool = False,  # 新参数，默认关闭
        enable_code_review: bool = False,   # 新参数，默认关闭
        enable_issue_tracking: bool = False # 新参数，默认关闭
    ) -> Dict:
        """可选参数扩展 - 默认行为不变"""
        pass
```

---

## 二、Code Reviewer Agent 技能配置

**FSD-ID**: FSD-QA-002
**版本**: v1.0
**状态**: 已实现

#### 功能概述

QA Agent (Code Reviewer) 配备 Google Engineering Practices 最佳实践知识库。

#### SOLID 依据

| 原则 | 应用说明 |
|------|---------|
| **S** | 知识库只负责存储最佳实践，不负责代码执行 |
| **O** | 新增知识库文件，不修改现有 QA Agent 核心逻辑 |
| **D** | QA Agent 依赖知识库抽象，可替换为其他最佳实践来源 |

#### 知识库配置

```
/home/nvidia/workspace/paper/knowledge/
└── google_eng_practices/
    ├── code_review_guide.md      # Google Code Review 最佳实践
    └── README.md                 # 知识库索引
```

#### 核心技能内容

| 检查项 | 来源 | 说明 |
|-------|------|------|
| Design | Google looking-for.md | 整体设计合理性 |
| Functionality | Google looking-for.md | 功能正确性、并发问题 |
| Complexity | Google looking-for.md | 是否过度复杂 |
| Tests | Google looking-for.md | 测试覆盖 |
| Naming | Google looking-for.md | 命名清晰度 |
| Comments | Google comments.md | 注释必要性 |
| Style | Google looking-for.md | 风格一致性 |

#### 评论标签规范

| 标签 | 含义 | 依据 |
|------|------|------|
| `Nit:` | 小问题 | Google comments.md |
| `Optional:` | 可选改进 | Google comments.md |
| `FYI:` | 信息 | Google comments.md |

#### 参考文档

- `knowledge/google_eng_practices/code_review_guide.md` - 知识库
- https://github.com/google/eng-practices - 原始来源

---

## 三、模块依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                      SOLID 依赖架构                          │
└─────────────────────────────────────────────────────────────┘

                    ┌───────────────┐
                    │ ToolRegistry  │  ← 抽象接口 (D)
                    │ (Interface)   │
                    └───────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │Retrieval   │  │Analysis    │  │QA Agent    │
    │Agent       │  │Agent       │  │            │
    │(S:检索)    │  │(S:分析)    │  │(S:验证)    │
    └────────────┘  └────────────┘  └────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                           ▼
                    ┌───────────────┐
                    │ Orchestrator  │  ← 编排层
                    │ (D:依赖抽象)  │
                    └───────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │IssueTracker│  │DashScope   │  │Ollama      │
    │(新增)      │  │Client      │  │Client      │
    │(O:不修改)  │  │(云端)      │  │(本地)      │
    └────────────┘  └────────────┘  └────────────┘
```

---

## 三、变更审批流程

```
需求提出 → SOLID 分析 → ADR 记录 → 代码评审 → 实施 → 测试验收
    │           │            │           │        │        │
    │           │            │           │        │        │
    ▼           ▼            ▼           ▼        ▼        ▼
  BRD.md     FSD.md      ADR.md     CR报告   代码提交  QA报告
```

| 文档 | 责责 Agent | 内容 |
|------|----------|------|
| BRD.md | Product Agent | 业务需求，用户价值 |
| FSD.md | Development Agent | 功能规格，技术实现 |
| ADR.md | Architect Agent | 架构决策，权衡依据 |
| CR报告 | Code Reviewer | 代码评审，安全检查 |
| QA报告 | QA Agent | 测试验收，问题清单 |

---

## 四、变更历史

| FSD-ID | 版本 | 日期 | 变更内容 | SOLID依据 |
|--------|------|------|---------|----------|
| FSD-QA-001 | v1.0 | 2026-05-25 | QA Agent 双模型配置 | O: 新增方法 |
| FSD-ISSUE-001 | v1.0 | 2026-05-25 | 问题追踪系统 | O: 新增表 |
| FSD-ORCH-001 | v1.0 | 2026-05-25 | Orchestrator 可选参数 | O: 默认关闭 |

---

## 五、参考索引

| 设计文档 | 对应 FSD-ID |
|---------|------------|
| `qa_agent_dual_model_design.md` | FSD-QA-001 |
| `issue_tracker_design.md` | FSD-ISSUE-001 |
| `agent_governance.md` | 治理规则 |

---

**文档状态**: v1.0 初始版本
**下次更新**: 功能实现后补充测试规格
**维护责任**: Development Agent