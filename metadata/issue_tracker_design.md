---
name: code-review-issue-tracker
description: Code Review 问题追踪闭环流程 - QA Agent 发现 → Dev Agent 修复 → Incident Agent 监控
metadata:
  type: project
---

# Code Review 问题追踪闭环流程

## 需求背景

QA Agent 通过 Code Review 发现代码问题后，需要：
1. 问题规范化记录（背景、影响、根因、纠正措施、预防措施）
2. 交由 Development Agent 执行修复
3. Incident Response Agent 监控修复进度和质量

**Why**: 确保问题可追溯、修复有依据、预防有措施，形成完整的质量闭环。
**How to apply**: 新增问题追踪表 + Agent协作协议 + 自动分配机制。

---

## 一、问题清单数据结构

### 1.1 数据库表设计

```sql
-- 新增：code_review_issues 表
CREATE TABLE IF NOT EXISTS code_review_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 问题标识
    issue_id TEXT UNIQUE NOT NULL,  -- "ISS-20260525-001"
    created_at TEXT NOT NULL,
    session_id TEXT,  -- 关联审计会话
    
    -- 问题分类
    issue_type TEXT NOT NULL,  -- 'logic', 'dimension', 'naming', 'boundary', 'security'
    severity TEXT NOT NULL,    -- 'critical', 'high', 'medium', 'low'
    status TEXT NOT NULL,      -- 'open', 'assigned', 'fixing', 'reviewing', 'closed', 'wontfix'
    
    -- 问题背景 (Background)
    paper_id TEXT,             -- 来源论文
    paper_context TEXT,        -- 论文算法描述
    code_file TEXT,            -- 问题代码文件
    code_location TEXT,        -- 具体位置 (如 "line 45-52")
    code_snippet TEXT,         -- 问题代码片段
    
    -- 影响评估 (Impact)
    impact_scope TEXT,         -- 'single_module', 'pipeline', 'system'
    impact_description TEXT,   -- 影响描述
    affected_components TEXT,  -- 受影响组件列表 (JSON)
    
    -- 根因分析 (Root Cause)
    root_cause_type TEXT,      -- 'misinterpretation', 'dimension_mismatch', 'logic_error', 'edge_case'
    root_cause_detail TEXT,    -- 详细根因
    analysis_method TEXT,      -- 'llm_analysis', 'rule_detection', 'manual_review'
    
    -- 纠正措施 (Corrective Action)
    fix_strategy TEXT,         -- 修复策略
    fix_assigned_to TEXT,      -- 分配给哪个 Agent
    fix_deadline TEXT,         -- 修复期限
    fix_priority INTEGER,      -- 优先级 (1-5)
    
    -- 预防措施 (Preventive Action)
    prevention_measures TEXT,  -- 预防措施 (JSON数组)
    test_coverage_added TEXT,  -- 新增测试覆盖
    documentation_updates TEXT, -- 文档更新
    
    -- 执行追踪
    fix_attempts INTEGER DEFAULT 0,  -- 修复尝试次数
    fix_history TEXT,          -- 修复历史 (JSON)
    review_result TEXT,        -- 复审结果
    
    -- 关联 Agent
    detected_by TEXT,          -- 发现者: 'qa_agent'
    assigned_to TEXT,          -- 执行者: 'dev_agent', 'incident_agent'
    
    -- 元数据
    metadata TEXT              -- JSON扩展
);
```

### 1.2 问题记录 JSON 格式

```python
issue_record = {
    # 问题标识
    "issue_id": "ISS-20260525-001",
    "created_at": "2026-05-25T10:30:00",
    "session_id": "sess_abc123",
    
    # 问题分类
    "issue_type": "dimension_mismatch",  # 张量维度错误
    "severity": "high",
    "status": "open",
    
    # 问题背景
    "background": {
        "paper_id": "transformer",
        "paper_context": "Attention(Q,K,V) = softmax(QK^T/√d_k)V",
        "code_file": "attention.py",
        "code_location": "line 45-52",
        "code_snippet": """
        # 错误代码
        attention_weights = torch.matmul(Q, K)  # 缺少维度转置
        output = torch.matmul(attention_weights, V)
        """,
        "expected_behavior": "Q与K需要转置后相乘，并除以√d_k"
    },
    
    # 影响评估
    "impact": {
        "scope": "single_module",
        "description": "注意力权重计算错误，导致模型无法正确聚焦",
        "affected_components": ["attention.py", "encoder.py"],
        "user_visible": False,  # 用户不可见，但影响准确性
        "data_loss_risk": False
    },
    
    # 根因分析
    "root_cause": {
        "type": "misinterpretation",  # 误解论文描述
        "detail": "未理解 Q×K^T 需要转置操作",
        "analysis_method": "llm_analysis",
        "confidence": 0.95
    },
    
    # 纠正措施
    "corrective_action": {
        "fix_strategy": "添加维度转置和缩放因子",
        "fix_code": """
        # 正确代码
        attention_weights = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(d_k)
        """,
        "assigned_to": "dev_agent",
        "deadline": "2026-05-25T14:00:00",
        "priority": 1
    },
    
    # 预防措施
    "preventive_action": {
        "measures": [
            "添加维度注释注释",
            "单元测试覆盖维度检查",
            "论文公式对照检查流程"
        ],
        "test_added": "test_attention_dimension.py",
        "doc_updated": "attention.md - 添加公式对照表"
    },
    
    # 执行追踪
    "execution": {
        "fix_attempts": 0,
        "fix_history": [],
        "final_status": None
    }
}
```

