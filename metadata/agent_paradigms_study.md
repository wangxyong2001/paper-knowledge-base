# Agent三范式学习报告

## 1. 范式对比总表

### 1.1 核心维度对比

| 维度 | ReAct | Plan-and-Solve | Reflection |
|------|-------|----------------|------------|
| **循环类型** | Thought-Action-Observation | Plan-Execute | Action-Reflect-Improve |
| **决策时机** | 每步动态决策 | 开始时一次性规划 | 每轮迭代后决策 |
| **改进方式** | 观察反馈调整行动 | 按计划顺序执行 | 自我评审优化结果 |
| **适用任务** | 搜索/API调用/不确定路径 | 数学推理/步骤明确任务 | 代码生成/方案优化/质量提升 |
| **可控性** | 低 (路径不确定) | 高 (步骤固定) | 中 (迭代次数可控) |
| **效率** | 可能多轮探索 | 固定步数 | 固定迭代次数 |
| **Token消耗** | 高 (多次调用) | 低 (单次规划) | 中 (迭代消耗) |
| **失败恢复** | 自然 (重试) | 难 (需重新规划) | 自然 (迭代改进) |

### 1.2 核心流程对比

```
ReAct 循环:
  Thought: 我应该做什么?
    -> Action: 执行工具
    -> Observation: 观察结果
    -> Thought: 下一步怎么做? (循环)

Plan-and-Solve 流程:
  Plan: [步骤1, 步骤2, 步骤3, ...]
    -> Execute(步骤1)
    -> Execute(步骤2)
    -> Execute(步骤3)
    -> 完成

Reflection 迭代:
  Action: 生成初始结果
    -> Reflect: 评审结果质量
    -> Improve: 根据反馈优化
    -> 循环直到满意或达到上限
```

---

## 2. 现有四角色Agent范式匹配评估

### 2.1 PaperRetrievalAgent - 检索专家

**当前实现分析:**
```python
# 当前: 固定流程，无动态决策
def retrieve(self, query, top_k):
    vector_result = self.registry.execute("vector_search", {...})
    bm25_result = self.registry.execute("bm25_search", {...})
    hybrid_result = self.registry.execute("hybrid_search", {...})
    metrics = self._calculate_metrics(query, results)
    return {...}
```

**范式匹配评估:**

| 特征 | ReAct适合度 | Plan-and-Solve适合度 | Reflection适合度 |
|------|------------|---------------------|------------------|
| 需要外部工具 | **高** (搜索工具) | 中 | 低 |
| 路径不确定性 | **高** (需动态调整) | 低 | 中 |
| 步骤明确性 | 中 (可变顺序) | **高** | 低 |
| 迭代改进需求 | 中 | 低 | **高** (优化召回) |

**结论: 推荐采用 ReAct + Reflection 组合**

- **ReAct**: 检索路径不确定，需要观察结果后调整策略
- **Reflection**: 召回质量不满意时自动重试/优化查询

**改造建议:**
```python
# ReAct 改造
def retrieve_with_react(self, query):
    while not satisfied:
        thought = self._think(query, current_results)
        action = self._decide_action(thought)
        observation = self._execute_action(action)
        if self._should_retry(observation):
            query = self._refine_query(observation)

# Reflection 增强
def retrieve_with_reflection(self, query, max_iterations=3):
    for i in range(max_iterations):
        results = self._search(query)
        reflection = self._evaluate_quality(results)
        if reflection["is_satisfied"]:
            break
        query = self._refine_based_on_reflection(reflection)
```

---

### 2.2 PaperAnalysisAgent - 解读专家

**当前实现分析:**
```python
# 当前: 固定步骤，无规划阶段
def analyze(self, query, chunks):
    context = self._assemble_context(chunks)
    formulas = self._extract_formulas(context)
    concepts = self._extract_concepts(context)
    summary = self._generate_napkin_summary(query, context)
    code_design = self._extract_code_design(context)
    return {...}
```

**范式匹配评估:**

| 特征 | ReAct适合度 | Plan-and-Solve适合度 | Reflection适合度 |
|------|------------|---------------------|------------------|
| 需要外部工具 | 低 | 低 | 低 |
| 路径不确定性 | 低 | **高** (步骤明确) | 中 |
| 步骤明确性 | **高** (分析有固定模式) | **高** | 中 |
| 迭代改进需求 | 中 | 低 | 中 |

**结论: 推荐采用 Plan-and-Solve + 轻量Reflection**

- **Plan-and-Solve**: 分析步骤明确，可提前规划
- **Reflection**: 结果不满意时可调整分析策略

