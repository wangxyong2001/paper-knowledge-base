---
name: qa-agent-dual-model-config
description: QA Agent 双模型配置方案 - 云端默认 + 本地 Code Review
metadata:
  type: project
---

# QA Agent 双模型配置方案

## 需求背景

QA Agent 当前只有规则工具验证（幻觉检测、引用检查），无 LLM 能力。
用户需求：
- 默认任务：使用云端 glm-5
- Code Review：使用本地 qwen3.5-9b-reviewer

## 设计原则

**Why**: QA Agent 需要 LLM 增强验证能力，但不能影响现有 validate() 规则检查。
**How to apply**: 新增方法，不修改现有代码，通过参数控制启用。

---

## 一、架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                   QualityAssuranceAgent                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐                                          │
│  │ 初始化参数    │                                          │
│  │ cloud_client  │───▶ DashScopeClient(glm-5)              │
│  │ local_model   │───▶ "qwen3.5-9b-reviewer"               │
│  │ registry      │───▶ 工具注册(现有)                       │
│  └───────────────┘                                          │
│                                                             │
│  ┌───────────────┐    ┌───────────────┐    ┌────────────┐   │
│  │ validate()    │    │ llm_validate()│    │ code_review│   │
│  │ (现有-不改)  │    │ (新增-云端)   │    │ (新增-本地)│   │
│  │ 规则工具     │    │ glm-5增强     │    │ 小LLM审查 │   │
│  └───────────────┘    └───────────────┘    └────────────┘   │
│        ✓                    ⏳ 待实现           ⏳ 待实现     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、初始化签名

```python
class QualityAssuranceAgent:
    def __init__(
        self,
        registry: ToolRegistry,
        memory: Optional[PaperMemoryManager] = None,
        # 新增参数 (可选，默认 None 不启用)
        cloud_client: Optional[DashScopeClient] = None,  # 云端大 LLM
        local_model: str = "qwen3.5-9b-reviewer",        # 本地 Code Review
        ollama_base_url: str = "http://localhost:11434"
    ):
        self.registry = registry
        self.memory = memory
        
        # 双模型配置 (可选)
        self.cloud_client = cloud_client  # 云端 glm-5
        self.local_model = local_model    # 本地小 LLM
        self.ollama_base_url = ollama_base_url
```

---

## 三、新增方法设计

### 3.1 llm_validate() - 云端 LLM 增强验证

**用途**: 当规则工具验证结果不确定时，调用云端 glm-5 进行二次验证。

```python
async def llm_validate(
    self,
    output: str,
    chunks: List[Dict],
    rule_result: Optional[Dict] = None  # 可选：先运行规则检查
) -> Dict:
    """
    云端 LLM 增强验证
    
    Args:
        output: 待验证输出
        chunks: 支撑上下文
        rule_result: 规则检查结果 (可选)
    
    Returns:
        {
            "llm_quality_score": LLM评分,
            "reasoning": 验证推理过程,
            "issues_found": 发现的问题列表,
            "confidence": 置信度
        }
    
    触发条件:
        - 规则检查 quality_score < 0.7 时自动调用
        - 或用户显式请求 LLM 验证
    """
    if self.cloud_client is None:
        return {"error": "cloud_client not configured"}
    
    # 构造验证 Prompt
    contexts = [c.get("content", "") for c in chunks]
    prompt = f"""
    你是质量审核专家。验证以下输出的准确性和可信度。
    
    输出内容：
    {output}
    
    参考上下文：
    {contexts[:3]}  # 最多3个chunk
    
    检查项：
    1. 内容是否被上下文支撑
    2. 是否有虚假信息或过度推断
    3. 引用标记是否准确对应
    
    输出格式（JSON）：
    {{
        "quality_score": 0-1评分,
        "issues": ["问题列表"],
        "reasoning": "推理过程"
    }}
    """
    
    # 调用云端 glm-5
    result = await self.cloud_client.chat(
        messages=[{"role": "user", "content": prompt}],
        model="glm-5"
    )
    
    return self._parse_llm_result(result.output)
```

### 3.2 code_review() - 本地小 LLM 代码审查

**用途**: 审查 CodeReproductionAgent 生成的代码质量。

