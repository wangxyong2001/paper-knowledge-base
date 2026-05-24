"""
监测指标自动采集与SQLite存储
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

DB_PATH = "/home/nvidia/workspace/paper/vectordb/rag_system.db"

class MetricsCollector:
    """监测指标采集器"""

    # 指标定义
    METRICS_DEFINITION = {
        # L1: 基础运行指标
        "request_count": {"category": "runtime", "unit": "count"},
        "success_rate": {"category": "runtime", "unit": "percent"},
        "error_rate": {"category": "runtime", "unit": "percent"},
        "avg_response_time_ms": {"category": "runtime", "unit": "ms"},
        "p95_response_time_ms": {"category": "runtime", "unit": "ms"},
        "total_tokens_input": {"category": "runtime", "unit": "tokens"},
        "total_tokens_output": {"category": "runtime", "unit": "tokens"},
        "concurrent_requests": {"category": "runtime", "unit": "count"},

        # L2: 质量指标
        "retrieval_hit_rate": {"category": "quality", "unit": "percent"},
        "retrieval_precision_5": {"category": "quality", "unit": "percent"},
        "retrieval_recall_10": {"category": "quality", "unit": "percent"},
        "mrr": {"category": "quality", "unit": "score"},
        "hallucination_rate": {"category": "quality", "unit": "percent"},
        "citation_accuracy": {"category": "quality", "unit": "percent"},
        "answer_satisfaction": {"category": "quality", "unit": "score"},
        "code_success_rate": {"category": "quality", "unit": "percent"},
        "test_pass_rate": {"category": "quality", "unit": "percent"},

        # L3: Agent行为指标
        "tool_call_count": {"category": "agent_behavior", "unit": "count"},
        "tool_success_rate": {"category": "agent_behavior", "unit": "percent"},
        "reflection_count": {"category": "agent_behavior", "unit": "count"},
        "retry_count": {"category": "agent_behavior", "unit": "count"},
        "state_transitions": {"category": "agent_behavior", "unit": "count"},
        "avg_loop_depth": {"category": "agent_behavior", "unit": "count"},

        # L4: 用户体验指标
        "user_satisfaction_avg": {"category": "user_experience", "unit": "score"},
        "task_completion_rate": {"category": "user_experience", "unit": "percent"},
        "first_try_success_rate": {"category": "user_experience", "unit": "percent"},
        "avg_interaction_rounds": {"category": "user_experience", "unit": "count"},

        # L5: 成本效率指标
        "token_efficiency": {"category": "cost", "unit": "ratio"},
        "time_efficiency": {"category": "cost", "unit": "ratio"},
        "cost_per_task": {"category": "cost", "unit": "currency"},
        "retrieval_efficiency": {"category": "cost", "unit": "percent"},

        # L6: 安全合规指标
        "injection_attack_count": {"category": "security", "unit": "count"},
        "security_alert_count": {"category": "security", "unit": "count"},
        "data_leak_risk": {"category": "security", "unit": "percent"},
        "compliance_pass_rate": {"category": "security", "unit": "percent"},
        "audit_coverage_rate": {"category": "security", "unit": "percent"},
    }

    # 告警阈值
    ALERT_THRESHOLDS = {
        "error_rate": {"threshold": 0.05, "level": "warning"},
        "avg_response_time_ms": {"threshold": 3000, "level": "warning"},
        "hallucination_rate": {"threshold": 0.05, "level": "critical"},
        "citation_accuracy": {"threshold": 0.90, "direction": "below", "level": "warning"},
        "retrieval_precision_5": {"threshold": 0.80, "direction": "below", "level": "warning"},
        "injection_attack_count": {"threshold": 1, "level": "critical"},
    }

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.current_metrics = defaultdict(float)
        self.session_metrics = defaultdict(list)

    def collect(self, metric_name: str, value: float, session_id: str = None):
        """采集单个指标"""
        if metric_name not in self.METRICS_DEFINITION:
            return

        # 存入内存
        self.current_metrics[metric_name] = value
        if session_id:
            self.session_metrics[session_id].append((metric_name, value))

        # 存入SQLite
        self._store_metric(metric_name, value, session_id)

    def collect_batch(self, metrics: Dict[str, float], session_id: str = None):
        """批量采集指标"""
        for name, value in metrics.items():
            self.collect(name, value, session_id)

    def _store_metric(self, metric_name: str, value: float, session_id: str = None):
        """存储到SQLite"""
        definition = self.METRICS_DEFINITION.get(metric_name, {})

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO metrics
            (timestamp, metric_name, metric_value, metric_unit,
             session_id, category, subcategory)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            metric_name,
            value,
            definition.get("unit", ""),
            session_id,
            definition.get("category", ""),
            ""
        ))
        self.conn.commit()

    def check_alerts(self) -> List[Dict]:
        """检查告警"""
        alerts = []

        for metric_name, config in self.ALERT_THRESHOLDS.items():
            value = self.current_metrics.get(metric_name, 0)
            threshold = config["threshold"]
            direction = config.get("direction", "above")

            triggered = False
            if direction == "above" and value > threshold:
                triggered = True
            elif direction == "below" and value < threshold:
                triggered = True

            if triggered:
                alerts.append({
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "level": config["level"],
                    "timestamp": datetime.now().isoformat()
                })

        return alerts

    def aggregate_hourly(self) -> Dict:
        """小时聚合"""
        hour_start = datetime.now() - timedelta(hours=1)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT metric_name, AVG(metric_value), COUNT(*), MIN(metric_value), MAX(metric_value)
            FROM metrics
            WHERE timestamp >= ?
            GROUP BY metric_name
        """, (hour_start.isoformat(),))

        results = {}
        for row in cursor.fetchall():
            metric_name = row[0]
            results[metric_name] = {
                "avg": row[1],
                "count": row[2],
                "min": row[3],
                "max": row[4]
            }

        return results

    def aggregate_daily(self) -> Dict:
        """日聚合"""
        day_start = datetime.now() - timedelta(days=1)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT metric_name, AVG(metric_value), COUNT(*), SUM(metric_value)
            FROM metrics
            WHERE timestamp >= ?
            GROUP BY metric_name
        """, (day_start.isoformat(),))

        results = {}
        for row in cursor.fetchall():
            metric_name = row[0]
            results[metric_name] = {
                "avg": row[1],
                "count": row[2],
                "total": row[3]
            }

        return results

    def get_metrics_history(self,
                            metric_name: str,
                            hours: int = 24) -> List[Dict]:
        """获取指标历史"""
        start_time = datetime.now() - timedelta(hours=hours)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT timestamp, metric_value, session_id
            FROM metrics
            WHERE metric_name = ? AND timestamp >= ?
            ORDER BY timestamp
        """, (metric_name, start_time.isoformat()))

        history = []
        for row in cursor.fetchall():
            history.append({
                "timestamp": row[0],
                "value": row[1],
                "session_id": row[2]
            })

        return history

    def get_dashboard_data(self) -> Dict:
        """获取Dashboard数据"""
        # L1运行指标
        cursor = self.conn.cursor()

        # 最近请求统计
        cursor.execute("""
            SELECT COUNT(*) FROM audit_logs
            WHERE timestamp >= datetime('now', '-1 hour')
        """)
        request_count = cursor.fetchone()[0]

        # 成功率
        cursor.execute("""
            SELECT
                SUM(CASE WHEN event_type != 'error' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
            FROM audit_logs
            WHERE timestamp >= datetime('now', '-1 hour')
        """)
        success_rate = cursor.fetchone()[0] or 0

        # 平均响应时间
        cursor.execute("""
            SELECT AVG(llm_latency_ms) FROM audit_logs
            WHERE llm_latency_ms IS NOT NULL
            AND timestamp >= datetime('now', '-1 hour')
        """)
        avg_response_time = cursor.fetchone()[0] or 0

        # Token消耗
        cursor.execute("""
            SELECT SUM(llm_input_tokens), SUM(llm_output_tokens)
            FROM audit_logs
            WHERE timestamp >= datetime('now', '-1 hour')
        """)
        tokens_row = cursor.fetchone()
        tokens_input = tokens_row[0] or 0
        tokens_output = tokens_row[1] or 0

        # 注入攻击
        cursor.execute("""
            SELECT COUNT(*) FROM injection_attacks
            WHERE timestamp >= datetime('now', '-1 hour')
        """)
        injection_count = cursor.fetchone()[0]

        # 幻觉风险
        cursor.execute("""
            SELECT AVG(hallucination_risk) FROM audit_logs
            WHERE hallucination_risk IS NOT NULL
            AND timestamp >= datetime('now', '-1 hour')
        """)
        hallucination_risk = cursor.fetchone()[0] or 0

        return {
            "runtime": {
                "request_count": request_count,
                "success_rate": success_rate,
                "avg_response_time_ms": avg_response_time,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
            },
            "quality": {
                "hallucination_risk": hallucination_risk,
            },
            "security": {
                "injection_attack_count": injection_count,
            },
            "alerts": self.check_alerts(),
            "timestamp": datetime.now().isoformat()
        }

    def close(self):
        """关闭连接"""
        self.conn.close()


# 测试
if __name__ == "__main__":
    collector = MetricsCollector()

    # 测试采集
    collector.collect_batch({
        "request_count": 100,
        "success_rate": 98.5,
        "avg_response_time_ms": 1200,
        "hallucination_rate": 0.03,
        "citation_accuracy": 0.96,
        "injection_attack_count": 0,
    }, "test_session")

    # 检查告警
    alerts = collector.check_alerts()
    print(f"告警数: {len(alerts)}")
    for alert in alerts:
        print(f"  {alert}")

    # Dashboard数据
    dashboard = collector.get_dashboard_data()
    print(f"\nDashboard数据:")
    print(json.dumps(dashboard, indent=2))

    collector.close()
    print("\n✓ 监测指标测试完成")