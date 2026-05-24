# Agent 工程化管理体系设计

## 一、上下文管理工程化

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                  Context Management System               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  输入层                                                  │
│  ├── 查询预处理 (Query Preprocessing)                   │
│  ├── 意图识别 (Intent Detection)                        │
│  └── 上下文相关性评估 (Context Relevance)               │
│                                                         │
│  管理层                                                  │
│  ├── 窗口管理器 (Window Manager)                        │
│  │   └── Token预算: 8000检索 + 4000生成                 │
│  ├── 上下文压缩器 (Context Compressor)                  │
│  │   └── 摘要压缩 + 重要性筛选                          │
│  ├── 重要度排序器 (Importance Ranker)                   │
│  │   ├── Anti-Lost-in-the-Middle                        │
│  │   └── 降序重组 (重要内容放首位和末尾)                │
│  └── 上下文摘要器 (Context Summarizer)                  │
│                                                         │
│  存储层                                                  │
│  ├── Session Context (瞬时)                             │
│  ├── Conversation Context (中期)                        │
│  └── User Preferences (长期)                            │
│                                                         │
│  输出层                                                  │
│  ├── Prompt组装器                                       │
│  ├── Token计数器                                        │
│  └── 上下文注入器                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Anti-Lost-in-the-Middle 实现

```python
class AntiLostMiddleManager:
    """
    防止"迷失在中间"问题
    重要内容放在开头和结尾，次要内容放在中间
    """
    
    def arrange_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """重排chunks避免中间迷失"""
        # 按重要度评分
        scored_chunks = [(chunk, self._score_importance(chunk)) for chunk in chunks]
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # 降序重组: 最重要放开头，次重要放结尾，中间放次要
        arranged = []
        for i, (chunk, score) in enumerate(scored_chunks):
            if i < 3:  # 前3个最重要放开头
                arranged.append(chunk)
            elif i >= len(scored_chunks) - 3:  # 后3个放结尾
                arranged.append(chunk)
            else:  # 其余放中间
                arranged.insert(3 + (i - 3), chunk)
        
        return arranged
    
    def _score_importance(self, chunk: Chunk) -> float:
        """重要度评分"""
        factors = {
            "query_similarity": chunk.similarity_score,
            "citation_count": chunk.metadata.get("citation_count", 0),
            "section_type": 1.0 if chunk.metadata.get("section") == "abstract" else 0.5,
        }
        return sum(factors.values()) / len(factors)
```

### Token预算分配

```
总Token预算: 128000 (Claude/GLM-5)

分配策略:
├── 系统提示词: 1000 tokens
├── 检索上下文: 8000 tokens
│   ├── 检索结果: 6000 tokens (10 chunks × 600)
│   └── 父块上下文: 2000 tokens
├── 用户查询: 500 tokens
├── 历史对话: 2000 tokens (压缩后)
├── 生成空间: 4000 tokens
└── 预留缓冲: 500 tokens
```

## 二、记忆系统工程化

### 记忆分层架构

```
┌─────────────────────────────────────────────────────────┐
│                  Memory System Architecture              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  记忆类型                                                │
│                                                         │
│  瞬时记忆 (Transient Memory)                            │
│  ├── 存储: 当前对话状态                                 │
│  ├── 生命周期: 单轮对话                                 │
│  └── 例子: 当前查询、中间结果                           │
│                                                         │
│  短期记忆 (Short-term Memory)                           │
│  ├── 存储: Session Context                             │
│  ├── 生命周期: 用户会话                                 │
│  └── 例子: 对话历史、检索缓存                           │
│                                                         │
│  中期记忆 (Medium-term Memory)                          │
│  ├── 存储: Conversation Context                        │
│  ├── 生命周期: 多日会话                                 │
│  └── 例子: 用户偏好、常用查询                           │
│                                                         │
│  长期记忆 (Long-term Memory)                            │
│  ├── 存储: User Profile + Vector Store                 │
│  ├── 生命周期: 永久                                     │
│  └── 例子: 用户知识库、个人设置                         │
│                                                         │
│  程序记忆 (Procedural Memory)                           │
│  ├── 存储: Agent Skill Database                        │
│  ├── 生命周期: 永久                                     │
│  └── 例子: 学到的解题模式、优化策略                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 记忆存储实现

```python
class MemoryManager:
    """记忆管理器"""
    
    def __init__(self):
        self.transient = {}  # 瞬时: 内存dict
        self.session_file = "session_memory.json"  # 短期: JSON文件
        self.conv_db = sqlite3.connect("conversation.db")  # 中期: SQLite
        self.long_term = ChromaDB("user_memory")  # 长期: 向量库
    
    def save_memory(self, memory_type: str, key: str, value: Any):
        """保存记忆"""
        if memory_type == "transient":
            self.transient[key] = value
        elif memory_type == "session":
            self._save_session(key, value)
        elif memory_type == "conversation":
            self._save_conversation(key, value)
        elif memory_type == "long_term":
            self._save_long_term(key, value)
    
    def retrieve_memory(self, query: str, memory_types: List[str]) -> List[Memory]:
        """检索记忆"""
        memories = []
        for mtype in memory_types:
            if mtype == "long_term":
                # 向量检索长期记忆
                results = self.long_term.search(query, top_k=5)
                memories.extend(results)
        return memories
