---
name: rag-requirement-gap-analysis
description: 当前 RAG Pipeline 与用户需求的差异分析
metadata:
  type: feedback
---

# RAG Pipeline 需求差异分析

## 用户需求流程

```
自然语言输入 → RAG包装(论文知识) → LLM生成 → RAG审核对比 → 修缮 → 给用户
                                              ↓
                                    确保没有幻觉 (审计日志全程记录)
```

---

## 一、需求 vs 实现对比表

| # | 需求步骤 | 当前状态 | 差异 | 优先级 |
|---|---------|---------|------|--------|
| 1 | **自然语言输入** | ✓ 已实现 | 无差异 | - |
| 2 | **RAG包装(检索论文)** | ✓ 已实现 | 无差异 | - |
| 3 | **LLM生成解释** | ✗ **未实现** | **缺失关键步骤** | **P0** |
| 4 | **RAG审核对比** | ⚠️ 部分 | 只有规则验证，无对比 | P1 |
| 5 | **修缮后给用户** | ✗ 未实现 | 无修缮闭环 | P1 |
| 6 | **确保没有幻觉** | ⚠️ 部分 | 有检测，但未与LLM生成联动 | P1 |
| 7 | **审计日志全程记录** | ✓ 已实现 | 16表审计系统 | - |

---

## 二、详细差异分析

### 差异 #1: LLM生成解释 (P0 关键缺失)

**需求**: 检索到的论文知识 → LLM生成通俗易懂的解释

**当前**: 截取前200字，不调用LLM

```python
# specialized_agents.py:389
def _generate_napkin_summary(self, query, context):
    """当前：截取前200字"""
    first_para = context.split("\n\n")[0]
    return first_para[:200] + "..."  # ✗ 不调用LLM
```

**应该**: 

```python
# 应有的实现
def _generate_llm_summary(self, query, context):
    """调用LLM生成解释"""
    prompt = f"论文内容: {context}\n用户问题: {query}\n请用通俗语言解释..."
    result = llm_client.chat(prompt)
    audit.log_llm_call(...)  # 审计记录
    return result
```

---

### 差异 #2: RAG审核对比 (P1 部分缺失)

**需求**: LLM生成结果 → 与检索知识对比 → 识别偏差

**当前**: 只有规则验证（实体支撑度），无对比机制

```python
# specialized_agents.py:479 - 只有规则验证
def validate(self, output, chunks):
    """当前：规则验证"""
    hallucination_result = self._detect_hallucination(output, contexts)
    citation_result = self._validate_citations(output, chunks)
    # ✗ 无对比LLM生成与检索知识的差异
```

**应该**: 

```python
# 应有的对比审核
def compare_with_source(self, llm_output, retrieved_chunks):
    """对比LLM输出与论文原文"""
    # 检查LLM是否添加了论文中没有的信息
    for entity in extract_entities(llm_output):
        if not entity_in_chunks(entity, retrieved_chunks):
            flag_as_potential_hallucination(entity)
    
    # 检查是否遗漏关键信息
    for key_point in extract_key_points(retrieved_chunks):
        if key_point not in llm_output:
            suggest_addition(key_point)
```

---

### 差异 #3: 修缮闭环 (P1 未实现)

**需求**: 审核发现问题 → 自动修缮 → 再次审核 → 给用户

**当前**: 只检测问题，不修缮

```python
# 当前流程
detect_hallucination() → "风险告警" → 直接输出给用户
                         ↑
                         没有修缮步骤
```

**应该**: 

```python
# 应有的修缮闭环
def repair_loop(self, output, chunks, max_retries=3):
    """修缮闭环"""
    for attempt in range(max_retries):
        # 1. 审核
        issues = self.review(output, chunks)
        
        if issues.is_passed:
            return output  # 通过
        
        # 2. 修缮（LLM修复）
        repair_prompt = f"原输出有误: {issues}\n请根据论文原文修正: {chunks}"
        output = llm_client.chat(repair_prompt)
        
        # 3. 再次审核
        audit.log_repair_attempt(attempt, issues, output)
    
    # 熔断：超过最大重试
    return {"warning": "无法完全修正", "output": output}
```

---

### 差异 #4: 幻觉检测未联动 (P1 部分缺失)

**需求**: 幻觉检测 → 与LLM生成联动 → 验证每个生成内容

