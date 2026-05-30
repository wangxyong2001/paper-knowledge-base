# Code Reviewer Agent 知识库索引

> 版本: v1.0
> 日期: 2026-05-25

---

## 知识库结构

```
/home/nvidia/workspace/paper/knowledge/
└── google_eng_practices/
    ├── code_review_guide.md      # Google Code Review 最佳实践
    ├── README.md                 # 本索引文件
    └── (待扩展)                   # 其他最佳实践知识库
```

---

## 知识库清单

| 知识库 | 来源 | 用途 | Agent 角色 |
|-------|------|------|----------|
| Google Code Review | github.com/google/eng-practices | 代码审查技能 | QA Agent (Code Reviewer) |

---

## 知识库调用方式

### QA Agent 配置

```python
class QualityAssuranceAgent:
    KNOWLEDGE_BASE = {
        "google_code_review": "/home/nvidia/workspace/paper/knowledge/google_eng_practices/code_review_guide.md"
    }
    
    def load_review_knowledge(self) -> str:
        """加载 Code Review 知识库"""
        with open(self.KNOWLEDGE_BASE["google_code_review"]) as f:
            return f.read()
```

---

## 知识库更新机制

| 更新来源 | 更新频率 | 维护 Agent |
|---------|---------|-----------|
| Google GitHub 仓库 | 每月检查 | QA Agent |
| 内部最佳实践 | 按需更新 | Development Agent |

---

**维护责任**: QA Agent