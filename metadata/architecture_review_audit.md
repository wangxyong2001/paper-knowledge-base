# RAG系统审计日志与监测系统架构审核报告

> 审核日期: 2026-05-24
> 审核人: System Architect Agent
> 版本: v1.0

---

## 执行摘要

本报告审核了论文检索RAG系统的审计日志和监测系统设计。整体设计方向正确，覆盖了核心审计需求，但存在以下关键问题需要解决：

| 优先级 | 问题 | 影响 |
|--------|------|------|
| P0 | 缺少API调用追踪表 | 无法关联云端API调用与审计日志 |
| P0 | 缺少用户反馈表 | 无法收集用户满意度数据 |
| P1 | 索引策略不完整 | 大数据量下查询性能下降 |
| P1 | 缺少数据生命周期管理 | 数据无限增长导致存储问题 |
| P2 | 监测指标采集点缺失 | 指标定义完整但采集逻辑未集成 |

---

## 1. Schema设计审核

### 1.1 当前表结构评估

#### audit_logs 表

**优点:**
- 单表设计简洁，支持事件追溯
- event_type分类清晰 (input/prompt/llm_call/output/error/retrieval/quality/security)
- JSON字段(metadata)支持灵活扩展

**问题:**
```sql
-- 问题1: 缺少主键外的唯一约束
-- 同一事件可能被重复记录

-- 问题2: 缺少query_id关联字段
-- 无法追踪单个查询的完整生命周期

-- 问题3: llm_request_id字段类型不匹配
-- DashScope/GLM-5返回的是字符串UUID，但无格式验证
```

**建议修改:**
```sql
ALTER TABLE audit_logs ADD COLUMN query_id TEXT;
CREATE INDEX idx_audit_query ON audit_logs(query_id);
CREATE UNIQUE INDEX idx_audit_unique ON audit_logs(session_id, query_id, event_type, timestamp);
```

#### sessions 表

**优点:**
- 统计字段设计合理
- 状态管理完整

**问题:**
```sql
-- 缺少用户标识字段
-- 当前user_id是TEXT但无验证

-- 缺少会话类型字段
-- 无法区分qa/analysis/batch等不同类型会话
```

**建议补充:**
```sql
ALTER TABLE sessions ADD COLUMN session_type TEXT DEFAULT 'qa';
ALTER TABLE sessions ADD COLUMN client_ip TEXT;
ALTER TABLE sessions ADD COLUMN user_agent TEXT;
```

#### retrieval_records 表

**优点:**
- 检索质量指标完整 (precision/recall/mrr)
- 支持混合检索参数记录

**问题:**
- 缺少检索策略字段
- 缺少重排序记录

#### prompt_templates 表

**优点:**
- 版本管理设计合理
- 支持效果统计

**问题:**
- 缺少模板变更历史
- 缺少A/B测试支持

---

### 1.2 需要补充的表

#### P0: api_calls 表 (云端API调用追踪)

```sql
CREATE TABLE api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT UNIQUE NOT NULL,         -- API调用唯一ID
    session_id TEXT NOT NULL,
    query_id TEXT,

    -- API信息
    provider TEXT NOT NULL,               -- dashscope/anthropic/openai
    model TEXT NOT NULL,                  -- glm-5/claude-sonnet-4
    endpoint TEXT,                         -- /v1/chat/completions

    -- 请求响应
    request_timestamp TEXT NOT NULL,
    response_timestamp TEXT,
    latency_ms INTEGER,

    -- Token统计
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,

    -- 成本
    estimated_cost REAL,                  -- 估算成本(USD)

    -- 状态
    status TEXT NOT NULL,                 -- pending/success/failed/timeout
    error_code TEXT,
    error_message TEXT,

    -- 重试信息
    retry_count INTEGER DEFAULT 0,
    retry_reason TEXT,

    -- 元数据
    metadata TEXT,                        -- JSON格式扩展

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_api_calls_session ON api_calls(session_id);
CREATE INDEX idx_api_calls_timestamp ON api_calls(request_timestamp);
CREATE INDEX idx_api_calls_status ON api_calls(status);
```

#### P0: user_feedback 表 (用户反馈收集)

```sql
CREATE TABLE user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    query_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,

    -- 反馈类型
    feedback_type TEXT NOT NULL,          -- rating/correction/rejection

    -- 评分反馈
    rating INTEGER,                        -- 1-5分
    rating_aspect TEXT,                    -- helpfulness/accuracy/completeness

    -- 纠正反馈
    expected_answer TEXT,                  -- 用户期望的答案
    correction_text TEXT,                  -- 用户纠正内容

    -- 拒绝原因
    rejection_reason TEXT,

    -- 元数据
    metadata TEXT,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_feedback_session ON user_feedback(session_id);
CREATE INDEX idx_feedback_timestamp ON user_feedback(timestamp);
```

