"""
DashScope/GLM-5 API Client
云端LLM调用封装，集成审计日志和指标采集
"""

import aiohttp
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional
import uuid
from dataclasses import dataclass

# 定价 (USD per 1K tokens)
PRICING = {
    "glm-5": {"input": 0.001, "output": 0.002},
    "glm-4-plus": {"input": 0.002, "output": 0.004},
    "qwen-turbo": {"input": 0.0005, "output": 0.001},
}


class APIError(Exception):
    """API错误"""
    pass


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
    }

    RETRYABLE_ERRORS = [
        "rate_limit_exceeded",
        "timeout",
        "service_unavailable",
        "internal_error",
    ]

    def __init__(self, strategy: str = "exponential_backoff"):
        self.config = self.STRATEGIES.get(strategy, self.STRATEGIES["exponential_backoff"])

    def should_retry(self, error_type: str, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.config["max_retries"]:
            return False
        return error_type in self.RETRYABLE_ERRORS

    def get_delay(self, attempt: int) -> float:
        """获取重试延迟"""
        delay = self.config["base_delay"] * (self.config["multiplier"] ** attempt)
        return min(delay, self.config["max_delay"])


class ResponseTimeMonitor:
    """响应时间监控"""

    def __init__(self):
        self.latency_buffer: List[int] = []
        self.buffer_size = 1000

    def record(self, latency_ms: int) -> Dict:
        """记录延迟并返回统计"""
        self.latency_buffer.append(latency_ms)

        if len(self.latency_buffer) > self.buffer_size:
            self.latency_buffer.pop(0)

        if len(self.latency_buffer) < 10:
            return {"avg_response_time_ms": latency_ms}

        sorted_latencies = sorted(self.latency_buffer)
        n = len(sorted_latencies)

        return {
            "avg_response_time_ms": sum(sorted_latencies) / n,
            "p50_response_time_ms": sorted_latencies[int(n * 0.5)],
            "p90_response_time_ms": sorted_latencies[int(n * 0.9)],
            "p95_response_time_ms": sorted_latencies[int(n * 0.95)],
            "p99_response_time_ms": sorted_latencies[int(n * 0.99)],
        }

    def check_sla(self, threshold_ms: int = 3000) -> Dict:
        """检查SLA"""
        if not self.latency_buffer:
            return {"compliant": True, "message": "No data"}

        sorted_latencies = sorted(self.latency_buffer)
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        compliant = p95 <= threshold_ms

        return {
            "compliant": compliant,
            "p95_ms": p95,
            "threshold_ms": threshold_ms,
            "message": "SLA compliant" if compliant else f"P95 ({p95}ms) exceeds threshold ({threshold_ms}ms)"
        }


@dataclass
class APICallResult:
    """API调用结果"""
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    latency_ms: int
    call_id: str
    status: str


class DashScopeClient:
    """DashScope/GLM-5 API 客户端"""

    ENDPOINTS = {
        "chat": "/v1/chat/completions",
        "embeddings": "/v1/embeddings",
    }

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        audit_logger=None,
        metrics_collector=None
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.audit_logger = audit_logger
        self.metrics_collector = metrics_collector
        self.retry_policy = RetryPolicy()
        self.response_monitor = ResponseTimeMonitor()

    async def chat(
        self,
        messages: List[Dict],
        model: str = "glm-5",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        session_id: str = None,
        query_id: str = None,
        **kwargs
    ) -> APICallResult:
        """聊天接口"""

        call_id = f"call_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()

        # 估算输入Token
        input_text = " ".join([m.get("content", "") for m in messages])
        input_tokens = self._estimate_tokens(input_text)

        # 记录请求开始
        self._log_api_call_start(call_id, session_id, query_id, model, input_tokens)

        retries = 0
        last_error = None

        for attempt in range(self.retry_policy.config["max_retries"] + 1):
            try:
                response = await self._make_request(
                    endpoint=self.ENDPOINTS["chat"],
                    payload={
                        "model": model,
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
                usage = response.get("usage", {})
                output_tokens = usage.get("completion_tokens", self._estimate_tokens(output_text))
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

                # 计算成本
                cost = self._calculate_cost(model, input_tokens, output_tokens)

                # 记录成功
                self._log_api_call_success(
                    call_id=call_id,
                    session_id=session_id,
                    query_id=query_id,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost=cost,
                    retries=retries,
                    raw_output=output_text
                )

                # 采集指标
                latency_metrics = self.response_monitor.record(latency_ms)
                self._collect_metrics(latency_metrics, input_tokens, output_tokens, cost, session_id)

                return APICallResult(
                    content=output_text,
                    prompt_tokens=input_tokens,
                    completion_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    call_id=call_id,
                    status="success"
                )

            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)

                if self.retry_policy.should_retry(error_type, attempt):
                    retries += 1
                    delay = self.retry_policy.get_delay(attempt)
                    self._log_retry(call_id, session_id, query_id, retries, error_type)
                    await asyncio.sleep(delay)
                else:
                    break

        # 记录失败
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        self._log_api_call_failure(
            call_id=call_id,
            session_id=session_id,
            query_id=query_id,
            model=model,
            error=str(last_error),
            retries=retries,
            latency_ms=latency_ms
        )

        raise APIError(f"API调用失败: {last_error}")

    async def _make_request(
        self,
        endpoint: str,
        payload: Dict,
        call_id: str
    ) -> Dict:
        """发送请求"""

        if self.session is None:
            self.session = aiohttp.ClientSession()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Request-ID": call_id,
        }

        async with self.session.post(
            f"{self.base_url}{endpoint}",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 429:  # Rate limit
                raise APIError("rate_limit_exceeded")
            elif response.status >= 500:
                error_body = await response.text()
                raise APIError(f"internal_error: {error_body}")
            else:
                error_body = await response.text()
                raise APIError(f"API error {response.status}: {error_body}")

    def _estimate_tokens(self, text: str) -> int:
        """估算Token数"""
        # 中文约1.5字符/token，英文约4字符/token
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算成本"""
        pricing = PRICING.get(model, {"input": 0.001, "output": 0.002})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_str = str(error).lower()
        if "rate limit" in error_str or "429" in error_str:
            return "rate_limit_exceeded"
        if "timeout" in error_str:
            return "timeout"
        if "500" in error_str or "internal" in error_str:
            return "internal_error"
        if "503" in error_str:
            return "service_unavailable"
        return "unknown"

    def _log_api_call_start(self, call_id: str, session_id: str, query_id: str, model: str, input_tokens: int):
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

    def _log_api_call_success(
        self,
        call_id: str,
        session_id: str,
        query_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost: float,
        retries: int,
        raw_output: str
    ):
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
                    status = 'success',
                    retry_count = ?
                WHERE call_id = ?
            """, (datetime.now().isoformat(), latency_ms, output_tokens,
                  input_tokens + output_tokens, cost, retries, call_id))
            self.audit_logger.conn.commit()

            # 同时记录到audit_logs
            self.audit_logger.log_llm_call(
                provider="dashscope",
                model=model,
                request_id=call_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                raw_output=raw_output[:500]  # 截断避免过长
            )

    def _log_api_call_failure(
        self,
        call_id: str,
        session_id: str,
        query_id: str,
        model: str,
        error: str,
        retries: int,
        latency_ms: int
    ):
        """记录API调用失败"""
        if self.audit_logger:
            cursor = self.audit_logger.conn.cursor()
            cursor.execute("""
                UPDATE api_calls SET
                    response_timestamp = ?,
                    latency_ms = ?,
                    status = 'failed',
                    error_message = ?,
                    retry_count = ?
                WHERE call_id = ?
            """, (datetime.now().isoformat(), latency_ms, error, retries, call_id))
            self.audit_logger.conn.commit()

    def _log_retry(self, call_id: str, session_id: str, query_id: str, retry_count: int, retry_reason: str):
        """记录重试"""
        if self.audit_logger:
            cursor = self.audit_logger.conn.cursor()
            cursor.execute("""
                UPDATE api_calls SET
                    retry_count = ?,
                    retry_reason = ?
                WHERE call_id = ?
            """, (retry_count, retry_reason, call_id))
            self.audit_logger.conn.commit()

    def _collect_metrics(self, latency_metrics: Dict, input_tokens: int, output_tokens: int, cost: float, session_id: str):
        """采集指标"""
        if self.metrics_collector:
            metrics = {
                **latency_metrics,
                "total_tokens_input": input_tokens,
                "total_tokens_output": output_tokens,
                "cost_per_task": cost,
            }
            self.metrics_collector.collect_batch(metrics, session_id)

    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None


# 同步版本（用于非异步环境）
class DashScopeClientSync:
    """DashScope/GLM-5 API 同步客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        audit_logger=None,
        metrics_collector=None
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.audit_logger = audit_logger
        self.metrics_collector = metrics_collector
        self.response_monitor = ResponseTimeMonitor()

    def chat(
        self,
        messages: List[Dict],
        model: str = "glm-5",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        session_id: str = None,
        query_id: str = None,
        **kwargs
    ) -> APICallResult:
        """同步聊天接口"""
        import requests

        call_id = f"call_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()

        input_text = " ".join([m.get("content", "") for m in messages])
        input_tokens = self._estimate_tokens(input_text)

        self._log_api_call_start(call_id, session_id, query_id, model, input_tokens)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )

            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if response.status_code == 200:
                data = response.json()
                output_text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                output_tokens = usage.get("completion_tokens", self._estimate_tokens(output_text))
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
                cost = self._calculate_cost(model, input_tokens, output_tokens)

                self._log_api_call_success(
                    call_id, session_id, query_id, model,
                    input_tokens, output_tokens, latency_ms, cost, 0, output_text
                )

                latency_metrics = self.response_monitor.record(latency_ms)
                self._collect_metrics(latency_metrics, input_tokens, output_tokens, cost, session_id)

                return APICallResult(
                    content=output_text,
                    prompt_tokens=input_tokens,
                    completion_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    call_id=call_id,
                    status="success"
                )
            else:
                error_msg = response.text
                self._log_api_call_failure(call_id, session_id, query_id, model, error_msg, 0, latency_ms)
                raise APIError(f"API error {response.status_code}: {error_msg}")

        except requests.exceptions.Timeout:
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call_failure(call_id, session_id, query_id, model, "timeout", 0, latency_ms)
            raise APIError("Request timeout")
        except Exception as e:
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call_failure(call_id, session_id, query_id, model, str(e), 0, latency_ms)
            raise APIError(f"Request failed: {e}")

    def _estimate_tokens(self, text: str) -> int:
        """估算Token数"""
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算成本"""
        pricing = PRICING.get(model, {"input": 0.001, "output": 0.002})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

    def _log_api_call_start(self, call_id: str, session_id: str, query_id: str, model: str, input_tokens: int):
        if self.audit_logger:
            cursor = self.audit_logger.conn.cursor()
            cursor.execute("""
                INSERT INTO api_calls
                (call_id, session_id, query_id, provider, model, request_timestamp, status, prompt_tokens)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (call_id, session_id, query_id, "dashscope", model, datetime.now().isoformat(), input_tokens))
            self.audit_logger.conn.commit()

    def _log_api_call_success(self, call_id, session_id, query_id, model, input_tokens, output_tokens, latency_ms, cost, retries, raw_output):
        if self.audit_logger:
            cursor = self.audit_logger.conn.cursor()
            cursor.execute("""
                UPDATE api_calls SET
                    response_timestamp=?, latency_ms=?, completion_tokens=?, total_tokens=?, estimated_cost=?, status='success', retry_count=?
                WHERE call_id=?
            """, (datetime.now().isoformat(), latency_ms, output_tokens, input_tokens + output_tokens, cost, retries, call_id))
            self.audit_logger.conn.commit()

    def _log_api_call_failure(self, call_id, session_id, query_id, model, error, retries, latency_ms):
        if self.audit_logger:
            cursor = self.audit_logger.conn.cursor()
            cursor.execute("""
                UPDATE api_calls SET response_timestamp=?, latency_ms=?, status='failed', error_message=?, retry_count=?
                WHERE call_id=?
            """, (datetime.now().isoformat(), latency_ms, error, retries, call_id))
            self.audit_logger.conn.commit()

    def _collect_metrics(self, latency_metrics, input_tokens, output_tokens, cost, session_id):
        if self.metrics_collector:
            metrics = {**latency_metrics, "total_tokens_input": input_tokens, "total_tokens_output": output_tokens, "cost_per_task": cost}
            self.metrics_collector.collect_batch(metrics, session_id)


# 测试
if __name__ == "__main__":
    import os

    # 从环境变量获取API密钥
    api_key = os.environ.get("DASHSCOPE_API_KEY", "test_key")

    client = DashScopeClientSync(api_key=api_key)

    # 模拟测试（无真实API）
    test_messages = [{"role": "user", "content": "你好，请介绍一下Transformer的核心创新"}]

    print("API Client 模块加载成功")
    print(f"  - Token估算: {client._estimate_tokens(test_messages[0]['content'])} tokens")
    print(f"  - 成本计算 (glm-5, 100 input + 50 output): ${client._calculate_cost('glm-5', 100, 50):.4f}")

    print("\n✓ DashScope API Client 测试完成")