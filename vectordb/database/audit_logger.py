"""
审计日志系统
记录所有输入/输出到SQLite，实现透明追溯
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import os

DB_PATH = "/home/nvidia/workspace/paper/vectordb/rag_system.db"

class AuditLogger:
    """审计日志记录器"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._generate_session_id()
        self.conn = sqlite3.connect(DB_PATH)
        self._init_session()

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _init_session(self):
        """初始化会话记录"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO sessions (session_id, created_at, status)
            VALUES (?, ?, 'active')
        """, (self.session_id, datetime.now().isoformat()))
        self.conn.commit()

    def log_input(self, user_query: str, query_intent: str = None, metadata: Dict = None):
        """记录用户输入"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type, user_query, query_intent, metadata)
            VALUES (?, ?, 'input', ?, ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            user_query,
            query_intent,
            json.dumps(metadata or {})
        ))
        self.conn.commit()

        # 更新会话统计
        self._update_session_stats({'total_queries': 1})

    def log_prompt(self,
                   template_name: str,
                   template_version: str,
                   assembled_prompt: str,
                   variables: Dict = None,
                   prompt_tokens: int = 0):
        """记录重构后的Prompt"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type, prompt_template, prompt_version,
             prompt_variables, assembled_prompt, prompt_tokens)
            VALUES (?, ?, 'prompt', ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            template_name,
            template_version,
            json.dumps(variables or {}),
            assembled_prompt,
            prompt_tokens
        ))
        self.conn.commit()

    def log_llm_call(self,
                     provider: str,
                     model: str,
                     request_id: str,
                     input_tokens: int,
                     output_tokens: int,
                     latency_ms: int,
                     raw_output: str):
        """记录LLM调用"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type, llm_provider, llm_model,
             llm_request_id, llm_input_tokens, llm_output_tokens,
             llm_latency_ms, raw_output)
            VALUES (?, ?, 'llm_call', ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            provider,
            model,
            request_id,
            input_tokens,
            output_tokens,
            latency_ms,
            raw_output
        ))
        self.conn.commit()

        # 更新会话统计
        self._update_session_stats({
            'total_tokens_input': input_tokens,
            'total_tokens_output': output_tokens,
            'total_latency_ms': latency_ms
        })

    def log_output(self,
                   formatted_output: str,
                   output_format: str = 'markdown',
                   citations: List[Dict] = None):
        """记录格式化输出"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type, formatted_output, output_format, metadata)
            VALUES (?, ?, 'output', ?, ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            formatted_output,
            output_format,
            json.dumps({'citations': citations or []})
        ))
        self.conn.commit()

    def log_retrieval(self,
                      query_text: str,
                      chunk_ids: List[str],
                      scores: List[float],
                      precision_at_5: float = None,
                      latency_ms: int = 0):
        """记录检索过程"""
        cursor = self.conn.cursor()
        query_id = f"query_{uuid.uuid4().hex[:8]}"

        cursor.execute("""
            INSERT INTO retrieval_records
            (session_id, query_id, timestamp, query_text,
             retrieved_chunk_ids, retrieved_scores,
             precision_at_5, retrieval_latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            query_id,
            datetime.now().isoformat(),
            query_text,
            json.dumps(chunk_ids),
            json.dumps(scores),
            precision_at_5,
            latency_ms
        ))

        # 同时记录到audit_logs
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type, user_query,
             retrieved_chunks, retrieval_scores, metadata)
            VALUES (?, ?, 'retrieval', ?, ?, ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            query_text,
            json.dumps(chunk_ids),
            json.dumps(scores),
            json.dumps({'query_id': query_id, 'latency_ms': latency_ms})
        ))

        self.conn.commit()

    def log_injection_detection(self,
                                 input_text: str,
                                 attack_type: str,
                                 threat_level: str,
                                 blocked: bool,
                                 sanitized_input: str = None):
        """记录注入攻击检测"""
        cursor = self.conn.cursor()

        # 记录到注入攻击表
        cursor.execute("""
            INSERT INTO injection_attacks
            (timestamp, session_id, input_text, attack_type,
             threat_level, blocked, sanitized_input)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            self.session_id,
            input_text,
            attack_type,
            threat_level,
            blocked,
            sanitized_input
        ))

        # 同时记录到audit_logs
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type, injection_detected,
             injection_type, injection_blocked, metadata)
            VALUES (?, ?, 'security', TRUE, ?, ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            attack_type,
            blocked,
            json.dumps({'threat_level': threat_level, 'sanitized_input': sanitized_input})
        ))

        self.conn.commit()

    def log_hallucination(self,
                          output_text: str,
                          claim: str,
                          hallucination_type: str,
                          risk_score: float,
                          matched_sources: List[str] = None):
        """记录幻觉检测"""
        cursor = self.conn.cursor()
        query_id = f"query_{uuid.uuid4().hex[:8]}"

        cursor.execute("""
            INSERT INTO hallucination_records
            (timestamp, session_id, query_id, output_text, claim,
             hallucination_type, risk_score, matched_sources)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            self.session_id,
            query_id,
            output_text,
            claim,
            hallucination_type,
            risk_score,
            json.dumps(matched_sources or [])
        ))

        # 更新audit_logs
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type, hallucination_risk, metadata)
            VALUES (?, ?, 'quality', ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            risk_score,
            json.dumps({'claim': claim, 'type': hallucination_type})
        ))

        self.conn.commit()

    def log_quality_metrics(self,
                            hallucination_risk: float,
                            citation_accuracy: float,
                            support_score: float):
        """记录质量评估指标"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type,
             hallucination_risk, citation_accuracy, support_score)
            VALUES (?, ?, 'quality', ?, ?, ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            hallucination_risk,
            citation_accuracy,
            support_score
        ))
        self.conn.commit()

        # 更新会话质量统计
        self._update_session_quality(hallucination_risk, citation_accuracy, support_score)

    def log_error(self, error_type: str, error_message: str, stack_trace: str = None):
        """记录错误"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs
            (session_id, timestamp, event_type, metadata)
            VALUES (?, ?, 'error', ?)
        """, (
            self.session_id,
            datetime.now().isoformat(),
            json.dumps({
                'error_type': error_type,
                'error_message': error_message,
                'stack_trace': stack_trace
            })
        ))
        self.conn.commit()

    def _update_session_stats(self, stats: Dict):
        """更新会话统计"""
        cursor = self.conn.cursor()
        for key, value in stats.items():
            cursor.execute(f"""
                UPDATE sessions
                SET {key} = {key} + ?
                WHERE session_id = ?
            """, (value, self.session_id))
        self.conn.commit()

    def _update_session_quality(self, hallucination_risk: float,
                                  citation_accuracy: float,
                                  support_score: float):
        """更新会话质量统计"""
        cursor = self.conn.cursor()
        # 计算平均值需要先查询当前值
        cursor.execute("""
            SELECT total_queries, avg_hallucination_risk, avg_citation_accuracy, avg_support_score
            FROM sessions WHERE session_id = ?
        """, (self.session_id,))
        row = cursor.fetchone()

        if row and row[0] > 0:
            n = row[0]
            new_avg_halu = (row[1] * (n-1) + hallucination_risk) / n if row[1] else hallucination_risk
            new_avg_cite = (row[2] * (n-1) + citation_accuracy) / n if row[2] else citation_accuracy
            new_avg_supp = (row[3] * (n-1) + support_score) / n if row[3] else support_score

            cursor.execute("""
                UPDATE sessions
                SET avg_hallucination_risk = ?,
                    avg_citation_accuracy = ?,
                    avg_support_score = ?
                WHERE session_id = ?
            """, (new_avg_halu, new_avg_cite, new_avg_supp, self.session_id))
            self.conn.commit()

    def end_session(self):
        """结束会话"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET ended_at = ?, status = 'completed'
            WHERE session_id = ?
        """, (datetime.now().isoformat(), self.session_id))
        self.conn.commit()

    def get_session_audit_log(self) -> List[Dict]:
        """获取当前会话完整审计日志"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM audit_logs
            WHERE session_id = ?
            ORDER BY timestamp
        """, (self.session_id,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    def close(self):
        """关闭连接"""
        self.conn.close()


# 测试
if __name__ == "__main__":
    # 初始化数据库
    from schema import init_database
    init_database()

    # 测试审计日志
    logger = AuditLogger()

    # 测试各类型日志
    logger.log_input("Transformer的核心创新是什么?", "qa")
    logger.log_prompt("rag_query", "2025.12.01", "重构后的prompt内容...", {'query': 'Transformer'}, 500)
    logger.log_llm_call("dashscope", "glm-5", "req_123", 500, 200, 1500, "LLM原始输出...")
    logger.log_output("格式化后的回答内容...", 'markdown', [{'chunk_id': 'xxx', 'text': '原文'}])
    logger.log_retrieval("Transformer", ['chunk_1', 'chunk_2'], [0.9, 0.85], 0.8, 50)
    logger.log_injection_detection("恶意输入", "role_hijack", "high", True, "清洗后的输入")
    logger.log_hallucination("输出内容", "幻觉声明", "fabrication", 0.8, ['chunk_1'])
    logger.log_quality_metrics(0.03, 0.96, 0.85)

    # 获取审计日志
    audit_log = logger.get_session_audit_log()
    print(f"审计日志记录数: {len(audit_log)}")

    logger.end_session()
    logger.close()
    print("✓ 审计日志测试完成")