#### P1: system_health 表 (系统健康快照)

```sql
CREATE TABLE system_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TEXT NOT NULL,

    -- 系统资源
    cpu_usage REAL,
    memory_usage REAL,
    gpu_usage REAL,
    disk_usage REAL,

    -- 服务状态
    embedding_service_status TEXT,
    vector_db_status TEXT,
    llm_api_status TEXT,

    -- 队列状态
    pending_requests INTEGER,
    active_sessions INTEGER,

    -- 错误统计
    error_count_1h INTEGER,
    error_count_24h INTEGER,

    metadata TEXT
);

CREATE INDEX idx_health_time ON system_health(snapshot_time);
```

#### P1: quality_assessments 表 (质量评估记录)

```sql
CREATE TABLE quality_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    query_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,

    -- 评估维度
    assessment_type TEXT NOT NULL,         -- auto/manual

    -- 忠诚度评估
    faithfulness_score REAL,               -- 答案对上下文的忠诚度
    answer_relevance_score REAL,           -- 答案与问题的相关性
    context_precision REAL,                -- 检索上下文精度
    context_recall REAL,                   -- 检索上下文召回

    -- 幻觉评估
    hallucination_type TEXT,               -- fabrication/contradiction/unsupported
    hallucinated_claims TEXT,              -- JSON数组

    -- 引用评估
    citation_precision REAL,
    citation_recall REAL,
    missing_citations TEXT,                -- JSON数组

    -- 完整性评估
    completeness_score REAL,
    missing_aspects TEXT,                  -- JSON数组

    -- 审核者
    reviewer_id TEXT,                      -- 人工审核时
    review_notes TEXT,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_quality_session ON quality_assessments(session_id);
CREATE INDEX idx_quality_type ON quality_assessments(assessment_type);
```

#### P2: data_retention_policy 表 (数据保留策略)

```sql
CREATE TABLE data_retention_policy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    retention_days INTEGER NOT NULL,
    archive_location TEXT,
    archive_format TEXT,

    -- 条件
    archive_condition TEXT,                -- SQL条件

    created_at TEXT NOT NULL,
    updated_at TEXT,

    UNIQUE(table_name)
);
```

---

### 1.3 索引策略优化

当前索引:
```sql
idx_audit_session ON audit_logs(session_id)
idx_audit_timestamp ON audit_logs(timestamp)
idx_metrics_name ON metrics(metric_name)
idx_metrics_timestamp ON metrics(timestamp)
idx_retrieval_session ON retrieval_records(session_id)
idx_injection_timestamp ON injection_attacks(timestamp)
```

**需要补充的索引:**
```sql
-- 复合索引 (高频查询优化)
CREATE INDEX idx_audit_session_time ON audit_logs(session_id, timestamp);
CREATE INDEX idx_audit_type_time ON audit_logs(event_type, timestamp);

-- 覆盖索引 (避免回表)
CREATE INDEX idx_metrics_coverage ON metrics(metric_name, timestamp, metric_value, category);

-- 全文搜索 (支持日志搜索)
-- SQLite FTS5 虚拟表
CREATE VIRTUAL TABLE audit_logs_fts USING fts5(
    user_query, raw_output, formatted_output,
    content=audit_logs, content_rowid=id
);
```

---

## 2. 审计覆盖完整性检查

### 2.1 覆盖矩阵

| 审计需求 | audit_logs | 专用表 | 覆盖状态 | 缺失项 |
|----------|------------|--------|----------|--------|
| 用户输入记录 | log_input() | - | PARTIAL | 缺少client_ip, user_agent |
| Prompt重构记录 | log_prompt() | prompt_templates | OK | - |
| LLM调用记录 | log_llm_call() | api_calls (需新增) | PARTIAL | 缺少重试机制记录 |
| 输出格式化记录 | log_output() | - | OK | - |
| 检索过程记录 | log_retrieval() | retrieval_records | OK | 缺少重排序记录 |
| 注入检测记录 | log_injection_detection() | injection_attacks | OK | - |
| 幻觉检测记录 | log_hallucination() | hallucination_records | OK | - |
| 质量评估记录 | log_quality_metrics() | quality_assessments (需新增) | PARTIAL | 缺少维度细分 |
| 用户反馈记录 | - | user_feedback (需新增) | MISSING | 完全缺失 |
| API调用追踪 | - | api_calls (需新增) | MISSING | 完全缺失 |