```

### 记忆衰减算法

```python
class MemoryDecay:
    """记忆衰减 (参考人类记忆Ebbinghaus曲线)"""
    
    def calculate_retention(self, memory: Memory) -> float:
        """计算记忆保留度"""
        age_hours = (now() - memory.created_at).total_seconds() / 3600
        
        # Ebbinghaus遗忘曲线: R = e^(-t/S)
        # S = 记忆强度 (访问次数 × 重要性)
        strength = memory.access_count * memory.importance
        
        retention = math.exp(-age_hours / strength)
        
        return retention
    
    def prune_memories(self, threshold: float = 0.1):
        """清理低保留度记忆"""
        for memory in self.all_memories:
            if self.calculate_retention(memory) < threshold:
                self.delete(memory)
```

## 三、提示词工程化管理

### 模板仓库结构

```
prompts/
├── v2025.12.01/              # CalVer版本
│   ├── paper_analysis/
│   │   ├── summary.yaml      # 摘要生成模板
│   │   ├── concept.yaml      # 概念提炼模板
│   │   ├── formula.yaml      # 公式解释模板
│   │   └── code_gen.yaml     # 代码生成模板
│   ├── rag/
│   │   ├── interpret.yaml    # 查询解析模板
│   │   ├── grade.yaml        # 文档分级模板
│   │   ├── generate.yaml     # 答案生成模板
│   │   └ reflect.yaml        # 自省评估模板
│   │   └── citation.yaml     # 引用标注模板
│   └── CHANGELOG.md          # 变更日志
│
├── v2025.11.15/              # 前一版本
│   └── ...
│
└── current -> v2025.12.01/   # 当前版本指针
```

### 提示词模板示例

```yaml
# prompts/v2025.12.01/rag/generate.yaml

version: "2025.12.01"
name: "answer_generation"
description: "生成带Citation的答案"

template: |
  你是一个学术论文知识库的AI助手。
  
  ## 任务
  根据检索到的论文片段，回答用户问题。
  
  ## 严格要求
  1. 每个事实声明必须标注来源 [chunk_id]
  2. 不得编造论文中未提及的内容
  3. 如果信息不足，明确说明
  
  ## 检索结果
  {chunks}
  
  ## 用户问题
  {query}
  
  ## 输出格式
  答案: [你的回答]
  Citations:
  - Claim: [声明]
    Source: [chunk_id]
    Text: [原文片段]

variables:
  - chunks: List[Chunk]
  - query: str

output_schema:
  answer: str
  citations: List[Citation]
  
metrics:
  hallucination_rate: 0.03
  citation_accuracy: 0.95
  user_satisfaction: 4.2/5
```

### 版本管理机制

```python
class PromptVersionManager:
    """提示词版本管理"""
    
    def __init__(self, prompts_dir: str):
        self.prompts_dir = prompts_dir
        self.current_version = self._load_current_version()
    
    def get_template(self, name: str) -> PromptTemplate:
        """获取当前版本模板"""
        path = f"{self.prompts_dir}/current/{name}.yaml"
        return self._load_yaml(path)
    
    def rollback(self, target_version: str):
        """回滚到指定版本"""
        self.current_version = target_version
        # 更新current指针
        os.symlink(f"{self.prompts_dir}/{target_version}", 
                   f"{self.prompts_dir}/current")
    
    def ab_test(self, template_a: str, template_b: str, samples: int = 100):
        """A/B测试"""
        results_a = self._test_template(template_a, samples)
        results_b = self._test_template(template_b, samples)
        
        # 统计显著性检验
        if results_a.hallucination_rate < results_b.hallucination_rate:
            return template_a
        return template_b
