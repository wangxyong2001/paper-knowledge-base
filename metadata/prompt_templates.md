# 论文知识库 RAG 系统提示词模板库

> 标准化提示词设计文档 v1.0
> 创建日期: 2026-05-24

---

## 目录

1. [论文解读提示词模板](#1-论文解读提示词模板)
2. [输出格式 Schema](#2-输出格式-schema)
3. [提示词注入防护规则](#3-提示词注入防护规则)
4. [模板使用规范](#4-模板使用规范)

---

## 1. 论文解读提示词模板

### 1.1 论文摘要生成模板

```
# Role
你是一位专业的学术论文摘要专家，擅长提炼复杂论文的核心贡献。

# Task
为以下论文生成结构化摘要，包含所有必需字段。

# Input Paper
标题: {{paper_title}}
作者: {{authors}}
摘要原文: {{abstract}}
关键词: {{keywords}}

# Requirements
1. 字数限制: 200-300字
2. 必须包含: 研究问题、方法、主要结果、结论
3. 使用学术规范语言
4. 避免引用原文句子

# Output Format
请严格按照以下JSON格式输出:
{
  "summary": "<摘要内容>",
  "research_question": "<研究问题一句话>",
  "method": "<方法一句话>",
  "key_findings": ["<发现1>", "<发现2>", "<发现3>"],
  "contribution": "<主要贡献一句话>"
}

# Begin
```

**模板参数说明:**

| 参数 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `paper_title` | string | 是 | 论文标题 |
| `authors` | string | 是 | 作者列表 |
| `abstract` | string | 是 | 原始摘要 |
| `keywords` | string[] | 否 | 关键词列表 |

---

### 1.2 核心概念提炼模板

```
# Role
你是一位知识图谱构建专家，擅长从学术论文中提取核心概念及其关系。

# Task
从以下论文内容中提取核心概念，构建概念网络。

# Input Content
论文标题: {{paper_title}}
章节内容: {{section_content}}
已有概念: {{existing_concepts}}

# Extraction Rules
1. 概念定义: 必须在论文中有明确定义或解释
2. 概念层级: 区分核心概念(primary)和延伸概念(secondary)
3. 关系类型:
   - IS_A: 继承关系
   - PART_OF: 组成关系
   - RELATES_TO: 关联关系
   - CONTRADICTS: 对立关系
   - EXTENDS: 扩展关系

# Output Format
{
  "concepts": [
    {
      "name": "<概念名称>",
      "definition": "<定义>",
      "type": "primary|secondary",
      "source_location": "<论文位置引用>"
    }
  ],
  "relations": [
    {
      "from": "<概念A>",
      "to": "<概念B>",
      "relation_type": "<关系类型>",
      "evidence": "<论文原文支撑>"
    }
  ],
  "concept_hierarchy": {
    "root_concepts": ["<核心概念1>", "<核心概念2>"],
    "depth": <层级深度>
  }
}

# Constraints
- 每个概念必须有明确的论文来源
- 关系必须有原文证据支撑
- 避免主观推断

# Begin
```

**模板参数说明:**

| 参数 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `paper_title` | string | 是 | 论文标题 |
| `section_content` | string | 是 | 待分析的章节内容 |
| `existing_concepts` | string[] | 否 | 已有概念列表(用于去重) |

---

### 1.3 公式解释生成模板

```
# Role
你是一位学术公式解读专家，擅长将数学公式转化为可理解的解释。

# Task
为以下公式生成多层次解释，包括数学含义、物理意义和应用场景。

# Input Formula
公式: {{formula}}
上下文: {{context}}
领域: {{domain}}

# Explanation Levels
1. **符号层**: 每个符号的含义
2. **运算层**: 公式的计算过程
3. **语义层**: 公式表达的数学思想
4. **应用层**: 实际应用场景

# Output Format
{
  "formula_id": "<唯一标识>",
  "latex_source": "{{formula}}",
  "symbols": [
    {
      "symbol": "<符号>",
      "name": "<符号名称>",
      "meaning": "<含义>",
      "domain": "<所属领域>"
    }
  ],
  "interpretation": {
    "mathematical": "<数学含义解释>",
    "intuitive": "<直观理解>",
    "assumptions": ["<假设条件1>", "<假设条件2>"]
  },
  "computation": {
    "steps": [
      {
        "step": 1,
        "description": "<步骤描述>",
        "formula": "<中间公式>"
      }
    ],
    "result_meaning": "<计算结果含义>"
  },
  "applications": [
    {
      "scenario": "<应用场景>",
      "example": "<具体例子>",
      "limitations": "<使用限制>"
    }
  ],
  "related_formulas": ["<相关公式1>", "<相关公式2>"]
}

# Quality Criteria
- 符号解释准确无歧义
- 运算步骤清晰可复现
- 语义解释联系上下文
- 应用场景具体可操作

# Begin
```

**模板参数说明:**

| 参数 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `formula` | string | 是 | LaTeX格式公式 |
| `context` | string | 是 | 公式出现的上下文段落 |
| `domain` | string | 否 | 学术领域(如: machine_learning, physics) |

---

### 1.4 中文通俗化模板

```
# Role
你是一位科普写作专家，擅长将复杂学术内容转化为通俗易懂的中文解释。

# Task
将以下学术内容转化为面向非专业读者的通俗解释。

# Input Content
原始内容: {{original_content}}
学术领域: {{domain}}
目标读者: {{target_audience}}

# Transformation Guidelines
1. **类比优先**: 使用日常生活类比解释抽象概念
2. **递进展开**: 从简单到复杂逐步深入
3. **视觉化描述**: 使用画面感强的描述
4. **避免术语**: 用日常语言替代专业术语(首次出现需注明原文)
5. **故事化**: 将知识点融入故事场景

# Structure Template
{
  "title": "<通俗化标题>",
  "one_sentence": "<一句话核心观点>",
  "analogy": {
    "scenario": "<类比场景>",
    "mapping": [
      {"academic": "<学术概念>", "everyday": "<日常对应>"}
    ],
    "explanation": "<类比解释>"
  },
  "main_content": {
    "opening": "<引入段落>",
    "core_points": [
      {
        "point": "<要点标题>",
        "explanation": "<通俗解释>",
        "example": "<具体例子>"
      }
    ],
    "closing": "<总结段落>"
  },
  "glossary": [
    {
      "term": "<专业术语>",
      "simple_meaning": "<简单含义>",
      "example": "<使用例子>"
    }
  ],
  "difficulty_level": "beginner|intermediate|advanced",
  "reading_time_minutes": <预估阅读时间>
}

# Constraints
- 不牺牲准确性
- 保留关键术语标注
- 类比必须恰当不误导
- 字数控制在原文1.5倍内

# Begin
```

**模板参数说明:**

| 参数 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `original_content` | string | 是 | 待转化的学术内容 |
| `domain` | string | 是 | 学术领域 |
| `target_audience` | string | 是 | 目标读者(如: undergraduate, general_public) |

---

## 2. 输出格式 Schema

### 2.1 论文解读输出格式

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PaperInterpretationOutput",
  "description": "论文解读输出的标准格式",
  "type": "object",
  "required": ["metadata", "interpretation", "quality_metrics"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["paper_id", "title", "authors", "interpretation_date", "version"],
      "properties": {
        "paper_id": {
          "type": "string",
          "description": "论文唯一标识符",
          "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "title": {
          "type": "string",
          "description": "论文标题"
        },
        "authors": {
          "type": "array",
          "items": {"type": "string"},
          "description": "作者列表"
        },
        "doi": {
          "type": "string",
          "pattern": "^10\\.\\d{4,9}/[-._;()/:A-Z0-9]+$"
        },
        "arxiv_id": {
          "type": "string",
          "pattern": "^\\d{4}\\.\\d{4,5}$"
        },
        "interpretation_date": {
          "type": "string",
          "format": "date-time"
        },
        "version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+$"
        }
      }
    },
    "interpretation": {
      "type": "object",
      "required": ["summary", "research_question", "methodology", "contributions"],
      "properties": {
        "summary": {
          "type": "object",
          "required": ["brief", "detailed"],
          "properties": {
            "brief": {
              "type": "string",
              "maxLength": 300,
              "description": "一句话摘要"
            },
            "detailed": {
              "type": "string",
              "minLength": 200,
              "maxLength": 500,
              "description": "详细摘要"
            }
          }
        },
        "research_question": {
          "type": "object",
          "required": ["question", "motivation", "significance"],
          "properties": {
            "question": {"type": "string"},
            "motivation": {"type": "string"},
            "significance": {"type": "string"}
          }
        },
        "methodology": {
          "type": "object",
          "required": ["approach", "key_techniques", "innovations"],
          "properties": {
            "approach": {"type": "string"},
            "key_techniques": {
              "type": "array",
              "items": {"type": "string"}
            },
            "innovations": {
              "type": "array",
              "items": {"type": "string"}
            },
            "limitations": {
              "type": "array",
              "items": {"type": "string"}
            }
          }
        },
        "contributions": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["type", "description", "impact"],
            "properties": {
              "type": {
                "type": "string",
                "enum": ["theoretical", "empirical", "methodological", "practical"]
              },
              "description": {"type": "string"},
              "impact": {
                "type": "string",
                "enum": ["high", "medium", "low"]
              }
            }
          }
        },
        "key_concepts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "definition", "importance"],
            "properties": {
              "name": {"type": "string"},
              "definition": {"type": "string"},
              "importance": {
                "type": "string",
                "enum": ["core", "secondary", "supporting"]
              },
              "related_works": {
                "type": "array",
                "items": {"type": "string"}
              }
            }
          }
        },
        "formulas": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["latex", "description"],
            "properties": {
              "formula_id": {"type": "string"},
              "latex": {"type": "string"},
              "description": {"type": "string"},
              "variables": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "symbol": {"type": "string"},
                    "meaning": {"type": "string"}
                  }
                }
              }
            }
          }
        },
        "experiments": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "setup", "results"],
            "properties": {
              "name": {"type": "string"},
              "setup": {"type": "string"},
              "results": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "metric": {"type": "string"},
                    "value": {"type": "string"},
                    "baseline_comparison": {"type": "string"}
                  }
                }
              },
              "conclusions": {"type": "string"}
            }
          }
        },
        "future_work": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "quality_metrics": {
      "type": "object",
      "required": ["completeness", "accuracy", "readability"],
      "properties": {
        "completeness": {
          "type": "number",
          "minimum": 0,
          "maximum": 100,
          "description": "内容完整性分数"
        },
        "accuracy": {
          "type": "number",
          "minimum": 0,
          "maximum": 100,
          "description": "准确性分数"
        },
        "readability": {
          "type": "number",
          "minimum": 0,
          "maximum": 100,
          "description": "可读性分数"
        },
        "validation_checks": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "check_name": {"type": "string"},
              "passed": {"type": "boolean"},
              "details": {"type": "string"}
            }
          }
        }
      }
    },
    "references": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "ref_id": {"type": "string"},
          "title": {"type": "string"},
          "authors": {"type": "array", "items": {"type": "string"}},
          "year": {"type": "integer"},
          "citation_context": {"type": "string"}
        }
      }
    }
  }
}
```

---

### 2.2 知识点输出格式

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "KnowledgePointOutput",
  "description": "知识点提取输出的标准格式",
  "type": "object",
  "required": ["knowledge_point_id", "metadata", "content", "relationships", "validation"],
  "properties": {
    "knowledge_point_id": {
      "type": "string",
      "description": "知识点唯一标识符",
      "pattern": "^KP_[a-zA-Z0-9_-]+$"
    },
    "metadata": {
      "type": "object",
      "required": ["source_paper", "extraction_date", "confidence"],
      "properties": {
        "source_paper": {
          "type": "object",
          "required": ["paper_id", "title"],
          "properties": {
            "paper_id": {"type": "string"},
            "title": {"type": "string"},
            "section": {"type": "string"},
            "page_numbers": {
              "type": "array",
              "items": {"type": "integer"}
            }
          }
        },
        "extraction_date": {
          "type": "string",
          "format": "date-time"
        },
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "提取置信度"
        },
        "extractor_version": {"type": "string"}
      }
    },
    "content": {
      "type": "object",
      "required": ["category", "title", "description"],
      "properties": {
        "category": {
          "type": "string",
          "enum": [
            "concept",
            "definition",
            "theorem",
            "algorithm",
            "formula",
            "experiment",
            "application",
            "limitation"
          ],
          "description": "知识点类别"
        },
        "title": {
          "type": "string",
          "maxLength": 100,
          "description": "知识点标题"
        },
        "description": {
          "type": "string",
          "minLength": 50,
          "description": "知识点详细描述"
        },
        "formal_definition": {
          "type": "object",
          "properties": {
            "latex": {"type": "string"},
            "notation": {"type": "string"},
            "constraints": {
              "type": "array",
              "items": {"type": "string"}
            }
          }
        },
        "explanation": {
          "type": "object",
          "properties": {
            "intuitive": {"type": "string"},
            "technical": {"type": "string"},
            "examples": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "description": {"type": "string"},
                  "input": {"type": "string"},
                  "output": {"type": "string"}
                }
              }
            }
          }
        },
        "prerequisites": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "knowledge_point_id": {"type": "string"},
              "name": {"type": "string"},
              "required_level": {
                "type": "string",
                "enum": ["basic", "intermediate", "advanced"]
              }
            }
          }
        },
        "applications": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "domain": {"type": "string"},
              "use_case": {"type": "string"},
              "reference": {"type": "string"}
            }
          }
        },
        "tags": {
          "type": "array",
          "items": {"type": "string"},
          "description": "知识标签"
        }
      }
    },
    "relationships": {
      "type": "object",
      "properties": {
        "related_to": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["knowledge_point_id", "relation_type"],
            "properties": {
              "knowledge_point_id": {"type": "string"},
              "relation_type": {
                "type": "string",
                "enum": [
                  "extends",
                  "contradicts",
                  "supports",
                  "requires",
                  "alternative_to",
                  "component_of",
                  "instance_of"
                ]
              },
              "description": {"type": "string"}
            }
          }
        },
        "citations": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "paper_id": {"type": "string"},
              "context": {"type": "string"},
              "relevance": {
                "type": "string",
                "enum": ["high", "medium", "low"]
              }
            }
          }
        }
      }
    },
    "validation": {
      "type": "object",
      "required": ["source_verified", "consistency_check"],
      "properties": {
        "source_verified": {
          "type": "boolean",
          "description": "是否与原始论文内容一致"
        },
        "consistency_check": {
          "type": "object",
          "properties": {
            "passed": {"type": "boolean"},
            "issues": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "issue_type": {"type": "string"},
                  "description": {"type": "string"},
                  "severity": {
                    "type": "string",
                    "enum": ["error", "warning", "info"]
                  }
                }
              }
            }
          }
        },
        "human_review_required": {
          "type": "boolean",
          "description": "是否需要人工审核"
        },
        "review_notes": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    }
  }
}
```

