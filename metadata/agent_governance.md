# 论文知识库系统 - Agent治理制度

> SDLC全生命周期Agent职责分工与审计追溯体系
> 创建日期: 2026-05-24

---

## 一、治理原则

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Agent治理三大原则                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  1. 可审计 Auditability                                                         │
│  ├─ 每项任务执行有完整记录                                                       │
│  ├─ 所有决策过程可追溯                                                           │
│  ├─ 输入输出数据留痕                                                             │
│                                                                                 │
│  2. 可解释 Explainability                                                       │
│  ├─ Agent行为有明确规则                                                          │
│  ├─ 决策依据可说明                                                               │
│  ├─ 输出逻辑可验证                                                               │
│                                                                                 │
│  3. 可追溯 Traceability                                                         │
│  ├─ 任务来源可追踪                                                               │
│  ├─ 执行路径可回溯                                                               │
│  ├─ 问题根因可定位                                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、Agent角色分工表

| Agent角色 | 工作职责 | 工作产出 | 工作底稿位置 | SDLC阶段 |
|----------|---------|---------|-------------|---------|
| **Main Agent** | 项目总协调、任务分配、进度追踪、制度维护 | 任务分配表、进度报告、治理制度 | metadata/main_agent_log.md | 全生命周期 |
| **Development Agent** | 核心模块代码开发、功能实现 | Python代码文件、单元测试 | vectordb/core/*.py, tests/*.py | 开发阶段 |
| **QA Agent** | 验收标准定义、测试执行、问题追踪 | SOP文档、验收报告、问题清单 | metadata/QA验收*.md | 测试阶段 |
| **Paper X-Ray Agent** | 论文深度解读、公式提炼、餐巾纸摘要 | 分析报告、知识JSON | analyses/*.md, *.json | 内容生产 |
| **Retrieval Agent** | 向量检索、召回优化、结果评分 | 检索结果、召回指标 | logs/retrieval/*.log | 运行阶段 |
| **Quality Agent** | 幻觉检测、引用验证、质量评分 | 质量报告、风险告警 | logs/quality/*.log | 运行阶段 |
| **Security Agent** | 注入检测、安全审计、合规检查 | 安全报告、合规清单 | logs/security/*.log | 全生命周期 |
| **Coordinator Agent** | Agent协调、状态同步、冲突解决 | 协调日志、状态表 | logs/coordinator/*.log | 运行阶段 |

---

## 三、Main Agent职责制度

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Main Agent核心职责                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  职责一: 任务分配与调度                                                          │
│  ──────────────────────────────────────────────────────────────────────────────│
│  • 接收用户需求，分解为子任务                                                    │
│  • 根据Agent能力分配任务                                                         │
│  • 设置任务优先级和依赖关系                                                      │
│  • 监控任务执行进度                                                              │
│                                                                                 │
│  职责二: Agent能力维护                                                           │
│  ──────────────────────────────────────────────────────────────────────────────│
│  • 维护Agent注册表                                                               │
│  • 定义Agent能力边界                                                             │
│  • 更新Agent职责分工                                                             │
│  • 处理Agent升级/降级                                                            │
│                                                                                 │
│  职责三: 制度与规范维护                                                          │
│  ──────────────────────────────────────────────────────────────────────────────│
│  • 维护Agent治理制度                                                             │
│  • 定义工作产出标准                                                              │
│  • 定义工作底稿格式                                                              │
│  • 定期审计制度执行                                                              │
│                                                                                 │
│  职责四: 审计追溯管理                                                            │
│  ──────────────────────────────────────────────────────────────────────────────│
│  • 记录所有任务分配                                                              │
│  • 追踪Agent执行历史                                                             │
│  • 收集工作底稿                                                                  │
│  • 定期生成审计报告                                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Main Agent工作产出

**产出一: 任务分配表**

```markdown
| 任务ID | 任务内容 | 分配Agent | 优先级 | 状态 | 开始时间 | 完成时间 |
|-------|---------|----------|-------|------|---------|---------|
| T001 | MemoryManager实现 | Development Agent | P0 | 完成 | 2026-05-24 10:00 | 2026-05-24 12:00 |
| T002 | ToolRegistry实现 | Development Agent | P0 | 完成 | 2026-05-24 10:00 | 2026-05-24 12:30 |
| T003 | QA验收体系建设 | QA Agent | P0 | 进行中 | 2026-05-24 12:00 | - |
| T004 | 四角色Agent实现 | Development Agent | P1 | 进行中 | 2026-05-24 12:00 | - |
```

**产出二: 进度报告**

```markdown
## 项目进度报告 - 2026-05-24

### 整体进度
- 已完成模块: 8个
- 进行中模块: 2个
- 待开始模块: 5个
- 整体进度: 60%

### Agent执行状态
- Development Agent: 2个任务完成，1个进行中
- QA Agent: 1个任务进行中
- Main Agent: 协调监控中

### 问题清单
- [ ] MemoryManager测试数据污染
- [ ] ToolRegistry mock依赖缺失

### 下一步计划
- 完成四角色Agent
- QA验收报告输出
- CLI界面开发启动
```

**产出三: 治理制度**

本文档即是Main Agent维护的治理制度。

---

## 四、Agent工作底稿规范

### 4.1 工作底稿目录结构

```
/home/nvidia/workspace/paper/
├── metadata/               # 制度与规范
│   ├── agent_governance.md # Agent治理制度 (本文件)
│   ├── main_agent_log.md   # Main Agent工作日志
│   ├── task_allocation.md  # 任务分配表
│   ├── progress_report.md  # 进度报告
│   └── QA验收*.md          # QA工作底稿
│
├── logs/                   # Agent执行日志
│   ├── main/              # Main Agent日志
│   ├── development/       # Development Agent日志
│   ├── qa/                # QA Agent日志
│   ├── retrieval/         # Retrieval Agent日志
│   ├── quality/           # Quality Agent日志
│   ├── security/          # Security Agent日志
│   └── coordinator/       # Coordinator Agent日志
│
├── vectordb/               # 代码产出
│   ├── core/              # Development Agent代码产出
│   ├── agents/            # Agent框架代码
│   └── tests/             # 测试代码产出
│
└── analyses/               # Paper X-Ray Agent产出
    ├── *.md               # 论文分析报告
    └── *.json             # 知识结构化数据
```

### 4.2 工作底稿格式规范

**日志格式** (logs/*.log):

```json
{
  "log_id": "LOG-20260524-001",
  "timestamp": "2026-05-24T12:00:00Z",
  "agent": "Development Agent",
  "agent_id": "aea9bbdbdd892cd6d",
  "task_id": "T001",
  "action": "create_file",
  "input": {
    "file_path": "/home/nvidia/workspace/paper/vectordb/core/memory_manager.py",
    "content_length": 500
  },
  "output": {
    "success": true,
    "file_created": true,
    "tests_passed": 13
  },
  "audit": {
    "traceable": true,
    "explainable": true,
    "decision_basis": "基于hello-agents第8章设计"
  }
}
```

**报告格式** (metadata/*.md):

```markdown
# [Agent角色]工作报告 - YYYY-MM-DD

## 任务概要
- 任务ID: T001
- 任务内容: MemoryManager实现
- 执行时间: 2026-05-24 10:00 - 12:00

## 执行过程
1. 分析hello-agents第8章WorkingMemory设计
2. 设计三层记忆架构
3. 实现WorkingMemory (deque maxlen=10)
4. 实现EpisodicMemory (SQLite持久化)
5. 实现SemanticMemory接口
6. 编写13项测试套件
7. 运行测试验证

## 工作产出
- vectordb/core/memory_manager.py (500行)
- tests/test_memory_manager.py (300行)
- 测试结果: 13测试通过

## 问题记录
- [问题1] 测试数据污染导致3个测试失败
- [原因] 之前测试数据残留
- [状态] 待修复

## 审计追溯
- 设计依据: hello-agents第8章
- 代码位置: vectordb/core/memory_manager.py
- 测试位置: tests/test_memory_manager.py
- Git commit: ecf4ed8
```

---

## 五、Agent审计追溯体系

### 5.1 任务执行审计链

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    任务执行审计链                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  任务输入                                                                        │
│      │                                                                          │
│      ▼                                                                          │
│  Main Agent接收 ──▶ 记录任务分配表                                              │
│      │                                                                          │
│      ▼                                                                          │
│  Agent执行 ──▶ 记录执行日志 (logs/)                                             │
│      │                                                                          │
│      ▼                                                                          │
│  工作产出 ──▶ 记录产出清单 (metadata/)                                          │
│      │                                                                          │
│      ▼                                                                          │
│  工作底稿 ──▶ 记录底稿文件 (logs/, metadata/, vectordb/)                        │
│      │                                                                          │
│      ▼                                                                          │
│  Git提交 ──▶ commit hash + 作者 + 时间                                          │
│      │                                                                          │
│      ▼                                                                          │
│  审计报告 ──▶ metadata/审计报告*.md                                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 审计追溯查询示例

```bash
# 1. 查询任务分配
cat metadata/task_allocation.md | grep "T001"

# 2. 查询执行日志
cat logs/development/*.log | jq 'select(.task_id=="T001")'

# 3. 查询Git提交
git log --oneline | grep "MemoryManager"

# 4. 查询工作产出
ls vectordb/core/memory_manager.py

# 5. 查询测试结果
python tests/test_memory_manager.py

# 6. 查询审计报告
cat metadata/QA验收报告_20260524.md
```

---

## 六、Agent注册表

Main Agent维护所有Agent的注册信息：

```json
{
  "agents": [
    {
      "agent_id": "main",
      "agent_name": "Main Agent",
      "capabilities": ["任务分配", "进度监控", "制度维护", "审计管理"],
      "status": "active",
      "last_activity": "2026-05-24T12:00:00Z"
    },
    {
      "agent_id": "dev",
      "agent_name": "Development Agent",
      "capabilities": ["代码开发", "测试编写", "模块实现"],
      "status": "active",
      "current_task": "四角色Agent实现",
      "last_activity": "2026-05-24T12:00:00Z"
    },
    {
      "agent_id": "qa",
      "agent_name": "QA Agent",
      "capabilities": ["验收检查", "测试执行", "问题追踪", "SOP文档"],
      "status": "active",
      "current_task": "验收体系建设",
      "last_activity": "2026-05-24T12:00:00Z"
    },
    {
      "agent_id": "paper",
      "agent_name": "Paper X-Ray Agent",
      "capabilities": ["论文解读", "公式提炼", "餐巾纸摘要"],
      "status": "pending",
      "last_activity": null
    },
    {
      "agent_id": "retrieval",
      "agent_name": "Retrieval Agent",
      "capabilities": ["向量检索", "召回优化", "结果评分"],
      "status": "pending",
      "last_activity": null
    },
    {
      "agent_id": "quality",
      "agent_name": "Quality Agent",
      "capabilities": ["幻觉检测", "引用验证", "质量评分"],
      "status": "pending",
      "last_activity": null
    },
    {
      "agent_id": "security",
      "agent_name": "Security Agent",
      "capabilities": ["注入检测", "安全审计", "合规检查"],
      "status": "pending",
      "last_activity": null
    },
    {
      "agent_id": "coordinator",
      "agent_name": "Coordinator Agent",
      "capabilities": ["Agent协调", "状态同步", "冲突解决"],
      "status": "pending",
      "last_activity": null
    }
  ]
}
```

---

## 七、Agent冲突解决机制

### 7.1 冲突类型

| 冲突类型 | 描述 | 解决机制 |
|---------|------|---------|
| 资源冲突 | 多Agent同时访问同一资源 | Coordinator Agent分配锁 |
| 任务冲突 | 多Agent承担相同任务 | Main Agent重新分配 |
| 产出冲突 | 多Agent产出相同文件 | Coordinator Agent协调版本 |
| 优先级冲突 | 任务优先级不一致 | Main Agent调整优先级 |

### 7.2 解决流程

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Agent冲突解决流程                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  冲突检测 ──▶ Coordinator Agent                                                  │
│      │                                                                          │
│      ▼                                                                          │
│  冲突分析 ──▶ 决定解决方案                                                       │
│      │                                                                          │
│      ├─▶ 资源冲突 ──▶ 分配时间锁                                                 │
│      │                                                                          │
│      ├─▶ 任务冲突 ──▶ 通知Main Agent重新分配                                     │
│      │                                                                          │
│      ├─▶ 产出冲突 ──▶ 版本合并或覆盖                                             │
│      │                                                                          │
│      ├─▶ 优先级冲突 ──▶ 按业务优先级排序                                         │
│      │                                                                          │
│      ▼                                                                          │
│  冲突解决 ──▶ 记录解决日志                                                       │
│      │                                                                          │
│      ▼                                                                          │
│  审计追溯 ──▶ metadata/conflict_log.md                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 八、定期审计制度

### 8.1 审计周期

| 审计类型 | 周期 | 执行者 | 产出 |
|---------|------|-------|------|
| 日审计 | 每日 | QA Agent | 日审计报告 |
| 周审计 | 每周 | Main Agent | 周进度报告 |
| 月审计 | 每月 | Main Agent | 月度审计报告 |
| 发布审计 | 发布前 | QA Agent | 发布验收报告 |

### 8.2 审计内容

```markdown
## 日审计检查项

- [ ] 所有任务日志完整性
- [ ] 工作产出文件完整性
- [ ] Git提交与日志一致性
- [ ] 测试执行结果记录
- [ ] 问题清单更新状态
- [ ] 工作底稿归档状态

## 周审计检查项

- [ ] Agent注册表更新
- [ ] 任务分配表完整性
- [ ] 进度报告准确性
- [ ] 冲突解决记录
- [ ] 制度执行情况

## 月审计检查项

- [ ] 全量日志审计
- [ ] 工作产出质量评估
- [ ] Agent能力评估
- [ ] 制度优化建议
- [ ] 治理体系改进
```

---

## 九、制度执行监督

### 9.1 Main Agent监督职责

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Main Agent监督职责                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  监督一: Agent执行监督                                                           │
│  ├─ 检查Agent是否按职责执行                                                      │
│  ├─ 检查工作产出是否符合标准                                                     │
│  ├─ 检查工作底稿是否完整                                                         │
│                                                                                 │
│  监督二: 审计追溯监督                                                            │
│  ├─ 检查日志记录完整性                                                           │
│  ├─ 检查Git提交规范性                                                            │
│  ├─ 检查审计报告准确性                                                           │
│                                                                                 │
│  监督三: 制度执行监督                                                            │
│  ├─ 检查Agent是否遵守制度                                                        │
│  ├─ 检查工作流程是否规范                                                         │
│  ├─ 检查冲突解决是否合规                                                         │
│                                                                                 │
│  监督四: 问题处理监督                                                            │
│  ├─ 检查问题是否及时记录                                                         │
│  ├─ 检查问题是否及时解决                                                         │
│  ├─ 检查问题追溯是否完整                                                         │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 违规处理机制

| 违规类型 | 处理方式 |
|---------|---------|
| 未记录日志 | 强制补记录 + 警告 |
| 未按职责执行 | 任务重新分配 + 记录 |
| 工作产出缺失 | 要求补充 + 重新验收 |
| 冲突未解决 | Coordinator介入 + 记录 |

---

## 十、制度更新机制

### 10.1 更新触发条件

- Agent能力变化
- 任务类型新增
- 工作流程优化
- 审计发现问题
- 用户需求变化

### 10.2 更新流程

```
触发条件 ──▶ Main Agent评估 ──▶ 制度修订 ──▶ Agent通知 ──▶ 生效执行
```

---

## 十一、附录

### A. Main Agent工作日志模板

见: `/home/nvidia/workspace/paper/metadata/main_agent_log.md`

### B. 任务分配表模板

见: `/home/nvidia/workspace/paper/metadata/task_allocation.md`

### C. 审计报告模板

见: `/home/nvidia/workspace/paper/metadata/QA验收报告_模板.md`

---

**制度版本**: v1.0
**创建日期**: 2026-05-24
**维护Agent**: Main Agent
**下次审计**: 2026-05-25