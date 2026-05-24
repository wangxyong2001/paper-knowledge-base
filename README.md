# 论文知识库系统

> 个人/团队知识基础设施，全流程透明可控

## 项目概述

分析87+论文 → 中文通俗解读 → 向量存储 → 语义检索 → 知识复用 → 透明治理

## 核心功能

### 已完成模块 ✓

| 模块 | 功能 | 状态 |
|-----|------|------|
| 审计日志系统 | SQLite 14表，全流程追溯 | ✓ |
| Prompt模板管理 | CalVer版本 + Anti-Lost优化 | ✓ |
| 注入防御 | 5类攻击检测 | ✓ |
| 监测指标 | 30+指标6层 + 告警 | ✓ |
| API客户端 | DashScope + Token审计 | ✓ |
| 向量检索 | ChromaDB + BM25 + RRF | ✓ |
| Agent框架 | LangGraph实现 | ✓ |

### 待开发模块 ⏳

- MemoryManager（三层记忆）
- ToolRegistry（统一接口）
- 四角色Agent（检索/解读/质量/复现）
- CLI交互界面
- WebUI Dashboard

## 目录结构

```
paper/
├── metadata/           # 需求文档、架构设计
├── vectordb/           # 核心代码实现
│   ├── database/       # Schema + 审计日志
│   ├── core/           # Prompt/输出/指标/API
│   ├── agents/         # LangGraph Agent
│   ├── tests/          # 集成测试
│   └── scripts/        # 入库/检索脚本
└── analyses/           # 论文分析结果
```

## 快速开始

```bash
# 安装依赖
cd vectordb
pip install -r requirements.txt

# 运行集成测试
python tests/integration_test.py

# 初始化数据库
python scripts/init_db.py
```

## 技术栈

- 向量数据库: ChromaDB
- 嵌入模型: BGE-M3
- 检索: Vector + BM25 + RRF融合
- LLM: DashScope API + 本地Ollama
- Agent框架: LangGraph
- 审计存储: SQLite

## hello-agents融合

本项目融合hello-agents学习成果：
- ReAct循环 → Agent推理框架
- MemoryManager → 三层记忆系统
- ToolRegistry → 统一工具接口
- Pipeline编排 → 工作流标准化
- 降级策略 → 网络韧性保障

## 文档

- [需求一页纸](metadata/paper_knowledge_system_requirements_onepage.md)
- [治理框架设计](metadata/governance_framework_design.md)
- [Agent落地方案](metadata/paper_rag_agent_implementation_plan.md)
- [架构审核报告](metadata/architecture_review_audit.md)

## 进度

```
整体进度: 40%
Layer 1 基础设施: 100% ✓
Layer 2 透明治理: 100% ✓
Layer 3 Agent智能: 25% ⏳
Layer 4 用户交互: 0% ⏳
```

## License

MIT

---

*更新日期: 2026-05-24*