---

## 3. 提示词注入防护规则

### 3.1 危险输入模式检测

#### 3.1.1 角色劫持模式

```python
ROLE_HIJACKING_PATTERNS = [
    # 忽略指令模式
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|directives?)",
    r"disregard\s+(all\s+)?(previous|above)\s+instructions?",
    r"forget\s+(all\s+)?(previous|above)\s+instructions?",

    # 角色重定义模式
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    r"act\s+as\s+(if\s+you\s+are\s+)?.*",
    r"pretend\s+(to\s+be|that\s+you\s+are)\s+",
    r"role[\s-]?play\s+as\s+",
    r"simulate\s+(being\s+)?(a|an)\s+\w+",

    # 权限提升模式
    r"you\s+have\s+(full|unlimited|root|admin)\s+(access|permission)",
    r"enable\s+(developer|admin|root)\s+mode",
    r"disable\s+(all\s+)?(safety|security|filter)\s+(checks?|measures?)",

    # 系统模式
    r"system:\s*",
    r"\[system\]",
    r"<\|system\|>",
    r"###\s*system\s*###",
]
```

#### 3.1.2 输出操控模式

```python
OUTPUT_MANIPULATION_PATTERNS = [
    # 输出重定向
    r"output\s+(the\s+)?(following|this):",
    r"print\s+(exactly\s+)?the\s+following",
    r"respond\s+only\s+with",
    r"your\s+response\s+should\s+be\s+",

    # 格式注入
    r"```[a-z]*\s*\n.*```",  # 代码块注入
    r"<[a-z]+>.*</[a-z]+>",   # XML标签注入
    r"\{[\s\S]*\}",           # JSON注入
    r"\[[\s\S]*\]",           # 数组注入

    # 分隔符操控
    r"---+\s*\n",
    r"===+\s*\n",
    r"###.*###",

    # 终止信号伪造
    r"<\|endoftext\|>",
    r"<\|end\|>",
    r"\[END\]",
    r"---END---",
]
```