---

## 二、Agent 角色分工

### 2.1 问题流转流程

```
┌─────────────────────────────────────────────────────────────┐
│                   问题追踪闭环流程                            │
└─────────────────────────────────────────────────────────────┘

     QA Agent                    Dev Agent              Incident Agent
        │                            │                        │
        │ 1. Code Review             │                        │
        │   发现问题                 │                        │
        │                            │                        │
        ▼                            │                        │
   ┌─────────────┐                   │                        │
   │ 创建问题记录 │                   │                        │
   │ (完整5项)   │                   │                        │
   └─────────────┘                   │                        │
        │                            │                        │
        │ 2. 分配问题                 │                        │
        ├────────────────────────────▶                        │
        │                            │                        │
        │                            ▼                        │
        │                     ┌─────────────┐                 │
        │                     │ 接收问题    │                 │
        │                     │ 分析根因    │                 │
        │                     │ 设计修复    │                 │
        │                     └─────────────┘                 │
        │                            │                        │
        │                            │ 3. 执行修复            │
        │                            │    + 测试验证          │
        │                            │                        │
        │                            ▼                        │
        │                     ┌─────────────┐                 │
        │                     │ 提交修复    │─────────────────▶
        │                     │ 更新状态    │                 │
        │                     └─────────────┘                 │
        │                            │                        │
        │                            │                        ▼
        │                            │                 ┌─────────────┐
        │                            │                 │ 监控进度    │
        │                            │                 │ 验证质量    │
        │                            │                 │ 记录闭环    │
        │                            │                 └─────────────┘
        │                            │                        │
        │ 4. 复审修复                │                        │
        ├────────────────────────────▶                        │
        │                            │                        │
        ▼                            ▼                        ▼
   ┌──────────────────────────────────────────────────────────┐
   │                    问题关闭                               │
   │   status: closed                                          │
   │   review_result: passed                                   │
   │   prevention_measures: documented                         │
   └──────────────────────────────────────────────────────────┘
```

### 2.2 Agent 职责矩阵

| Agent | 职责 | 调用模型 | 关键方法 |
|-------|------|---------|---------|
| **QA Agent** | 发现问题、记录问题、复审修复 | 本地 qwen3.5-9b (Code Review) | `code_review()`, `create_issue()`, `verify_fix()` |
| **Development Agent** | 分析根因、执行修复、编写测试 | 云端 glm-5 | `analyze_issue()`, `implement_fix()`, `add_test()` |
| **Incident Response Agent** | 监控进度、协调资源、记录闭环 | 云端 glm-5 | `track_issue()`, `escalate_issue()`, `close_issue()` |

### 2.3 内置 Agent 映射

| 项目角色 | Claude 内置 Agent | 说明 |
|---------|------------------|------|
| Development Agent | `Senior Developer` | Laravel/Python专家，代码修复 |
| Incident Agent | `Incident Response Commander` | 事件管理、SLO追踪 |
| 代码审查专员 | `Minimal Change Engineer` | 最小化修改，防止过度重构 |

---

## 三、问题流转协议

### 3.1 问题生命周期

```
open → assigned → fixing → reviewing → closed
                 │                    │
                 │                    ▼
                 │            wontfix (无法修复)
                 │
                 ▼
          blocked (阻塞项)
```

| 状态 | 含义 | 责任 Agent |
|------|------|-----------|
| `open` | 新发现问题，待分配 | QA Agent |
| `assigned` | 已分配给 Dev Agent | Incident Agent |
| `fixing` | Dev Agent 正在修复 | Development Agent |
| `reviewing` | QA Agent 正在复审 | QA Agent |
| `closed` | 修复通过，预防措施已落实 | Incident Agent |
| `wontfix` | 无法修复或低优先级 | Incident Agent |
| `blocked` | 有阻塞项（依赖其他任务） | Incident Agent |

### 3.2 Agent 协作消息格式