**改造建议:**
```python
# Plan-and-Solve 改造
def analyze_with_planning(self, query, chunks):
    # Phase 1: Plan
    plan = self._create_analysis_plan(query, chunks)
    # plan = {
    #     "steps": [
    #         {"action": "extract_context", "priority": 1},
    #         {"action": "identify_paper_type", "priority": 1},
    #         {"action": "extract_formulas", "priority": 2},
    #         {"action": "extract_concepts", "priority": 2},
    #         {"action": "generate_summary", "priority": 3},
    #         {"action": "extract_code_design", "priority": 3}
    #     ]
    # }

    # Phase 2: Execute
    results = {}
    for step in sorted(plan["steps"], key=lambda x: x["priority"]):
        results.update(self._execute_step(step))

    return results

# 轻量Reflection
def analyze_with_reflection(self, query, chunks):
    analysis = self._analyze(query, chunks)
    reflection = self._reflect_on_analysis(analysis)
    if reflection["needs_improvement"]:
        analysis = self._improve_analysis(analysis, reflection)
    return analysis
```

---

### 2.3 QualityAssuranceAgent - 质量专家

**当前实现分析:**
```python
# 当前: 一次性验证，无迭代改进
def validate(self, output, chunks):
    hallucination_result = self._detect_hallucination(output, contexts)
    citation_result = self._validate_citations(output, chunks)
    quality_score = self._calculate_quality_score(...)
    risks = self._generate_risks(...)
    suggestions = self._generate_suggestions(...)
    return {...}
```

**范式匹配评估:**

| 特征 | ReAct适合度 | Plan-and-Solve适合度 | Reflection适合度 |
|------|------------|---------------------|------------------|
| 需要外部工具 | 中 | 低 | 低 |
| 路径不确定性 | 低 | 低 | **高** |
| 步骤明确性 | 中 | **高** | **高** |
| 迭代改进需求 | 中 | 低 | **高** (核心特征) |

**结论: 强烈推荐采用 Reflection**

- **Reflection**: 质量验证是典型的迭代改进场景，检测到问题应自动修正

**改造建议:**
```python
# Reflection 改造
def validate_with_reflection(self, output, chunks, max_iterations=3):
    current_output = output
    history = []

    for i in range(max_iterations):
        # Validate
        validation = self._validate(current_output, chunks)
        history.append({
            "iteration": i,
            "quality_score": validation["quality_score"],
            "risks": validation["risks"]
        })

        # Check if passed
        if validation["is_passed"]:
            return {
                "final_output": current_output,
                "iterations": i + 1,
                "history": history,
                "status": "passed"
            }

        # Reflect and improve
        reflection = self._reflect_on_quality(validation)
        current_output = self._apply_suggestions(current_output, reflection["improvements"])

    return {
        "final_output": current_output,
        "iterations": max_iterations,
        "history": history,
        "status": "max_iterations_reached"
    }
```

---

### 2.4 CodeReproductionAgent - 复现专家

**当前实现分析:**
```python
# 当前: 一次性生成，测试失败无修正
def reproduce(self, query, analysis):
    code_modules = self._generate_code_modules(query, analysis)
    test_cases = self._generate_test_cases(code_modules)
    run_results = self._run_code_modules(code_modules)
    return {...}
```

**范式匹配评估:**

| 特征 | ReAct适合度 | Plan-and-Solve适合度 | Reflection适合度 |
|------|------------|---------------------|------------------|
| 需要外部工具 | **高** (代码执行) | 中 | **高** |
| 路径不确定性 | 中 | 中 | **高** |
| 步骤明确性 | 中 | **高** | **高** |
| 迭代改进需求 | 中 | 低 | **高** (核心特征) |

**结论: 推荐采用 Plan-and-Solve + Reflection 组合**

- **Plan-and-Solve**: 代码生成有明确步骤（设计→实现→测试）
- **Reflection**: 测试失败时自动调试修正

**改造建议:**
```python
# Plan-and-Solve + Reflection 组合
def reproduce_with_planning_and_reflection(self, query, analysis, max_iterations=5):
    # Phase 1: Plan
    plan = self._create_code_plan(query, analysis)
    # plan = {
    #     "design": "先设计架构",
    #     "implement": "生成代码模块",
    #     "test": "运行测试",
    #     "debug": "根据测试结果修正"
    # }

    # Phase 2: Execute with Reflection
    code_modules = self._generate_code_modules(query, analysis)

    for i in range(max_iterations):
        # Run tests
        test_results = self._run_tests(code_modules)

        if all(t["passed"] for t in test_results):
            return {"success": True, "code": code_modules, "iterations": i}

        # Reflect on failures
        reflection = self._analyze_test_failures(test_results)

        # Fix code
        code_modules = self._fix_code(code_modules, reflection)

    return {"success": False, "code": code_modules, "iterations": max_iterations}
```