### 2.2 审计事件生命周期

```
用户输入 → 意图解析 → 注入检测 → Prompt重构 → 检索 →
文档分级 → LLM调用 → 输出生成 → 幻觉检测 → Citation检查 → 格式化输出
    ↓           ↓           ↓           ↓        ↓
 [input]   [security]   [prompt]   [retrieval] [llm_call]
                                                        ↓
                                              [output] + [quality]
```

**当前audit_logger.py事件类型:**
- input: log_input()
- prompt: log_prompt()
- llm_call: log_llm_call()
- output: log_output()
- retrieval: log_retrieval()
- security: log_injection_detection()
- quality: log_hallucination() + log_quality_metrics()
- error: log_error()

**需要补充的事件类型:**
- intent: 意图解析结果
- grade: 文档分级结果
- reflect: 自省评估结果
- retry: 重试事件
- escalate: 熔断事件
- feedback: 用户反馈事件

---

## 3. 监测指标完整性检查

### 3.1 六层指标覆盖度

#### L1: 基础运行指标

| 指标 | 定义 | 采集点 | 状态 |
|------|------|--------|------|
| request_count | 请求数 | audit_logs | OK |
| success_rate | 成功率 | audit_logs | OK |
| error_rate | 错误率 | audit_logs | OK |
| avg_response_time_ms | 平均响应时间 | audit_logs.llm_latency_ms | OK |
| p95_response_time_ms | P95响应时间 | 需计算 | MISSING |
| total_tokens_input | 输入Token数 | audit_logs.llm_input_tokens | OK |
| total_tokens_output | 输出Token数 | audit_logs.llm_output_tokens | OK |
| concurrent_requests | 并发请求数 | 需运行时计算 | MISSING |

**建议:**
- 添加百分位计算逻辑
- 实现并发请求计数器

#### L2: 质量指标

| 指标 | 定义 | 采集点 | 状态 |
|------|------|--------|------|
| retrieval_hit_rate | 检索命中率 | retrieval_records | OK |
| retrieval_precision_5 | P@5 | retrieval_records | OK |
| retrieval_recall_10 | R@10 | retrieval_records | OK |
| mrr | 平均倒数排名 | retrieval_records | OK |
| hallucination_rate | 幻觉率 | hallucination_records | OK |
| citation_accuracy | 引用准确率 | audit_logs | OK |
| answer_satisfaction | 答案满意度 | user_feedback (需新增) | MISSING |
| code_success_rate | 代码成功率 | 需单独表 | MISSING |
| test_pass_rate | 测试通过率 | 需单独表 | MISSING |

**建议:**
- 新增user_feedback表收集满意度
- 考虑代码执行结果的单独表

#### L3: Agent行为指标

| 指标 | 定义 | 采集点 | 状态 |
|------|------|--------|------|
| tool_call_count | 工具调用次数 | 需新增事件 | MISSING |
| tool_success_rate | 工具成功率 | 需新增事件 | MISSING |
| reflection_count | 自省次数 | Agent状态 | MISSING |
| retry_count | 重试次数 | Agent状态 | MISSING |
| state_transitions | 状态转换数 | Agent状态 | MISSING |
| avg_loop_depth | 平均循环深度 | Agent状态 | MISSING |

**问题:**
- 当前LangGraph Agent未集成指标采集
- 需要在Agent节点中添加采集点

**建议修改 paper_rag_agent.py:**
```python
def _retrieve_node(self, state: PaperRAGState) -> PaperRAGState:
    metrics_collector.collect("tool_call_count", 1)
    # ... existing code ...
    metrics_collector.collect("retrieval_latency_ms", latency)
```

#### L4: 用户体验指标

| 指标 | 定义 | 采集点 | 状态 |
|------|------|--------|------|
| user_satisfaction_avg | 用户满意度均值 | user_feedback (需新增) | MISSING |
| task_completion_rate | 任务完成率 | sessions表 | PARTIAL |
| first_try_success_rate | 首次成功率 | 需计算 | MISSING |
| avg_interaction_rounds | 平均交互轮数 | sessions表 | PARTIAL |

**建议:**
- 新增user_feedback表
- 计算首次成功率逻辑

#### L5: 成本效率指标

