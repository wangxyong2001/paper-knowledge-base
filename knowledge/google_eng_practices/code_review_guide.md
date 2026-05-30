---
name: google-code-review-practices
description: Google Engineering Practices - Code Review 最佳实践知识库，供 QA Agent (Code Reviewer) 使用
metadata:
  type: reference
---

# Google Code Review 最佳实践知识库

> 来源: https://github.com/google/eng-practices
> 版本: v1.0
> 日期: 2026-05-25
> 用途: QA Agent 作为 Code Reviewer 的技能配置

---

## 一、核心原则

### 1.1 Code Review 的首要目标

> **"改进整体代码健康度"** (Improve overall code health)

**核心规则**：
> 当 CL（Change List）确实改进了系统的整体代码健康度时，即使不完美，Reviewer 也应该批准。

**关键要点**：
- 没有"完美"代码，只有"更好"代码
- 追求**持续改进**，而非完美
- 不应因"不完美"而推迟数天或数周

### 1.2 决策原则

| 原则 | 说明 |
|------|------|
| **技术事实优先** | 技术事实和数据 > 个人意见和偏好 |
| **风格指南权威** | 风格指南是绝对权威 |
| **设计非风格** | 软件设计基于原则，非个人偏好 |
| **一致性原则** | 无其他规则时，与现有代码保持一致 |

---

## 二、检查项清单 (What to Look For)

### 2.1 Design（设计） ⭐ 最重要

| 检查点 | 说明 |
|-------|------|
| 整体设计 | 各部分代码交互是否合理 |
| 归属位置 | 是否应在代码库或库中 |
| 系统集成 | 与系统其他部分集成是否良好 |
| 时间合适 | 是否是添加此功能的合适时机 |

### 2.2 Functionality（功能）

| 检查点 | 说明 |
|-------|------|
| 预期行为 | CL 是否做了开发者预期的 |
| 用户价值 | 开发者预期对用户是否有益 |
| 边界情况 | 是否处理了边界情况 |
| 并发问题 | 死锁、竞态条件风险 |
| UI变更 | 用户界面变更需要实际验证 |

### 2.3 Complexity（复杂度）

| 检查点 | 说明 |
|-------|------|
| 行级复杂度 | 单行是否太复杂 |
| 函数复杂度 | 函数是否太复杂 |
| 类级复杂度 | 类是否太复杂 |
| 过度工程 | 是否过于通用或添加不需要的功能 |

**"太复杂"定义**：
- 代码读者无法快速理解
- 开发者调用/修改时容易引入 bug

**过度工程警告**：
> 解决**现在**需要解决的问题，而非**可能**未来需要解决的问题

### 2.4 Tests（测试）

| 检查点 | 说明 |
|-------|------|
| 测试覆盖 | 单元测试、集成测试是否添加 |
| 测试正确 | 测试是否正确、合理、有用 |
| 测试失败 | 代码破坏时测试是否会失败 |
| 断言有用 | 断言是否简单有用 |
| 测试复杂度 | 测试代码也需要维护，不接受不必要的复杂性 |

### 2.5 Naming（命名）

| 检查点 | 说明 |
|-------|------|
| 名称长度 | 足够传达含义，但不过长 |
| 名称清晰 | 是否说明是什么或做什么 |

### 2.6 Comments（注释）

| 检查点 | 说明 |
|-------|------|
| 注释必要性 | 所有注释是否实际必要 |
| 解释 WHY | 注释应解释**为什么**存在 |
| 不解释 WHAT | 代码应足够清晰解释自己 |
| TODO清理 | 检查是否有 TODO 可以移除 |

### 2.7 Style（风格）

| 检查点 | 说明 |
|-------|------|
| 风格指南 | 遵循语言风格指南 |
| Nit 标记 | 风格建议用 "Nit:" 标记非强制 |
| 风格分离 | 不将风格变更与其他变更混合 |

### 2.8 Consistency（一致性）

| 检查点 | 说明 |
|-------|------|
| 风格指南优先 | 风格指南要求必须遵循 |
| 与周围一致 | 风格指南未规定时与周围代码一致 |
| 清理遗留 | 鼓励提交 bug 并添加 TODO 清理不一致代码 |

### 2.9 Documentation（文档）

| 检查点 | 说明 |
|-------|------|
| 构建文档 | 构建、测试、交互、发布文档是否更新 |
| 删除文档 | 删除/废弃代码时文档是否同步删除 |

---

## 三、如何写评论 (How to Write Comments)

### 3.1 核心原则

```
Be kind（友善） + Explain why（解释原因） + Balance guidance（平衡指导）
```

### 3.2 评论格式模板

| 类型 | 标签 | 示例 |
|------|------|------|
| **必须修改** | 无标签 | "此处的并发模型增加了复杂性..." |
| **Nit（小问题）** | `Nit:` | "Nit: 命名可以更清晰" |
| **Optional（可选）** | `Optional:` 或 `Consider:` | "Consider: 可以重构为..." |
| **FYI（信息）** | `FYI:` | "FYI: 未来可以考虑..." |

### 3.3 评论原则

| 原则 | 说明 |
|------|------|
| 对代码不对人 | 评论代码，不评论开发者 |
| 解释原因 | 说明为什么，而非只说问题 |
| 重写优于解释 | 开发者应重写代码使其更清晰，而非只在 review 中解释 |
| 正向反馈 | 也评论做得好的地方 |