```python
# QA Agent → Issue Tracker
issue_message = {
    "from": "qa_agent",
    "to": "issue_tracker",
    "action": "create",
    "issue": issue_record,  # 完整问题记录
    "timestamp": "2026-05-25T10:30:00"
}

# Issue Tracker → Dev Agent
assign_message = {
    "from": "issue_tracker",
    "to": "dev_agent",
    "action": "assign",
    "issue_id": "ISS-20260525-001",
    "priority": 1,
    "deadline": "2026-05-25T14:00:00"
}

# Dev Agent → Issue Tracker (修复完成)
fix_message = {
    "from": "dev_agent",
    "to": "issue_tracker",
    "action": "fix_complete",
    "issue_id": "ISS-20260525-001",
    "fix_result": {
        "code_changes": "diff...",
        "tests_added": "test_attention_dimension.py",
        "test_passed": True
    }
}

# Issue Tracker → QA Agent (复审请求)
review_message = {
    "from": "issue_tracker",
    "to": "qa_agent",
    "action": "verify_fix",
    "issue_id": "ISS-20260525-001",
    "fix_commit": "abc123"
}

# QA Agent → Issue Tracker (复审通过)
close_message = {
    "from": "qa_agent",
    "to": "issue_tracker",
    "action": "approve",
    "issue_id": "ISS-20260525-001",
    "review_result": "passed",
    "prevention_verified": True
}
```

---

## 四、QA Agent 问题记录方法

```python
class QualityAssuranceAgent:
    
    async def create_issue_from_review(
        self,
        review_result: Dict,
        paper_context: Dict,
        code_context: Dict
    ) -> str:
        """
        从 Code Review 结果创建问题记录
        
        Args:
            review_result: code_review() 返回的结果
            paper_context: 论文上下文
            code_context: 代码上下文
        
        Returns:
            issue_id: 问题编号
        """
        import uuid
        from datetime import datetime
        
        # 生成问题编号
        issue_id = f"ISS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
        
        # 构建完整问题记录
        issue_record = {
            "issue_id": issue_id,
            "created_at": datetime.now().isoformat(),
            
            # 从 review_result 提取问题分类
            "issue_type": review_result.get("issue_type", "logic"),
            "severity": self._calculate_severity(review_result),
            "status": "open",
            
            # 问题背景
            "background": {
                "paper_id": paper_context.get("paper_id"),
                "paper_context": paper_context.get("algorithm_desc"),
                "code_file": code_context.get("file_path"),
                "code_location": review_result.get("location"),
                "code_snippet": review_result.get("snippet"),
                "expected_behavior": paper_context.get("expected")
            },
            
            # 影响评估 (LLM 分析)
            "impact": await self._analyze_impact(review_result, code_context),
            
            # 根因分析
            "root_cause": {
                "type": review_result.get("root_cause_type"),
                "detail": review_result.get("root_cause_detail"),
                "analysis_method": "llm_analysis",
                "confidence": review_result.get("confidence", 0.8)
            },
            
            # 纠正措施 (LLM 建议)
            "corrective_action": {
                "fix_strategy": review_result.get("fix_suggestions", []),
                "assigned_to": "dev_agent",
                "deadline": self._calculate_deadline(review_result),
                "priority": self._calculate_priority(review_result)
            },
            
            # 预防措施
            "preventive_action": {
                "measures": review_result.get("prevention_measures", []),
                "test_added": None,  # Dev Agent 补充
                "doc_updated": None   # Dev Agent 补充
            }
        }
        
        # 写入数据库
        self._save_issue_to_db(issue_record)
        
        # 通知 Incident Agent
        await self._notify_incident_agent(issue_record)
        
        return issue_id
    
    def _calculate_severity(self, review_result: Dict) -> str:
        """计算问题严重等级"""
        score = review_result.get("score", 5)
        
        if score < 3:
            return "critical"  # 严重：核心功能错误
        elif score < 5:
            return "high"      # 高：重要功能问题
        elif score < 7:
            return "medium"    # 中：次要问题
        else:
            return "low"       # 低：优化建议
    
    def _calculate_deadline(self, review_result: Dict) -> str:
        """计算修复期限"""
        severity = self._calculate_severity(review_result)
        
        from datetime import datetime, timedelta
        
        if severity == "critical":
            deadline = datetime.now() + timedelta(hours=4)
        elif severity == "high":
            deadline = datetime.now() + timedelta(hours=8)
        elif severity == "medium":
            deadline = datetime.now() + timedelta(days=1)
        else:
            deadline = datetime.now() + timedelta(days=3)
        
        return deadline.isoformat()
    
    def _calculate_priority(self, review_result: Dict) -> int:
        """计算优先级 (1最高，5最低)"""
        severity = self._calculate_severity(review_result)
        
        priority_map = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 5
        }
        
        return priority_map.get(severity, 4)
```