| 指标 | 定义 | 采集点 | 状态 |
|------|------|--------|------|
| token_efficiency | Token效率 | api_calls (需新增) | MISSING |
| time_efficiency | 时间效率 | 需计算 | MISSING |
| cost_per_task | 单任务成本 | api_calls (需新增) | MISSING |
| retrieval_efficiency | 检索效率 | retrieval_records | PARTIAL |

**建议:**
- 新增api_calls表记录Token成本
- 实现成本计算逻辑

#### L6: 安全合规指标

| 指标 | 定义 | 采集点 | 状态 |
|------|------|--------|------|
| injection_attack_count | 注入攻击数 | injection_attacks | OK |
| security_alert_count | 安全告警数 | injection_attacks | OK |
| data_leak_risk | 数据泄露风险 | 需计算 | MISSING |
| compliance_pass_rate | 合规通过率 | 需单独表 | MISSING |
| audit_coverage_rate | 审计覆盖率 | 需计算 | MISSING |

**建议:**
- 实现数据泄露风险评估
- 添加合规检查表

### 3.2 指标采集点缺失汇总

```
metrics_collector.py 定义了39个指标
实际有采集点的: 15个 (38%)
定义但无采集:    24个 (62%)

优先补充采集点:
1. Agent行为指标 - 在LangGraph节点中添加
2. 用户体验指标 - 新增user_feedback表后实现
3. 成本效率指标 - 新增api_calls表后实现
```

---

## 4. 长期监测考虑

### 4.1 数据量增长预估

| 表 | 日均增长 | 月增长 | 年增长 |
|----|----------|--------|--------|
| audit_logs | ~10,000行 | ~300,000行 | ~3.6M行 |
| metrics | ~50,000行 | ~1.5M行 | ~18M行 |
| sessions | ~500行 | ~15,000行 | ~180K行 |
| retrieval_records | ~5,000行 | ~150,000行 | ~1.8M行 |

**预估前提:** 100活跃用户/天，每人平均20次查询

### 4.2 查询性能影响

**当前问题:**
1. metrics表按timestamp查询，无分区策略
2. audit_logs表JSON字段(metadata)无法索引
3. 无预聚合表，实时查询压力大

**优化方案:**

```sql
-- 1. 创建预聚合表
CREATE TABLE metrics_hourly (
    hour_timestamp TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    avg_value REAL,
    min_value REAL,
    max_value REAL,
    sum_value REAL,
    count_value INTEGER,
    PRIMARY KEY (hour_timestamp, metric_name)
);

CREATE TABLE metrics_daily (
    day_date TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    avg_value REAL,
    min_value REAL,
    max_value REAL,
    sum_value REAL,
    count_value INTEGER,
    PRIMARY KEY (day_date, metric_name)
);

-- 2. 创建物化视图 (SQLite使用触发器模拟)
CREATE TRIGGER update_metrics_hourly
AFTER INSERT ON metrics
BEGIN
    INSERT OR REPLACE INTO metrics_hourly
    SELECT
        strftime('%Y-%m-%d %H:00:00', NEW.timestamp),
        NEW.metric_name,
        AVG(metric_value),
        MIN(metric_value),
        MAX(metric_value),
        SUM(metric_value),
        COUNT(*)
    FROM metrics
    WHERE metric_name = NEW.metric_name
    AND timestamp >= strftime('%Y-%m-%d %H:00:00', NEW.timestamp)
    AND timestamp < strftime('%Y-%m-%d %H:00:00', NEW.timestamp, '+1 hour');
END;
```

### 4.3 数据归档策略

```sql
-- 归档策略定义
INSERT INTO data_retention_policy VALUES
    ('audit_logs', 90, '/archive/audit_logs/', 'parquet', "event_type != 'error'", datetime('now'), datetime('now')),
    ('metrics', 30, '/archive/metrics/', 'parquet', '1=1', datetime('now'), datetime('now')),
    ('sessions', 365, '/archive/sessions/', 'parquet', '1=1', datetime('now'), datetime('now')),
    ('retrieval_records', 90, '/archive/retrieval/', 'parquet', '1=1', datetime('now'), datetime('now'));
```

**归档实现脚本:**
```python
def archive_old_data(table_name: str, retention_days: int, archive_path: str):
    """归档过期数据"""
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    # 1. 导出数据到Parquet
    df = pd.read_sql(f"""
        SELECT * FROM {table_name}
        WHERE timestamp < ?
    """, conn, params=(cutoff_date.isoformat(),))

    df.to_parquet(f"{archive_path}/{table_name}_{cutoff_date.date()}.parquet")

    # 2. 删除已归档数据
    cursor.execute(f"""
        DELETE FROM {table_name}
        WHERE timestamp < ?
    """, (cutoff_date.isoformat(),))

    conn.commit()
```