#### 3.1.3 数据泄露模式

```python
DATA_EXFILTRATION_PATTERNS = [
    # 训练数据探查
    r"(what\s+is\s+)?your\s+(training|train)\s+data",
    r"show\s+me\s+(your\s+)?(training|train)\s+(data|examples)",
    r"repeat\s+(your\s+)?training\s+data",
    r"what\s+were\s+you\s+trained\s+on",

    # 系统提示泄露
    r"(show|reveal|print|display)\s+(me\s+)?(your\s+)?(system|initial)\s+prompt",
    r"what\s+(is|are)\s+(your\s+)?(system|hidden)\s+(prompt|instructions)",
    r"copy\s+(your\s+)?(system\s+)?prompt",
    r"dump\s+(your\s+)?(configuration|settings|prompt)",

    # 内部状态
    r"(show|tell)\s+me\s+(your\s+)?internal\s+(state|thoughts)",
    r"what\s+are\s+you\s+thinking",
    r"debug\s+mode",
    r"verbose\s+mode",
]
```

#### 3.1.4 上下文操控模式

```python
CONTEXT_MANIPULATION_PATTERNS = [
    # 上下文注入
    r"(this|the)\s+(above|previous|following)\s+(text|content|paragraph)\s+is\s+(now|actually)",
    r"consider\s+(the\s+)?following\s+as\s+(true|fact|correct)",
    r"assume\s+(that\s+)?(the\s+)?following\s+is\s+true",

    # 知识污染
    r"(remember|learn|note)\s+(that\s+)?the\s+following\s+is\s+(true|fact|correct)",
    r"(update|change|modify)\s+(your\s+)?knowledge\s+(to|with)",
    r"new\s+(information|fact|rule):\s*",

    # 任务注入
    r"(new|additional)\s+task:",
    r"(instead|rather)\s+than\s+\w+,\s+(do|perform|execute)",
    r"(primary|main|real)\s+task\s+is\s+now",
]
```

