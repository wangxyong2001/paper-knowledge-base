---
name: rag-llm-integration-gap
description: 当前 RAG Pipeline 缺失 LLM 生成解释阶段的问题分析与修复方案
metadata:
  type: feedback
---

# RAG Pipeline LLM 调用缺失问题分析

## Why: 当前 Pipeline 不调用 LLM

**根因**: 系统设计时预留了 LLM 接口，但先实现了规则简化版（截取前200字），等待后续接入。

**代码证据** (specialized_agents.py:389-410):
```python
def _generate_napkin_summary(self, query: str, context: str) -> str:
    """
    当前为简化实现，截取第一段前200字
    **未来可接入LLM生成更准确的摘要**  ← 注释明确说明
    """
    first_para = context.split("\n\n")[0]
    summary = first_para[:200] + "..."  # 只是截取，没有 LLM
    return summary
```

## How to apply: 修复方案

---

## 一、当前 vs 标准 RAG 流程对比

```
┌─────────────────────────────────────────────────────────────┐
│                   标准 RAG Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Query → 检索 → 重排序 → **LLM生成** → 输出                  │
│                          ↑                                  │
│                          关键阶段：解释检索内容               │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   当前实现 Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Query → 检索 → 重排序 → **规则截取** → 输出                  │
│                          ↑                                  │
│                          缺失 LLM 解释，只是截取前200字       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、修复方案：AnalysisAgent 接入 LLM

### 修改位置

**文件**: `vectordb/agents/specialized_agents.py`
**方法**: `PaperAnalysisAgent.analyze()`

### 修改代码

```python
class PaperAnalysisAgent:
    
    def __init__(
        self,
        registry: ToolRegistry,
        memory: Optional[PaperMemoryManager] = None,
        llm_client: Optional[DashScopeClientSync] = None,  # 新增参数
        enable_llm: bool = False  # 默认关闭，保持向后兼容
    ):
        self.registry = registry
        self.memory = memory
        self.llm_client = llm_client  # LLM 客户端
        self.enable_llm = enable_llm
    
    def analyze(self, query: str, chunks: List[Dict]) -> Dict:
        """分析论文内容"""
        context = self._assemble_context(chunks)
        
        # LLM 生成摘要（如启用）
        if self.enable_llm and self.llm_client:
            summary = self._generate_llm_summary(query, context)
        else:
            # 原规则截取（向后兼容）
            summary = self._generate_napkin_summary(query, context)
        
        formulas = self._extract_formulas(context)
        concepts = self._extract_concepts(context)
        code_design = self._extract_code_design(context)
        
        return {
            "query": query,
            "summary": summary,
            "concepts": concepts,
            "formulas": formulas,
            "code_design": code_design
        }
    
    def _generate_llm_summary(self, query: str, context: str) -> str:
        """使用 LLM 生成餐巾纸摘要"""
        
        prompt = f"""
        你是论文解读专家。请根据以下论文内容，用通俗语言回答用户问题。

        用户问题：{query}

        论文内容：
        {context[:3000]}  # 限制长度避免超 token

        要求：
        1. 用餐巾纸级别的简洁语言解释
        2. 核心概念用通俗比喻
        3. 关键公式用大白话解释
        4. 长度控制在300字左右

        输出格式：
        【一句话概括】...
        【核心思想】...
        【关键公式解释】...
        """
        
        # 调用云端 LLM
        result = self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            model="glm-5",
            max_tokens=500
        )
        
        # 记录审计日志
        if self.audit_logger:
            self.audit_logger.log_llm_call(
                provider="dashscope",
                model="glm-5",
                input_tokens=self._estimate_tokens(prompt),
                output_tokens=self._estimate_tokens(result.output)
            )
        
        return result.output
```

---

## 三、Orchestrator 调用方式

```python
class SpecializedAgentOrchestrator:
    
    def __init__(self, ..., enable_llm_analysis: bool = False):
        # 初始化 LLM 客户端
        if enable_llm_analysis:
            from api_client import DashScopeClientSync
            llm_client = DashScopeClientSync(
                api_key=os.getenv("DASHSCOPE_API_KEY")
            )
        else:
            llm_client = None
        
        # 初始化 Analysis Agent（带 LLM）
        self.analysis_agent = PaperAnalysisAgent(
            registry=registry,
            memory=memory,
            llm_client=llm_client,
            enable_llm=enable_llm_analysis  # 控制是否启用
        )
    
    def run_pipeline(
        self,
        query: str,
        top_k: int = 10,
        need_code: bool = False,
        enable_llm: bool = False  # 新参数，默认关闭
    ):
        """运行 Pipeline"""
        
        retrieval_result = self.retrieval_agent.retrieve(query, top_k)
        
        # LLM 分析（如启用）
        analysis_result = self.analysis_agent.analyze(
            query,
            retrieval_result["results"],
            # enable_llm 已在初始化时设置
        )
        
        qa_result = self.qa_agent.validate(
            analysis_result["summary"],
            retrieval_result["results"]
        )
        
        return {
            "retrieval": retrieval_result,
            "analysis": analysis_result,
            "qa": qa_result
        }
```

---

## 四、CLI 参数扩展

```bash
# 启用 LLM 解释
python vectordb/cli/main.py query "Transformer原理" --enable-llm

# 不启用（默认，规则截取）
python vectordb/cli/main.py query "Transformer原理"
```

---

## 五、SOLID 依据

| 原则 | 应用 |
|------|------|
| **O** - Open/Closed | 新增参数 `enable_llm`，不修改原有 `analyze()` 逻辑 |
| **D** - Dependency Inversion | AnalysisAgent 依赖 DashScopeClient 抽象，可替换 |

---

## 六、验收标准

| 测试 | 预期 |
|------|------|
| `enable_llm=False` | 保持原有规则截取行为 |
| `enable_llm=True` | 调用 glm-5 生成摘要 |
| 审计日志 | 记录 llm_calls 表 |

---

**文档状态**: 问题分析与修复方案
**优先级**: P0 - RAG 核心功能缺失

[[qa-agent-dual-model-config]]