### 4.4 备份恢复方案

```bash
# 备份脚本
#!/bin/bash
BACKUP_DIR="/backup/rag_system"
DATE=$(date +%Y%m%d)

# 全量备份
sqlite3 /home/nvidia/workspace/paper/vectordb/rag_system.db ".backup ${BACKUP_DIR}/rag_system_${DATE}.db"

# 压缩
gzip ${BACKUP_DIR}/rag_system_${DATE}.db

# 保留最近30天
find ${BACKUP_DIR} -name "*.gz" -mtime +30 -delete

# 远程同步 (可选)
rsync -avz ${BACKUP_DIR}/ rag-backup-server:/backup/
```

---

## 5. 云端API集成设计

### 5.1 DashScope/GLM-5 API调用架构

```
┌─────────────────────────────────────────────────────────────┐
│                    API Call Flow                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Agent Node → APIWrapper → RateLimiter → RetryPolicy       │
│       │            │              │              │          │
│       ▼            ▼              ▼              ▼          │
│   [采集指标]   [记录api_calls] [限流控制]  [重试逻辑]      │
│                                                             │
│  APIResponse → ResponseParser → CostCalculator → Auditor   │
│       │              │               │              │       │
│       ▼              ▼               ▼              ▼       │
│   [解析输出]   [提取Token]    [计算成本]   [记录审计]       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 API调用封装实现

```python
# api_client.py

import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Optional
import uuid