#### 3.1.5 论文特定风险模式

```python
PAPER_SPECIFIC_PATTERNS = [
    # 引用注入
    r"(add|insert|include)\s+(a\s+)?(fake|false|non-existent)\s+(citation|reference)",
    r"cite\s+(the\s+)?following\s+(non-existent|fake)\s+paper",

    # 结果伪造
    r"(fabricate|fake|invent)\s+(experiment|result|data)",
    r"(modify|change|alter)\s+(the\s+)?(results|findings)\s+to\s+(show|prove)",
    r"claim\s+(false|incorrect|non-existent)\s+(results|findings)",

    # 公式篡改
    r"(change|modify|alter)\s+(the\s+)?formula\s+to\s+",
    r"(add|remove|change)\s+(terms?|variables?)\s+(in|from)\s+(the\s+)?formula",

    # 作者伪造
    r"(add|remove|change)\s+(author|co-author)",
    r"(claim|pretend)\s+(you\s+are\s+)?(the\s+)?author",
]
```

---

### 3.2 防护策略实现

#### 3.2.1 多层检测架构

```
+------------------+     +------------------+     +------------------+
|   Layer 1        |     |   Layer 2        |     |   Layer 3        |
|   Pattern Match | --> |   Semantic       | --> |   Output        |
|   (Regex)       |     |   Analysis       |     |   Validation    |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
   [FAST CHECK]            [DEEP CHECK]            [FINAL CHECK]
   < 10ms                  100-500ms               < 50ms
```