```

## 四、运营监测指标体系

### 六层监测指标

```
┌─────────────────────────────────────────────────────────┐
│                  Agent Operations Monitoring             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  L1: 基础运行指标                                       │
│  ├── Request Count: Σ requests                         │
│  ├── Success Rate: success / total                     │
│  ├── Response Time: P50/P95/P99                        │
│  ├── Error Rate: errors / total                        │
│  ├── Token Consumption: Σ tokens                       │
│  └── Concurrency: concurrent requests                  │
│                                                         │
│  L2: 质量指标                                           │
│  ├── Retrieval Hit Rate: hits / queries                │
│  ├── Retrieval Accuracy: correct / retrieved           │
│  ├── Hallucination Rate: false claims / all claims     │
│  ├── Citation Accuracy: valid citations / all          │
│  ├── Answer Satisfaction: avg(user_score)              │
│  ├── Code Success Rate: passed tests / generated       │
│  └── Test Pass Rate: passed / all tests                │
│                                                         │
│  L3: Agent行为指标                                      │
│  ├── Tool Call Count: Σ tool_calls                     │
│  ├── Tool Success Rate: success / calls                │
│  ├── Reflection Count: Σ reflections                   │
│  ├── Retry Count: Σ retries                            │
│  ├── State Transitions: Σ transitions                  │
│  └── Loop Depth: max iteration depth                   │
│                                                         │
│  L4: 用户体验指标                                       │
│  ├── User Satisfaction: avg(survey_score)              │
│  ├── Task Completion: completed / started              │
│  ├── First Try Success: first_success / all            │
│  ├── User Feedback Rate: feedbacks / responses         │
│  └── Avg Interaction Rounds: Σ rounds / tasks          │
│                                                         │
│  L5: 成本效率指标                                       │
│  ├── Token Efficiency: output_tokens / input_tokens    │
│  ├── Time Efficiency: human_time / ai_time             │
│  ├── Retrieval Efficiency: useful_chunks / retrieved   │
│  ├── Cost Per Task: total_cost / tasks                 │
│  └── ROI: value_created / cost                         │
│                                                         │
│  L6: 安全合规指标                                       │
│  ├── Injection Attack Count: Σ attacks                 │
│  ├── Security Alert Count: Σ alerts                    │
│  ├── Data Leak Risk: high_risk_outputs / all           │
│  ├── Compliance Pass Rate: passed / checked            │
│  └── Audit Coverage: audited / total                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 告警规则设计

```python
class AlertRules:
    """告警规则配置"""
    
    ALERT_THRESHOLDS = {
        # L1 运行告警
        "error_rate_high": {"threshold": 0.05, "level": "warning"},
        "response_time_slow": {"threshold": 5000, "unit": "ms", "level": "warning"},
        "concurrency_overload": {"threshold": 100, "level": "critical"},
        
        # L2 质量告警
        "hallucination_high": {"threshold": 0.05, "level": "critical"},
        "citation_accuracy_low": {"threshold": 0.90, "level": "warning"},
        "retrieval_hit_low": {"threshold": 0.70, "level": "warning"},
        
        # L3 Agent行为告警
        "retry_excessive": {"threshold": 3, "level": "warning"},
        "loop_depth_deep": {"threshold": 5, "level": "warning"},
        
        # L6 安全告警
        "injection_attack": {"threshold": 1, "level": "critical"},
        "data_leak_risk": {"threshold": 0.01, "level": "critical"},
    }
    
    def check_alerts(self, metrics: Dict) -> List[Alert]:
        """检查告警"""
        alerts = []
        for metric_name, config in self.ALERT_THRESHOLDS.items():
            value = metrics.get(metric_name)
            if value > config["threshold"]:
                alerts.append(Alert(
                    name=metric_name,
                    value=value,
                    threshold=config["threshold"],
                    level=config["level"]
                ))
        return alerts
```

### Dashboard设计

```
┌────────────────────────────────────────────────────────────────────┐
│  📊 Agent Operations Dashboard                    Last Update: 3s   │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ Request Rate    │  │ Success Rate    │  │ Avg Response    │    │
│  │ 125 req/min     │  │ 98.5%           │  │ 1.2s            │    │
│  │ [📈 +5%]        │  │ [✓ Target >95%] │  │ [✓ <2s]         │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ Hallucination   │  │ Citation Acc    │  │ Retrieval Hit   │    │
│  │ 2.3%            │  │ 96.2%           │  │ 82.5%           │    │
│  │ [✓ <5%]         │  │ [✓ >95%]        │  │ [⚠ <85% target] │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                    │
│  [Real-time Chart: Response Time Distribution]                     │
│  [Historical Trend: Quality Metrics 7-day]                         │
│  [Alert Panel: 2 warnings, 0 critical]                             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

**创建时间**: 2026-05-24
**状态**: 初版设计