class DashScopeClient:
    """DashScope/GLM-5 API 客户端"""

    ENDPOINTS = {
        "chat": "/v1/chat/completions",
        "embeddings": "/v1/embeddings",
    }

    MODELS = {
        "glm-5": "glm-5",
        "glm-4-plus": "glm-4-plus",
        "qwen-turbo": "qwen-turbo",
    }

    # 定价 (USD per 1K tokens)
    PRICING = {
        "glm-5": {"input": 0.001, "output": 0.002},
        "glm-4-plus": {"input": 0.002, "output": 0.004},
        "qwen-turbo": {"input": 0.0005, "output": 0.001},
    }

    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None
        self.audit_logger = None  # 注入
        self.metrics_collector = None  # 注入

    async def chat(
        self,
        messages: list,
        model: str = "glm-5",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        session_id: str = None,
        query_id: str = None,
        **kwargs
    ) -> Dict:
        """聊天接口"""

        call_id = f"call_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()

        # 估算输入Token
        input_text = " ".join([m.get("content", "") for m in messages])
        input_tokens = self._estimate_tokens(input_text)

        # 记录请求开始
        await self._log_api_call_start(call_id, session_id, query_id, model, input_tokens)

        try:
            response = await self._make_request(
                endpoint=self.ENDPOINTS["chat"],
                payload={
                    "model": self.MODELS.get(model, model),
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                },
                call_id=call_id
            )

            # 计算延迟
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 解析响应
            output_text = response["choices"][0]["message"]["content"]
            output_tokens = response.get("usage", {}).get("completion_tokens", self._estimate_tokens(output_text))
            total_tokens = input_tokens + output_tokens

            # 计算成本
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            # 记录成功
            await self._log_api_call_success(
                call_id=call_id,
                session_id=session_id,
                query_id=query_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost=cost,
                raw_output=output_text
            )

            return {
                "content": output_text,
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": total_tokens,
                },
                "cost": cost,
                "latency_ms": latency_ms,
                "call_id": call_id,
            }

        except Exception as e:
            # 记录失败
            await self._log_api_call_failure(
                call_id=call_id,
                session_id=session_id,
                query_id=query_id,
                model=model,
                error=str(e)
            )
            raise

    async def _make_request(self, endpoint: str, payload: Dict, call_id: str, retries: int = 3) -> Dict:
        """发送请求，带重试"""

        if self.session is None:
            self.session = aiohttp.ClientSession()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Request-ID": call_id,
        }

        for attempt in range(retries):
            try:
                async with self.session.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limit
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        error_body = await response.text()
                        raise APIError(f"API error {response.status}: {error_body}")

            except aiohttp.ClientError as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise APIError("Max retries exceeded")

    def _estimate_tokens(self, text: str) -> int:
        """估算Token数"""
        # 中文约1.5字符/token，英文约4字符/token
        chinese_chars = len([c for c in text if '一' <= c <= '鿿'])
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算成本"""
        pricing = self.PRICING.get(model, {"input": 0.001, "output": 0.002})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

    async def _log_api_call_start(self, call_id: str, session_id: str, query_id: str, model: str, input_tokens: int):
        """记录API调用开始"""
        if self.audit_logger:
            cursor = self.audit_logger.conn.cursor()
            cursor.execute("""
                INSERT INTO api_calls
                (call_id, session_id, query_id, provider, model, request_timestamp,
                 status, prompt_tokens, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, 0)
            """, (call_id, session_id, query_id, "dashscope", model,
                  datetime.now().isoformat(), input_tokens))
            self.audit_logger.conn.commit()

    async def _log_api_call_success(self, call_id: str, session_id: str, query_id: str,
                                     model: str, input_tokens: int, output_tokens: int,
                                     latency_ms: int, cost: float, raw_output: str):
        """记录API调用成功"""
        if self.audit_logger:
            cursor = self.audit_logger.conn.cursor()
            cursor.execute("""
                UPDATE api_calls SET
                    response_timestamp = ?,
                    latency_ms = ?,
                    completion_tokens = ?,
                    total_tokens = ?,
                    estimated_cost = ?,
                    status = 'success'
                WHERE call_id = ?
            """, (datetime.now().isoformat(), latency_ms, output_tokens,
                  input_tokens + output_tokens, cost, call_id))
            self.audit_logger.conn.commit()

        # 采集指标
        if self.metrics_collector:
            self.metrics_collector.collect_batch({
                "avg_response_time_ms": latency_ms,
                "total_tokens_input": input_tokens,
                "total_tokens_output": output_tokens,
                "cost_per_task": cost,
            }, session_id)

    async def _log_api_call_failure(self, call_id: str, session_id: str, query_id: str,
                                     model: str, error: str):
        """记录API调用失败"""
        if self.audit_logger:
            cursor = self.audit_logger.conn.cursor()
            cursor.execute("""
                UPDATE api_calls SET
                    response_timestamp = ?,
                    status = 'failed',
                    error_message = ?
                WHERE call_id = ?
            """, (datetime.now().isoformat(), error, call_id))
            self.audit_logger.conn.commit()

        if self.metrics_collector:
            self.metrics_collector.collect("error_rate", 1, session_id)


class APIError(Exception):
    """API错误"""
    pass
```

### 5.3 错误重试机制设计

```python
class RetryPolicy:
    """重试策略"""

    STRATEGIES = {
        "exponential_backoff": {
            "base_delay": 1,
            "max_delay": 60,
            "multiplier": 2,
            "max_retries": 3,
        },
        "linear_backoff": {
            "base_delay": 2,
            "max_delay": 30,
            "multiplier": 1,
            "max_retries": 5,
        },
        "immediate": {
            "base_delay": 0,
            "max_delay": 0,
            "multiplier": 0,
            "max_retries": 1,
        }
    }

    RETRYABLE_ERRORS = [
        "rate_limit_exceeded",
        "timeout",
        "service_unavailable",
        "internal_error",
    ]

    def __init__(self, strategy: str = "exponential_backoff"):
        self.config = self.STRATEGIES[strategy]

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.config["max_retries"]:
            return False

        error_type = self._classify_error(error)
        return error_type in self.RETRYABLE_ERRORS

    def get_delay(self, attempt: int) -> float:
        """获取重试延迟"""
        delay = self.config["base_delay"] * (self.config["multiplier"] ** attempt)
        return min(delay, self.config["max_delay"])

    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        if isinstance(error, aiohttp.ClientError):
            return "timeout"
        if "rate limit" in str(error).lower():
            return "rate_limit_exceeded"
        if "500" in str(error):
            return "internal_error"
        return "unknown"
```

### 5.4 响应时间监控

```python
class ResponseTimeMonitor:
    """响应时间监控"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.collector = metrics_collector
        self.latency_buffer = []  # 滑动窗口
        self.buffer_size = 1000

    def record(self, latency_ms: int):
        """记录延迟"""
        self.latency_buffer.append(latency_ms)

        if len(self.latency_buffer) > self.buffer_size:
            self.latency_buffer.pop(0)

        # 计算统计指标
        sorted_latencies = sorted(self.latency_buffer)
        n = len(sorted_latencies)

        metrics = {
            "avg_response_time_ms": sum(sorted_latencies) / n,
            "p50_response_time_ms": sorted_latencies[int(n * 0.5)],
            "p90_response_time_ms": sorted_latencies[int(n * 0.9)],
            "p95_response_time_ms": sorted_latencies[int(n * 0.95)],
            "p99_response_time_ms": sorted_latencies[int(n * 0.99)],
        }

        self.collector.collect_batch(metrics)

    def check_sla(self, threshold_ms: int = 3000) -> Dict:
        """检查SLA"""
        if not self.latency_buffer:
            return {"compliant": True, "message": "No data"}

        p95 = sorted(self.latency_buffer)[int(len(self.latency_buffer) * 0.95)]
        compliant = p95 <= threshold_ms

        return {
            "compliant": compliant,
            "p95_ms": p95,
            "threshold_ms": threshold_ms,
            "message": "SLA compliant" if compliant else f"P95 ({p95}ms) exceeds threshold ({threshold_ms}ms)"
        }