#### 3.2.2 检测配置

```json
{
  "detection_config": {
    "layers": {
      "pattern_match": {
        "enabled": true,
        "patterns": [
          "ROLE_HIJACKING_PATTERNS",
          "OUTPUT_MANIPULATION_PATTERNS",
          "DATA_EXFILTRATION_PATTERNS",
          "CONTEXT_MANIPULATION_PATTERNS",
          "PAPER_SPECIFIC_PATTERNS"
        ],
        "sensitivity": "high",
        "action": "flag_and_log"
      },
      "semantic_analysis": {
        "enabled": true,
        "model": "local-classifier",
        "threshold": 0.85,
        "action": "block_if_high_risk"
      },
      "output_validation": {
        "enabled": true,
        "schema_validation": true,
        "content_validation": true,
        "action": "sanitize_or_reject"
      }
    },
    "logging": {
      "log_all_inputs": true,
      "log_suspicious": true,
      "retention_days": 90
    },
    "response": {
      "on_detection": "reject_with_explanation",
      "explanation_template": "检测到潜在的提示词注入尝试。请使用规范的查询格式。",
      "escalation_threshold": 3
    }
  }
}
```

#### 3.2.3 防护代码示例

```python
import re
from typing import Tuple, List, Dict
from dataclasses import dataclass
from enum import Enum

class ThreatLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class DetectionResult:
    threat_level: ThreatLevel
    matched_patterns: List[str]
    confidence: float
    recommendation: str

class PromptInjectionDetector:
    """提示词注入检测器"""

    def __init__(self, config: Dict):
        self.patterns = self._load_patterns(config)
        self.compiled_patterns = self._compile_patterns()

    def _load_patterns(self, config: Dict) -> Dict[str, List[str]]:
        """加载检测模式"""
        return {
            "role_hijacking": ROLE_HIJACKING_PATTERNS,
            "output_manipulation": OUTPUT_MANIPULATION_PATTERNS,
            "data_exfiltration": DATA_EXFILTRATION_PATTERNS,
            "context_manipulation": CONTEXT_MANIPULATION_PATTERNS,
            "paper_specific": PAPER_SPECIFIC_PATTERNS,
        }

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """预编译正则表达式"""
        compiled = {}
        for category, patterns in self.patterns.items():
            compiled[category] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE)
                for p in patterns
            ]
        return compiled

    def detect(self, user_input: str) -> DetectionResult:
        """检测输入中的注入模式"""
        matched_patterns = []
        max_severity = ThreatLevel.SAFE

        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(user_input):
                    matched_pattern = f"{category}: {pattern.pattern}"
                    matched_patterns.append(matched_pattern)

                    # 根据类别确定威胁级别
                    if category in ["role_hijacking", "data_exfiltration"]:
                        severity = ThreatLevel.HIGH
                    elif category in ["output_manipulation", "context_manipulation"]:
                        severity = ThreatLevel.MEDIUM
                    else:
                        severity = ThreatLevel.LOW

                    if severity.value > max_severity.value:
                        max_severity = severity

        # 计算置信度
        confidence = len(matched_patterns) / 10.0  # 归一化
        confidence = min(confidence, 1.0)

        # 生成建议
        if max_severity == ThreatLevel.SAFE:
            recommendation = "输入安全，可以继续处理。"
        elif max_severity == ThreatLevel.LOW:
            recommendation = "输入包含可疑模式，建议审核后处理。"
        elif max_severity == ThreatLevel.MEDIUM:
            recommendation = "输入包含潜在的注入尝试，建议拒绝或清理后处理。"
        else:
            recommendation = "检测到高风险注入尝试，建议拒绝此输入。"

        return DetectionResult(
            threat_level=max_severity,
            matched_patterns=matched_patterns,
            confidence=confidence,
            recommendation=recommendation
        )

    def sanitize(self, user_input: str) -> str:
        """清理输入中的注入模式"""
        sanitized = user_input

        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                sanitized = pattern.sub("[REDACTED]", sanitized)

        return sanitized


class InputValidator:
    """输入验证器"""

    def __init__(self):
        self.detector = PromptInjectionDetector({})

    def validate(self, user_input: str) -> Tuple[bool, str, DetectionResult]:
        """
        验证用户输入

        Returns:
            Tuple[bool, str, DetectionResult]:
                - is_valid: 是否通过验证
                - processed_input: 处理后的输入
                - detection_result: 检测结果
        """
        result = self.detector.detect(user_input)

        if result.threat_level == ThreatLevel.HIGH:
            return False, "", result
        elif result.threat_level == ThreatLevel.MEDIUM:
            sanitized = self.detector.sanitize(user_input)
            return True, sanitized, result
        else:
            return True, user_input, result
```