### 3.4 好评论 vs 坏评论示例

**坏评论**：
> "为什么**你**在这里使用线程？显然没有任何并发收益？"

**好评论**：
> "此处的并发模型增加了系统复杂性，但我看不到任何实际性能收益。由于没有性能收益，最好让此代码单线程，而非使用多线程。"

---

## 四、评论严重性标注 (Label Comment Severity)

### 4.1 标签定义

| 标签 | 含义 | 开发者应处理 |
|------|------|-------------|
| `Nit:` | 小问题，技术上应该做但影响不大 | 可选处理 |
| `Optional:` 或 `Consider:` | 好主意，但不强制 | 可选处理 |
| `FYI:` | 此 CL 不期望处理，但值得了解 | 无需处理 |
| 无标签 | 必须修改 | 必须处理 |

### 4.2 标注好处

- 明确评论意图
- 帮助开发者优先级排序
- 避免误解（所有评论被当作强制）

---

## 五、QA Agent Code Review 报告模板

基于 Google Practices，QA Agent 生成的报告格式：

```markdown
## Code Review Report

### 概览
- **评审者**: QA Agent (qwen3.5-9b-reviewer)
- **评审时间**: 2026-05-25T10:30
- **CL**: {file_path}
- **整体评分**: {score}/10

### 检查项结果

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Design | ✅/⚠️/❌ | 整体设计合理性 |
| Functionality | ✅/⚠️/❌ | 功能实现正确性 |
| Complexity | ✅/⚠️/❌ | 是否过度复杂 |
| Tests | ✅/⚠️/❌ | 测试覆盖情况 |
| Naming | ✅/⚠️/❌ | 命名清晰度 |
| Comments | ✅/⚠️/❌ | 注释必要性 |
| Style | ✅/⚠️/❌ | 风格一致性 |
| Documentation | ✅/⚠️/❌ | 文档更新 |

### 评论列表

#### 必须修改
- [位置: line XX] {评论内容}
  - **原因**: {为什么需要修改}
  - **建议**: {修复建议}

#### Nit: 小问题
- [Nit] [位置: line XX] {评论内容}

#### Optional: 可选改进
- [Optional] {改进建议}

#### FYI: 信息
- [FYI] {值得了解的信息}

### 决策
- **是否批准**: Yes/No (附条件批准)
- **条件**: {必须修改项处理完成后批准}
```

---

## 六、QA Agent 技能配置

### 6.1 Code Review Prompt 模板

```python
CODE_REVIEW_PROMPT = """
你是 Code Reviewer，遵循 Google Engineering Practices 最佳实践。

核心原则：
1. 改进整体代码健康度是首要目标
2. 追求持续改进，而非完美
3. 技术事实优先于个人意见
4. 评论代码，不评论开发者

检查项（按优先级）：
- Design: 整体设计是否合理
- Functionality: 功能是否正确，是否有并发问题
- Complexity: 是否过度复杂或过度工程
- Tests: 测试是否正确、有用
- Naming: 命名是否清晰
- Comments: 注释是否必要（解释 WHY）
- Style: 风格是否一致
- Documentation: 文档是否更新

评论格式：
- 必须修改: 无标签，说明原因和建议
- Nit: "Nit:" 标记小问题
- Optional: "Consider:" 或 "Optional:" 标记建议
- FYI: "FYI:" 标记信息

评审论文代码：
论文上下文：{paper_context}
生成代码：{code_content}

输出 JSON 格式：
{
    "score": 0-10,
    "checks": {...},
    "comments": [...],
    "decision": "approve"/"reject"/"conditional",
    "conditions": [...]
}
"""
```

### 6.2 QA Agent 调用配置

```python
class QualityAssuranceAgent:
    
    CODE_REVIEW_PROMPT = CODE_REVIEW_PROMPT
    
    async def code_review_with_google_practices(
        self,
        code: str,
        paper_context: str,
        enable_local: bool = True
    ) -> Dict:
        """使用 Google Engineering Practices 进行代码审查"""
        
        prompt = self.CODE_REVIEW_PROMPT.format(
            paper_context=paper_context,
            code_content=code
        )
        
        if enable_local:
            # 本地 qwen3.5-9b-reviewer
            result = await self._call_local_llm(prompt)
        else:
            # 云端 glm-5
            result = await self.cloud_client.chat(
                messages=[{"role": "user", "content": prompt}]
            )
        
        return self._parse_review_result(result)
```

---

## 七、参考文献

| 文档 | 链接 | 内容 |
|------|------|------|
| Reviewer Guide | review/reviewer/index.md | 完整 reviewer 指南 |
| Standard | review/reviewer/standard.md | Code Review 标准 |
| What to Look For | review/reviewer/looking-for.md | 检查项清单 |
| Comments | review/reviewer/comments.md | 如何写评论 |
| Speed | review/reviewer/speed.md | 提速建议 |
| Pushback | review/reviewer/pushback.md | 处理反馈 |
| Developer Guide | review/developer/index.md | CL 作者指南 |

---

**知识库状态**: v1.0
**更新频率**: 定期同步 Google 原仓库更新
**维护责任**: QA Agent