```

---

## 6. 审核结论与建议

### 6.1 优先级排序

#### P0 - 必须立即解决

1. **新增api_calls表** - 无此表无法追踪云端API调用
2. **新增user_feedback表** - 无此表无法收集用户满意度
3. **添加query_id字段到audit_logs** - 无法追踪查询生命周期

#### P1 - 尽快解决

1. **完善索引策略** - 大数据量下性能问题
2. **实现预聚合表** - 实时查询压力
3. **集成Agent指标采集** - L3指标完全缺失
4. **新增quality_assessments表** - 质量评估维度不足

#### P2 - 可以延后

1. **数据归档策略** - 数据量尚小时可延后
2. **全文搜索索引** - 日志搜索需求可延后
3. **合规检查表** - 当前无合规需求

### 6.2 架构改进建议

```
┌─────────────────────────────────────────────────────────────────┐
│                    改进后架构                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ Agent   │───▶│  API    │───▶│ Audit   │───▶│ SQLite  │       │
│  │ Nodes   │    │ Wrapper │    │ Logger  │    │  DB     │       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│       │              │              │              │             │
│       ▼              ▼              ▼              ▼             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ Metrics │    │  Retry  │    │  FTS    │    │ Archive │       │
│  │Collector│    │ Policy  │    │ Index   │    │ Manager │       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Pre-aggregation Layer                        │   │
│  │  metrics_hourly | metrics_daily | session_summary         │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Dashboard Layer                       │   │
│  │   Runtime | Quality | Cost | Security | User Experience   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 开发人员后续实现建议

1. **Schema更新脚本** (1天)
   ```python
   # scripts/migrate_schema.py
   def migrate_v1_to_v2():
       # 添加新表
       # 添加新字段
       # 创建新索引
       pass
   ```

2. **API客户端集成** (2天)
   ```python
   # core/api_client.py - 实现DashScopeClient
   # core/retry_policy.py - 实现重试机制
   # core/response_monitor.py - 实现响应时间监控
   ```

3. **Agent指标采集集成** (1天)
   ```python
   # 修改 paper_rag_agent.py
   # 在每个节点添加 metrics_collector.collect() 调用
   ```

4. **Dashboard实现** (3天)
   ```python
   # web/dashboard.py
   # 使用 Streamlit 或 FastAPI + React
   ```

5. **归档与备份** (1天)
   ```bash
   # scripts/archive_old_data.py
   # scripts/backup_database.sh
   ```

### 6.4 验收标准

| 功能 | 验收标准 |
|------|----------|
| API调用追踪 | 每次LLM调用在api_calls表有完整记录 |
| 用户反馈 | 用户可对答案评分，数据存入user_feedback表 |
| 指标采集 | 6层指标采集覆盖率 > 80% |
| 查询性能 | P95查询延迟 < 100ms |
| 数据归档 | 数据自动归档到指定目录 |
| 备份恢复 | 从备份恢复时间 < 5分钟 |

---

## 附录A: 完整Schema更新SQL

