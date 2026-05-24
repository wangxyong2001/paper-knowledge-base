"""
RAG系统数据库Schema
审计日志 + 监测指标 + 会话记录
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "/home/nvidia/workspace/paper/vectordb/rag_system.db"

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ===== 审计日志表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        -- event_type: 'input', 'prompt', 'llm_call', 'output', 'error'

        -- 输入记录
        user_query TEXT,
        query_intent TEXT,

        -- Prompt记录
        prompt_template TEXT,
        prompt_version TEXT,
        prompt_variables TEXT,  -- JSON格式
        assembled_prompt TEXT,
        prompt_tokens INTEGER,

        -- LLM调用记录
        llm_provider TEXT,
        llm_model TEXT,
        llm_request_id TEXT,
        llm_input_tokens INTEGER,
        llm_output_tokens INTEGER,
        llm_latency_ms INTEGER,

        -- 输出记录
        raw_output TEXT,
        formatted_output TEXT,
        output_format TEXT,

        -- 检索记录
        retrieved_chunks TEXT,  -- JSON格式chunk_ids
        retrieval_scores TEXT,  -- JSON格式

        -- 安全检查
        injection_detected BOOLEAN,
        injection_type TEXT,
        injection_blocked BOOLEAN,

        -- 质量评估
        hallucination_risk REAL,
        citation_accuracy REAL,
        support_score REAL,

        -- 元数据
        metadata TEXT  -- JSON格式扩展字段
    )
    """)

    # ===== 监测指标表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL NOT NULL,
        metric_unit TEXT,
        session_id TEXT,

        -- 分类维度
        category TEXT,  -- 'runtime', 'quality', 'agent_behavior', 'cost', 'security'
        subcategory TEXT,

        -- 聚合信息
        aggregation_period TEXT,  -- 'hourly', 'daily', 'weekly'

        metadata TEXT  -- JSON格式扩展
    )
    """)

    # ===== 会话表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        ended_at TEXT,
        user_id TEXT,

        -- 会话统计
        total_queries INTEGER DEFAULT 0,
        total_tokens_input INTEGER DEFAULT 0,
        total_tokens_output INTEGER DEFAULT 0,
        total_latency_ms INTEGER DEFAULT 0,

        -- 质量统计
        avg_hallucination_risk REAL,
        avg_citation_accuracy REAL,
        avg_support_score REAL,

        -- 状态
        status TEXT DEFAULT 'active'
    )
    """)

    # ===== 检索记录表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS retrieval_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        query_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,

        -- 检索输入
        query_text TEXT NOT NULL,
        query_intent TEXT,

        -- 检索配置
        vector_top_k INTEGER,
        bm25_top_k INTEGER,
        final_top_k INTEGER,

        -- 检索结果
        retrieved_chunk_ids TEXT,  -- JSON数组
        retrieved_scores TEXT,  -- JSON数组
        retrieved_categories TEXT,  -- JSON数组

        -- 检索质量
        precision_at_5 REAL,
        recall_at_10 REAL,
        mrr REAL,

        -- 检索时间
        retrieval_latency_ms INTEGER
    )
    """)

    # ===== Prompt模板版本表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prompt_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT NOT NULL,
        version TEXT NOT NULL,
        created_at TEXT NOT NULL,

        -- 模板内容
        template_content TEXT NOT NULL,
        variables TEXT,  -- JSON格式变量定义

        -- 效果统计
        avg_hallucination_rate REAL,
        avg_citation_accuracy REAL,
        avg_user_satisfaction REAL,
        usage_count INTEGER DEFAULT 0,

        -- 状态
        is_active BOOLEAN DEFAULT TRUE,
        deprecated_at TEXT
    )
    """)

    # ===== 注入攻击记录表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS injection_attacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        session_id TEXT,

        -- 攻击检测
        input_text TEXT NOT NULL,
        attack_type TEXT NOT NULL,
        -- attack_type: 'role_hijack', 'output_manipulation', 'data_exfiltration', 'context_injection'

        threat_level TEXT NOT NULL,
        -- threat_level: 'safe', 'low', 'medium', 'high', 'critical'

        -- 处理结果
        blocked BOOLEAN NOT NULL,
        sanitized_input TEXT,

        -- 来源信息
        source_ip TEXT,
        user_agent TEXT,

        metadata TEXT
    )
    """)

    # ===== 幻觉检测记录表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hallucination_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        session_id TEXT,
        query_id TEXT,

        -- 检测结果
        output_text TEXT NOT NULL,
        claim TEXT,  -- 具体幻觉声明
        hallucination_type TEXT,
        -- hallucination_type: 'fabrication', 'contradiction', 'unsupported', 'citation_error'

        risk_score REAL NOT NULL,

        -- 验证信息
        expected_sources TEXT,  -- JSON格式
        matched_sources TEXT,  -- JSON格式
        validation_result TEXT,

        -- 处理
        corrected BOOLEAN,
        correction_text TEXT
    )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_retrieval_session ON retrieval_records(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_injection_timestamp ON injection_attacks(timestamp)")

    conn.commit()
    conn.close()

    print(f"✓ 数据库初始化完成: {DB_PATH}")

def get_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)

if __name__ == "__main__":
    init_database()