---

## 3. 组合使用方案

### 3.1 推荐: Plan → ReAct → Reflection 流水线

```
用户查询
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ Phase 1: Planning (Plan-and-Solve)                  │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 任务分析 → 步骤规划 → 资源分配                   │ │
│ │ 输出: execution_plan                            │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ Phase 2: Execution (ReAct)                          │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ for step in plan.steps:                         │ │
│ │   Thought → Action → Observation                │ │
│ │   if not_satisfied: adjust_strategy             │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ Phase 3: Quality Assurance (Reflection)              │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ result = execute()                              │ │
│ │ while not_satisfied and iterations < max:       │ │
│ │   reflection = evaluate(result)                 │ │
│ │   result = improve(result, reflection)          │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
    │
    ▼
最终输出
```

### 3.2 四角色Agent范式分配

| Agent | 主范式 | 辅助范式 | 理由 |
|-------|--------|---------|------|
| PaperRetrievalAgent | **ReAct** | Reflection | 检索路径不确定，需观察调整 |
| PaperAnalysisAgent | **Plan-and-Solve** | Reflection | 分析步骤明确，可提前规划 |
| QualityAssuranceAgent | **Reflection** | - | 质量验证需迭代改进 |
| CodeReproductionAgent | **Plan-and-Solve** | **Reflection** | 代码生成步骤明确，测试失败需修正 |

---

## 4. 改造实施计划

### 4.1 Phase 1: PaperRetrievalAgent ReAct改造 (预计2天)

**目标:** 引入动态检索策略调整

**改造点:**
1. 添加 `_think()` 方法：分析当前检索状态
2. 添加 `_decide_action()` 方法：选择下一步行动
3. 添加 `_observe()` 方法：观察检索结果
4. 添加 `_should_retry()` 方法：判断是否需要重试
5. 添加 `_refine_query()` 方法：优化查询词

**代码框架:**
```python
class PaperRetrievalAgent:
    def retrieve_with_react(self, query, max_iterations=5):
        results = []
        current_query = query

        for i in range(max_iterations):
            # Thought
            thought = self._think(current_query, results)

            # Action
            action = self._decide_action(thought)
            new_results = self._execute_action(action, current_query)

            # Observation
            observation = self._observe(new_results, results)

            # Update
            results = self._merge_results(results, new_results)

            # Check termination
            if self._is_satisfied(observation):
                break

            # Refine query
            current_query = self._refine_query(current_query, observation)

        return self._finalize_results(results)
```

### 4.2 Phase 2: PaperAnalysisAgent Plan-and-Solve改造 (预计1天)

**目标:** 引入显式规划阶段

**改造点:**
1. 添加 `_create_analysis_plan()` 方法：根据论文类型规划分析步骤
2. 添加 `_execute_step()` 方法：执行单个分析步骤
3. 添加 `_reflect_on_analysis()` 方法：评估分析质量

**代码框架:**
```python
class PaperAnalysisAgent:
    def analyze_with_planning(self, query, chunks):
        # Plan
        paper_type = self._identify_paper_type(chunks)
        plan = self._create_analysis_plan(paper_type)

        # Execute
        results = {}
        for step in plan["steps"]:
            results.update(self._execute_step(step, chunks))

        # Reflect
        reflection = self._reflect_on_analysis(results)
        if reflection["needs_improvement"]:
            results = self._improve_analysis(results, reflection)

        return results
```

### 4.3 Phase 3: QualityAssuranceAgent Reflection改造 (预计2天)

**目标:** 引入迭代修正循环

**改造点:**
1. 添加 `_reflect_on_quality()` 方法：评估输出质量
2. 添加 `_apply_suggestions()` 方法：应用修正建议
3. 添加迭代验证循环

**代码框架:**
```python
class QualityAssuranceAgent:
    def validate_with_reflection(self, output, chunks, max_iterations=3):
        current_output = output

        for i in range(max_iterations):
            # Validate
            validation = self._validate(current_output, chunks)

            if validation["is_passed"]:
                return {"success": True, "output": current_output}

            # Reflect
            reflection = self._reflect_on_quality(validation)

            # Improve
            current_output = self._apply_suggestions(current_output, reflection)

        return {"success": False, "output": current_output}
```

### 4.4 Phase 4: CodeReproductionAgent Reflection改造 (预计2天)

**目标:** 引入测试驱动的代码修正

**改造点:**
1. 添加 `_create_code_plan()` 方法：规划代码生成步骤
2. 添加 `_analyze_test_failures()` 方法：分析测试失败原因
3. 添加 `_fix_code()` 方法：根据错误修正代码
4. 添加迭代测试循环