```sql
-- Version 2 Schema Migration
-- 执行前请备份数据库

-- ===== 新增表 =====

-- API调用追踪表
CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    query_id TEXT,

    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    endpoint TEXT,

    request_timestamp TEXT NOT NULL,
    response_timestamp TEXT,
    latency_ms INTEGER,

    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,

    estimated_cost REAL,

    status TEXT NOT NULL,
    error_code TEXT,
    error_message TEXT,

    retry_count INTEGER DEFAULT 0,
    retry_reason TEXT,

    metadata TEXT,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- 用户反馈表
CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    query_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,

    feedback_type TEXT NOT NULL,

    rating INTEGER,
    rating_aspect TEXT,

    expected_answer TEXT,
    correction_text TEXT,

    rejection_reason TEXT,

    metadata TEXT,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- 系统健康快照表
CREATE TABLE IF NOT EXISTS system_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TEXT NOT NULL,

    cpu_usage REAL,
    memory_usage REAL,
    gpu_usage REAL,
    disk_usage REAL,

    embedding_service_status TEXT,
    vector_db_status TEXT,
    llm_api_status TEXT,

    pending_requests INTEGER,
    active_sessions INTEGER,

    error_count_1h INTEGER,
    error_count_24h INTEGER,

    metadata TEXT
);

-- 质量评估表
CREATE TABLE IF NOT EXISTS quality_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    query_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,

    assessment_type TEXT NOT NULL,

    faithfulness_score REAL,
    answer_relevance_score REAL,
    context_precision REAL,
    context_recall REAL,

    hallucination_type TEXT,
    hallucinated_claims TEXT,

    citation_precision REAL,
    citation_recall REAL,
    missing_citations TEXT,

    completeness_score REAL,
    missing_aspects TEXT,

    reviewer_id TEXT,
    review_notes TEXT,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- 数据保留策略表
CREATE TABLE IF NOT EXISTS data_retention_policy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    retention_days INTEGER NOT NULL,
    archive_location TEXT,
    archive_format TEXT,
    archive_condition TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    UNIQUE(table_name)
);

-- 小时聚合表
CREATE TABLE IF NOT EXISTS metrics_hourly (
    hour_timestamp TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    avg_value REAL,
    min_value REAL,
    max_value REAL,
    sum_value REAL,
    count_value INTEGER,
    PRIMARY KEY (hour_timestamp, metric_name)
);

-- 日聚合表
CREATE TABLE IF NOT EXISTS metrics_daily (
    day_date TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    avg_value REAL,
    min_value REAL,
    max_value REAL,
    sum_value REAL,
    count_value INTEGER,
    PRIMARY KEY (day_date, metric_name)
);

-- ===== 修改现有表 =====

-- audit_logs 添加query_id
ALTER TABLE audit_logs ADD COLUMN query_id TEXT;

-- sessions 添加字段
ALTER TABLE sessions ADD COLUMN session_type TEXT DEFAULT 'qa';
ALTER TABLE sessions ADD COLUMN client_ip TEXT;
ALTER TABLE sessions ADD COLUMN user_agent TEXT;

-- ===== 新增索引 =====

CREATE INDEX IF NOT EXISTS idx_audit_query ON audit_logs(query_id);
CREATE INDEX IF NOT EXISTS idx_audit_session_time ON audit_logs(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_type_time ON audit_logs(event_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_coverage ON metrics(metric_name, timestamp, metric_value, category);
CREATE INDEX IF NOT EXISTS idx_api_calls_session ON api_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_api_calls_timestamp ON api_calls(request_timestamp);
CREATE INDEX IF NOT EXISTS idx_api_calls_status ON api_calls(status);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON user_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON user_feedback(timestamp);
CREATE INDEX IF NOT EXISTS idx_health_time ON system_health(snapshot_time);
CREATE INDEX IF NOT EXISTS idx_quality_session ON quality_assessments(session_id);
CREATE INDEX IF NOT EXISTS idx_quality_type ON quality_assessments(assessment_type);

-- ===== 初始化数据保留策略 =====
INSERT OR REPLACE INTO data_retention_policy
(table_name, retention_days, archive_location, archive_format, archive_condition, created_at)
VALUES
('audit_logs', 90, '/archive/audit_logs/', 'parquet', "event_type != 'error'", datetime('now')),
('metrics', 30, '/archive/metrics/', 'parquet', '1=1', datetime('now')),
('sessions', 365, '/archive/sessions/', 'parquet', '1=1', datetime('now')),
('retrieval_records', 90, '/archive/retrieval/', 'parquet', '1=1', datetime('now')),
('api_calls', 90, '/archive/api_calls/', 'parquet', '1=1', datetime('now')),
('injection_attacks', 365, '/archive/injection/', 'parquet', '1=1', datetime('now'));
```

---

**报告完成**

本报告基于对以下文件的审核:
- `/home/nvidia/workspace/paper/vectordb/database/schema.py`
- `/home/nvidia/workspace/paper/vectordb/database/audit_logger.py`
- `/home/nvidia/workspace/paper/vectordb/core/metrics_collector.py`
- `/home/nvidia/workspace/paper/vectordb/agents/paper_rag_agent.py`
- `/home/nvidia/workspace/paper/vectordb/core/prompt_restructurer.py`
- `/home/nvidia/workspace/paper/vectordb/core/output_formatter.py`
- `/home/nvidia/workspace/paper/vectordb/scripts/config.py`