```python
async def code_review(
    self,
    code_content: str,
    paper_context: str,
    enable_local: bool = True  # 默认用本地，可切换云端
) -> Dict:
    """
    代码质量审查
    
    Args:
        code_content: 待审查代码
        paper_context: 论文上下文 (算法描述)
        enable_local: True=本地小LLM, False=云端大LLM
    
    Returns:
        {
            "review_score": 代码质量评分,
            "logic_check": 逻辑一致性检查,
            "dimension_check": 张量维度检查,
            "suggestions": 改进建议,
            "backend_used": "local" | "cloud"
        }
    """
    
    review_prompt = f"""
    你是代码审查专家。检查以下代码是否正确实现论文算法。
    
    论文算法描述：
    {paper_context}
    
    生成的代码：
    {code_content}
    
    审查项：
    1. 【逻辑一致性】代码逻辑是否与论文描述一致
    2. 【张量维度】矩阵运算维度是否正确 (如 [B,T,C] vs [B,C,T])
    3. 【变量命名】命名是否清晰反映论文概念
    4. 【边界情况】是否处理了论文提到的特殊情况
    
    输出格式（JSON）：
    {{
        "score": 0-10评分,
        "logic_ok": true/false,
        "dimension_ok": true/false,
        "issues": ["问题列表"],
        "fix_suggestions": ["修复建议"]
    }}
    """
    
    if enable_local and self.local_model:
        # 本地小 LLM (qwen3.5-9b-reviewer)
        return await self._call_local_llm(review_prompt)
    elif self.cloud_client:
        # 云端大 LLM (glm-5)
        result = await self.cloud_client.chat(
            messages=[{"role": "user", "content": review_prompt}],
            model="glm-5"
        )
        return {"backend_used": "cloud", **self._parse_review_result(result.output)}
    else:
        return {"error": "no LLM backend configured"}

async def _call_local_llm(self, prompt: str) -> Dict:
    """调用本地 Ollama"""
    import aiohttp
    
    url = f"{self.ollama_base_url}/api/generate"
    payload = {
        "model": self.local_model,
        "prompt": prompt,
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            return {
                "backend_used": "local",
                "model": self.local_model,
                **self._parse_review_result(data.get("response", ""))
            }
```

---

## 四、Orchestrator 集成方式

**原则**: 新方法可选调用，不改变现有流程。

```python
class SpecializedAgentOrchestrator:
    
    async def run_pipeline(self, query: str, enable_llm_validate=False, enable_code_review=False):
        
        # Stage 1-3: 现有流程不变
        retrieval_result = await self.retrieval_agent.retrieve(query)
        analysis_result = await self.analysis_agent.analyze(retrieval_result)
        
        # Stage 3.5: QA验证 (现有 + 可选LLM增强)
        qa_result = self.qa_agent.validate(analysis_result["output"], retrieval_result["results"])
        
        if enable_llm_validate and qa_result["quality_score"] < 0.7:
            # 规则检查不达标时，调用云端LLM二次验证
            llm_qa_result = await self.qa_agent.llm_validate(
                analysis_result["output"],
                retrieval_result["results"],
                rule_result=qa_result
            )
            qa_result["llm_validation"] = llm_qa_result
        
        # Stage 4: 代码生成
        code_result = await self.code_agent.generate(analysis_result)
        
        # Stage 4.5: 代码审查 (可选)
        if enable_code_review:
            review_result = await self.qa_agent.code_review(
                code_result["code"],
                analysis_result["algorithm_desc"],
                enable_local=True  # 默认用本地小LLM
            )
            code_result["review"] = review_result
        
        return {
            "retrieval": retrieval_result,
            "analysis": analysis_result,
            "qa": qa_result,
            "code": code_result
        }
```

---

## 五、调用矩阵

| 场景 | 方法 | 后端 | 模型 | 触发条件 |
|------|------|------|------|---------|
| 规则验证 | `validate()` | 无LLM | 规则工具 | 默认总是执行 |
| LLM增强验证 | `llm_validate()` | 云端 | glm-5 | quality_score < 0.7 时 |
| 代码审查 | `code_review(enable_local=True)` | 本地 | qwen3.5-9b | enable_code_review=True |
| 代码审查(云端) | `code_review(enable_local=False)` | 云端 | glm-5 | 复杂代码/本地失败时 |

---

## 六、实施步骤

| 步骤 | 内容 | 预估工期 | 影响范围 |
|------|------|---------|---------|
| 1 | QA Agent 初始化参数扩展 | 0.5天 | 仅新增参数，不影响现有调用 |
| 2 | 实现 `llm_validate()` 方法 | 1天 | 新方法，独立实现 |
| 3 | 实现 `code_review()` 方法 | 1天 | 新方法，含本地调用 |
| 4 | Orchestrator 可选参数 | 0.5天 | 新参数默认 False |
| 5 | 单元测试 | 1天 | 独立测试文件 |

**总计**: 4天，零风险（不修改现有代码）

---

## 七、验收标准

| 功能 | 测试方法 | 预期结果 |
|------|---------|---------|
| validate() 不受影响 | 现有测试 | 100% 通过 |
| llm_validate() 云端调用 | API Mock | 返回验证结果 |
| code_review() 本地调用 | Ollama测试 | qwen3.5-9b 返回审查 |
| Orchestrator 默认行为 | 集成测试 | 与现有行为一致 |

---

**文档状态**: 设计方案，待用户确认
**下一步**: 确认后开始实现

[[qa-agent-code-review-integration]]