**代码框架:**
```python
class CodeReproductionAgent:
    def reproduce_with_reflection(self, query, analysis, max_iterations=5):
        # Plan
        plan = self._create_code_plan(analysis)

        # Generate initial code
        code_modules = self._generate_code_modules(query, analysis)

        # Test-Driven Reflection
        for i in range(max_iterations):
            test_results = self._run_tests(code_modules)

            if all(t["passed"] for t in test_results):
                return {"success": True, "code": code_modules}

            # Analyze failures
            failures = self._analyze_test_failures(test_results)

            # Fix code
            code_modules = self._fix_code(code_modules, failures)

        return {"success": False, "code": code_modules}
```

### 4.5 Phase 5: Orchestrator 流水线整合 (预计1天)

**目标:** 整合四种范式到协调器

**改造点:**
```python
class SpecializedAgentOrchestrator:
    def run_pipeline_v2(self, query, need_code=False):
        # Phase 1: Planning
        plan = self._create_execution_plan(query)

        # Phase 2: Execution with ReAct (Retrieval)
        retrieval_result = self.retrieval_agent.retrieve_with_react(query)

        # Phase 3: Execution with Planning (Analysis)
        analysis_result = self.analysis_agent.analyze_with_planning(
            query, retrieval_result["results"]
        )

        # Phase 4: Quality Assurance with Reflection
        qa_result = self.qa_agent.validate_with_reflection(
            analysis_result["summary"], retrieval_result["results"]
        )

        # Phase 5: Code with Planning + Reflection
        if need_code:
            code_result = self.code_agent.reproduce_with_reflection(
                query, analysis_result
            )

        return self._assemble_final_result(...)
```

---

## 5. 风险与应对

### 5.1 Token消耗风险

| 改造 | 增加Token | 应对策略 |
|------|----------|---------|
| ReAct | +30-50% | 设置max_iterations限制 |
| Reflection | +20-40% | 设置质量阈值提前退出 |
| 组合使用 | +50-80% | 分阶段启用，按需开关 |

### 5.2 性能风险

| 风险 | 影响 | 应对策略 |
|------|------|---------|
| 迭代不收敛 | 无限循环 | max_iterations硬限制 |
| 效果提升不明显 | 浪费资源 | A/B测试验证效果 |
| 实现复杂度 | 维护成本 | 渐进式改造，保留原实现 |

### 5.3 兼容性风险

| 风险 | 应对策略 |
|------|---------|
| 破坏现有接口 | 新增 `*_v2()` 方法，保留原方法 |
| 工具调用失败 | 添加fallback到原流程 |
| 依赖LLM质量 | 添加规则引擎兜底 |

---

## 6. 效果评估指标

### 6.1 定量指标

| Agent | 指标 | 基线 | 目标 |
|-------|------|------|------|
| Retrieval | Recall@10 | 0.65 | 0.75 |
| Analysis | 完整性得分 | 0.70 | 0.85 |
| QA | 通过率 | 0.75 | 0.90 |
| Code | 可运行率 | 0.60 | 0.80 |

### 6.2 定性指标

- 用户满意度评分 (1-5)
- 人工修正次数
- 错误恢复成功率

---

## 7. 总结

### 7.1 范式匹配结论

| Agent | 当前状态 | 推荐范式 | 改造优先级 |
|-------|---------|---------|-----------|
| PaperRetrievalAgent | 静态流程 | ReAct + Reflection | **高** |
| PaperAnalysisAgent | 固定步骤 | Plan-and-Solve + Reflection | 中 |
| QualityAssuranceAgent | 一次性验证 | **Reflection** | **高** |
| CodeReproductionAgent | 一次性生成 | Plan-and-Solve + **Reflection** | **高** |

### 7.2 实施路线

```
Week 1: Phase 1 + Phase 3 (Retrieval + QA)
    ├── PaperRetrievalAgent ReAct改造
    └── QualityAssuranceAgent Reflection改造

Week 2: Phase 4 + Phase 5 (Code + Orchestrator)
    ├── CodeReproductionAgent Reflection改造
    └── Orchestrator 流水线整合

Week 3: Phase 2 + 测试验证
    ├── PaperAnalysisAgent Planning改造
    └── A/B测试验证效果
```

### 7.3 核心收益

1. **智能检索**: ReAct使检索路径动态适应查询特点
2. **质量保障**: Reflection实现自动修正，提升输出质量
3. **代码复现**: 测试驱动的迭代修正，提高可运行率
4. **可观测性**: 每个阶段有明确的中间状态，便于调试

---

**学习成果**: 理解了三种范式的核心差异和适用场景，评估了现有四角色Agent的范式匹配度，制定了详细的改造计划。下一步按优先级实施改造，并通过A/B测试验证效果。