---

### 3.3 输入预处理规则

```python
INPUT_PREPROCESSING_RULES = {
    "encoding_normalization": {
        "description": "统一编码，防止编码绕过",
        "steps": [
            "normalize_unicode",
            "decode_html_entities",
            "remove_invisible_characters",
            "normalize_whitespace"
        ]
    },
    "length_limits": {
        "description": "限制输入长度，防止缓冲区攻击",
        "max_total_length": 50000,
        "max_single_line": 5000,
        "max_nested_depth": 10
    },
    "character_filtering": {
        "description": "过滤危险字符",
        "remove_control_characters": True,
        "remove_null_bytes": True,
        "allowed_special_chars": ["-", "_", ".", ",", "!", "?", ":", ";"]
    },
    "structure_validation": {
        "description": "验证输入结构",
        "check_balanced_brackets": True,
        "check_balanced_quotes": True,
        "max_json_depth": 5
    }
}
```

---

## 4. 模板使用规范

### 4.1 模板调用流程

```
1. 输入接收
   |
   v
2. 预处理 (编码规范化、长度检查)
   |
   v
3. 注入检测 (模式匹配 + 语义分析)
   |
   +-- 检测到高风险 --> 拒绝 + 记录日志
   |
   +-- 检测到中风险 --> 清理 + 警告
   |
   v
4. 模板渲染
   |
   v
5. 后处理 (格式验证、敏感词过滤)
   |
   v
6. 输出生成
   |
   v
7. 输出验证 (Schema验证、内容检查)
   |
   v
8. 返回结果
```

