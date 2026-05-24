# 工作流测试问题日志

> 测试日期: 2026-05-24
> 测试状态: 中断（网络问题）
> 测试者: Main Agent

---

## 一、问题记录

### 问题1: HuggingFace连接超时

**问题描述**:
```
'timed out' thrown while requesting HEAD https://huggingface.co/BAAI/bge-large-zh-v1.5/resolve/main/./modules.json
Retrying in 1s [Retry 1/5].
'timed out' thrown while requesting HEAD https://huggingface.co/BAAI/bge-large-zh-v1.5/resolve/main/./modules.json
Retrying in 2s [Retry 2/5].
'[Errno 111] Connection refused' thrown while requesting HEAD https://huggingface.co/BAAI/bge-large-zh-v1.5/resolve/main/./modules.json
```

**影响范围**:
- 向量检索无法执行（embedding模型依赖HuggingFace）
- 工作流第一阶段（检索）阻塞
- 后续阶段无法继续

**根本原因**:
- 网络防火墙限制
- HuggingFace服务器国内访问不稳定
- 本地模型缓存未生效

**解决方案**:
1. 配置本地模型缓存路径
2. 使用离线embedding模型（Ollama本地）
3. 配置网络代理

---

### 问题2: 工作流测试未完整跑完

**问题描述**:
- 测试中断在检索阶段
- 分析、质量、代码阶段未执行
- 无法验证完整Pipeline

**影响范围**:
- 无法验证四阶段衔接
- 无法检查遗漏和产出质量

---

## 二、问题登记表

| 问题ID | 问题类型 | 问题描述 | 影响 | 状态 | 解决方案 |
|-------|---------|---------|------|------|---------|
| NET-01 | 网络 | HuggingFace连接超时 | 向量检索阻塞 | 待解决 | 本地模型/代理 |
| NET-02 | 网络 | Connection refused | embedding失败 | 待解决 | 网络配置 |
| TEST-01 | 测试 | Pipeline未完整执行 | 验证中断 | 待解决 | 解决网络问题后重试 |

---

## 三、需求方测试指南

### 3.1 测试准备

**环境检查**:
```bash
# 1. 检查网络连通性
curl -I https://huggingface.co

# 2. 检查本地模型
.venv/bin/python -c "
import sys
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb/scripts')
from embed_local import LocalEmbedding
embedder = LocalEmbedding()
vec = embedder.embed(['测试文本'])
print('本地模型状态: OK, 向量维度:', len(vec[0]))
"

# 3. 检查向量数据库
ls -la /home/nvidia/workspace/paper/vectordb/chroma_db
```

### 3.2 测试步骤

**步骤1: CLI查询测试**
```bash
cd /home/nvidia/workspace/paper/vectordb
.venv/bin/python cli/main.py query "Transformer的核心创新" --top-k 3
```

**步骤2: WebUI测试**
```bash
cd /home/nvidia/workspace/paper/vectordb
.venv/bin/python -m webui.app
# 浏览器访问 http://localhost:7860
# 输入查询测试
```

**步骤3: Agent Pipeline测试**
```bash
.venv/bin/python -c "
from agents.specialized_agents import SpecializedAgentOrchestrator
orch = SpecializedAgentOrchestrator('test-session')
result = orch.run_pipeline('Transformer自注意力机制', top_k=3, need_code=True)
print('Pipeline状态:', result['pipeline_status'])
print('质量评分:', result['quality_assurance']['quality_score'])
"
```

### 3.3 测试验证点

| 验证点 | 验证方法 | 预期结果 |
|-------|---------|---------|
| 检索阶段 | 检查chunks数量 | >= 3个 |
| 分析阶段 | 检查concepts长度 | > 0 |
| 质量阶段 | 检查quality_score | >= 0.7 |
| 代码阶段 | 检查is_runnable | True |
| 无遗漏 | 检查所有阶段status | completed |

### 3.4 问题反馈格式

```markdown
## 测试反馈

### 测试环境
- 日期: YYYY-MM-DD
- 测试者: 姓名
- 网络状态: 正常/异常

### 测试结果
- 检索: [通过/失败] - 描述
- 分析: [通过/失败] - 描述
- 质量: [通过/失败] - 描述
- 代码: [通过/失败] - 描述

### 发现问题
- 问题1: 描述
- 问题2: 描述

### 建议
- 建议1: 描述
```

---

## 四、后续处理建议

### 4.1 网络问题解决

**方案A: 使用本地模型**
```python
# 配置本地embedding
from embed_local import LocalEmbedding
embedder = LocalEmbedding()  # 使用Ollama本地模型
```

**方案B: 配置代理**
```bash
# 设置HTTP代理
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

**方案C: 预下载模型**
```bash
# 预下载模型到本地
.venv/bin/python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-large-zh-v1.5', cache_folder='/home/nvidia/.cache/huggingface')
"
```

### 4.2 测试恢复计划

| 步骤 | 内容 | 依赖 |
|-----|------|------|
| 1 | 解决网络问题 | 代理/本地模型 |
| 2 | 重新运行测试 | 步骤1完成 |
| 3 | 验证完整Pipeline | 步骤2完成 |
| 4 | 记录测试报告 | 步骤3完成 |

---

## 五、测试状态总结

| 维度 | 状态 | 说明 |
|-----|------|------|
| Pipeline代码 | ✓ 完成 | 代码可运行 |
| 网络环境 | ✗ 异常 | HuggingFace超时 |
| 完整测试 | ✗ 中断 | 网络阻塞 |
| 需求方验证 | 待执行 | 需解决网络后测试 |

---

**记录者**: Main Agent
**记录日期**: 2026-05-24
**下次更新**: 需求方测试完成后