**当前**: 幻觉检测独立存在，但Pipeline未调用LLM

```python
# hallucination_records表: 0条记录
# 因为没有LLM生成，所以没有幻觉检测数据
```

**应该**: LLM生成后立即幻觉检测

---

## 三、审计日志覆盖评估

| 审计方法 | 覆盖步骤 | 记录数 | 状态 |
|---------|---------|--------|------|
| `log_input()` | 步骤1 | ✓ 有 | 正常 |
| `log_retrieval()` | 步骤2 | ✓ 有 | 正常 |
| `log_prompt()` | 步骤2包装 | ✓ 有 | 正常 |
| `log_llm_call()` | 步骤3 | **0条** | **未调用** |
| `log_hallucination()` | 步骤4 | **0条** | **未联动** |
| `log_output()` | 步骤5 | ✓ 有 | 正常 |
| `log_error()` | 异常 | ✓ 有 | 正常 |

---

## 四、完整需求流程设计

```
┌─────────────────────────────────────────────────────────────┐
│                   完整 Agentic RAG 流程                       │
└─────────────────────────────────────────────────────────────┘

用户输入 "Transformer原理"
         │
         ▼
┌─────────────────────────────────────────────┐
│  Step 1: 自然语言输入                        │
│  audit.log_input()                          │
│  ✓ 已实现                                    │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Step 2: RAG包装（检索论文）                  │
│  HybridSearcher → Vector + BM25 + RRF       │
│  audit.log_retrieval()                      │
│  ✓ 已实现                                    │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Step 3: LLM生成解释                         │
│  glm-5 → 通俗解读论文                        │
│  audit.log_llm_call()                       │
│  ✗ **缺失 - 关键步骤**                       │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Step 4: RAG审核对比                         │
│  检查LLM输出与论文原文差异                    │
│  audit.log_hallucination()                  │
│  ⚠️ 部分 - 只有规则，无对比                   │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Step 5: 修缮闭环                            │
│  发现问题 → LLM修缮 → 再次审核                │
│  audit.log_repair()                         │
│  ✗ 未实现                                    │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Step 6: 给用户                              │
│  格式化输出 + Citation标记                   │
│  audit.log_output()                         │
│  ✓ 已实现                                    │
└─────────────────────────────────────────────┘
```

---

## 五、差异汇总

| 类别 | 已实现 | 未实现 | 完成度 |
|------|--------|--------|--------|
| 输入/检索 | ✓ 2步 | - | 100% |
| **LLM生成** | - | **✗ 1步** | **0%** |
| 审核/修缮 | ⚠️ 部分 | ✗ 对比+修缮 | 30% |
| 审计日志 | ✓ 16表 | - | 100% |
| **总计** | **4/7** | **3/7** | **57%** |

---

## 六、修复优先级

| P级 | 修复内容 | 预估工期 | 依赖 |
|-----|---------|---------|------|
| **P0** | LLM生成解释 | 2小时 | 无 |
| **P1** | RAG审核对比 | 4小时 | P0 |
| **P1** | 修缮闭环 | 6小时 | P1 |

---

## 七、修复后的完整 Pipeline

```python
class CompleteRAGPipeline:
    
    async def run(self, query: str):
        """完整需求流程"""
        
        # Step 1: 输入记录
        self.audit.log_input(query)
        
        # Step 2: RAG包装
        chunks = self.retrieval.search(query)
        self.audit.log_retrieval(query, chunks)
        
        # Step 3: LLM生成 ← 新增
        context = self.restructure(chunks)
        llm_output = self.llm_client.chat(
            f"论文: {context}\n问题: {query}\n请解释..."
        )
        self.audit.log_llm_call(llm_output)
        
        # Step 4: RAG审核 ← 增强
        issues = self.review.compare(llm_output, chunks)
        self.audit.log_hallucination(issues)
        
        # Step 5: 修缮闭环 ← 新增
        if not issues.is_passed:
            llm_output = self.repair(llm_output, chunks, issues)
            # 再次审核
            issues = self.review.compare(llm_output, chunks)
        
        # Step 6: 给用户
        final = self.format(llm_output, chunks)
        self.audit.log_output(final)
        
        return final
```

---

**文档状态**: 需求差异分析
**关键缺失**: LLM生成解释 (P0)
**审计系统**: 完整，但未联动LLM

[[rag-llm-integration-gap]]