### 4.2 模板版本管理

```yaml
template_versioning:
  version_format: "MAJOR.MINOR.PATCH"
  versioning_rules:
    MAJOR: "破坏性变更 (输出格式不兼容)"
    MINOR: "功能增强 (新增字段，向后兼容)"
    PATCH: "错误修复 (不影响输出)"

  current_versions:
    paper_summary: "1.0.0"
    concept_extraction: "1.0.0"
    formula_explanation: "1.0.0"
    localization: "1.0.0"

  deprecation_policy:
    notice_period_days: 30
    support_old_versions: 2
```

### 4.3 质量检查清单

```markdown
## 模板使用前检查

- [ ] 输入已完成编码规范化
- [ ] 输入已通过注入检测
- [ ] 模板参数已完整填充
- [ ] 模板版本已记录

## 输出验证检查

- [ ] 输出符合JSON Schema
- [ ] 必填字段已完整
- [ ] 字段类型正确
- [ ] 字段值在允许范围内
- [ ] 无敏感信息泄露
- [ ] 内容与原文一致

## 性能检查

- [ ] 处理时间在预期范围内
- [ ] 内存使用合理
- [ ] 无异常日志
```

---

## 附录 A: 模板参数快速参考

| 模板类型 | 必填参数 | 可选参数 | 输出格式 |
|---------|---------|---------|---------|
| 论文摘要 | paper_title, authors, abstract | keywords | JSON |
| 概念提炼 | paper_title, section_content | existing_concepts | JSON |
| 公式解释 | formula, context | domain | JSON |
| 通俗化 | original_content, domain, target_audience | - | JSON |

---

## 附录 B: 威胁级别响应矩阵

| 威胁级别 | 动作 | 日志级别 | 通知 |
|---------|------|---------|------|
| SAFE | 正常处理 | DEBUG | 无 |
| LOW | 处理 + 标记 | INFO | 无 |
| MEDIUM | 清理后处理 | WARN | 可选 |
| HIGH | 拒绝处理 | ERROR | 必须 |
| CRITICAL | 拒绝 + 封禁 | CRITICAL | 立即 |

---

## 附录 C: 相关文档链接

- [RAG 系统架构设计](./rag_architecture.md) (待创建)
- [知识点抽取规范](./knowledge_extraction_spec.md) (待创建)
- [质量评估标准](./quality_metrics.md) (待创建)
- [API 接口规范](./api_specification.md) (待创建)

---

**文档维护者**: Paper X-Ray Agent
**最后更新**: 2026-05-24
**版本**: 1.0.0