---

## 五、Orchestrator 集成

```python
class SpecializedAgentOrchestrator:
    
    def __init__(self, ...):
        # 现有初始化
        
        # 新增：问题追踪组件
        self.issue_tracker = IssueTracker()
        self.incident_agent = IncidentResponseAgent(self.issue_tracker)
    
    async def run_pipeline_with_issue_tracking(
        self,
        query: str,
        enable_code_review: bool = True,
        enable_issue_tracking: bool = True
    ):
        """带问题追踪的完整流程"""
        
        # Stage 1-3: 现有流程
        retrieval_result = await self.retrieval_agent.retrieve(query)
        analysis_result = await self.analysis_agent.analyze(retrieval_result)
        qa_result = self.qa_agent.validate(analysis_result["output"], retrieval_result["results"])
        
        # Stage 4: 代码生成
        code_result = await self.code_agent.generate(analysis_result)
        
        # Stage 4.5: 代码审查 (带问题追踪)
        if enable_code_review:
            review_result = await self.qa_agent.code_review(
                code_result["code"],
                analysis_result["algorithm_desc"],
                enable_local=True
            )
            code_result["review"] = review_result
            
            # 问题严重则创建问题记录
            if enable_issue_tracking and review_result.get("score", 10) < 7:
                issue_id = await self.qa_agent.create_issue_from_review(
                    review_result,
                    paper_context={
                        "paper_id": retrieval_result.get("paper_id"),
                        "algorithm_desc": analysis_result.get("algorithm_desc")
                    },
                    code_context={
                        "file_path": code_result.get("file_path"),
                        "module": code_result.get("module")
                    }
                )
                
                # 分配给 Development Agent
                await self.incident_agent.assign_issue(issue_id, "dev_agent")
                
                code_result["issue_created"] = issue_id
        
        return {
            "retrieval": retrieval_result,
            "analysis": analysis_result,
            "qa": qa_result,
            "code": code_result,
            "issues": self.issue_tracker.get_open_issues()
        }
```

---

## 六、问题追踪 Dashboard

### 6.1 实时监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| `open_issues_count` | 待处理问题数 | > 5 |
| `critical_issues_count` | 严重问题数 | > 0 |
| `avg_fix_time_hours` | 平均修复时间 | > 24h |
| `fix_success_rate` | 修复成功率 | < 90% |
| `prevention_rate` | 预防措施落实率 | < 80% |

### 6.2 问题清单视图

```
┌─────────────────────────────────────────────────────────────┐
│                   Code Review Issues Dashboard               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Open Issues: 3    Critical: 1    Avg Fix Time: 4.2h       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ ISS-20260525-001 [critical] [fixing]                  │ │
│  │ 类型: dimension_mismatch                              │ │
│  │ 影响: attention.py 无法正确聚焦                        │ │
│  │ 根因: 未理解 Q×K^T 需要转置                            │ │
│  │ 修复: Dev Agent 正在修复 (deadline: 14:00)            │ │
│  │ 预防: 添加维度注释 + 单元测试                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ ISS-20260525-002 [high] [assigned]                    │ │
│  │ 类型: logic_error                                     │ │
│  │ 影响: encoder 少处理一层                               │ │
│  │ 根因: 论文描述理解偏差                                 │ │
│  │ 修复: 待 Dev Agent 开始                               │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、实施步骤

| 步骤 | 内容 | 预估工期 | 影响范围 |
|------|------|---------|---------|
| 1 | 新增 `code_review_issues` 表到 schema.py | 0.5天 | 独立新增表 |
| 2 | 实现 `IssueTracker` 类 | 1天 | 新模块 |
| 3 | QA Agent 添加 `create_issue_from_review()` | 1天 | 新方法 |
| 4 | 实现 `IncidentResponseAgent` | 1天 | 新 Agent |
| 5 | Orchestrator 集成问题追踪 | 0.5天 | 可选参数 |
| 6 | Dashboard 可视化 | 2天 | WebUI 模块 |

**总计**: 6天

---

## 八、验收标准

| 功能 | 测试方法 | 预期结果 |
|------|---------|---------|
| 问题创建 | 模拟 Code Review 低分 | issue_id 生成，数据库记录完整 |
| 问题分配 | Incident Agent API | Dev Agent 收到任务 |
| 修复执行 | Dev Agent 修复流程 | 状态变为 reviewing |
| 复审验证 | QA Agent verify_fix() | 状态变为 closed |
| 预防措施 | 检查 test/doc 更新 | prevention_verified=True |

---

**文档状态**: 设计方案
**下一步**: 确认后开始实现 IssueTracker 类

[[qa-agent-dual-model-config]]