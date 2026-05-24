"""
Schema Migration Script
从v1迁移到v2，添加api_calls、user_feedback等表
"""

import sqlite3
from datetime import datetime

DB_PATH = "/home/nvidia/workspace/paper/vectordb/rag_system.db"

def migrate_v1_to_v2():
    """执行Schema迁移"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("开始Schema迁移 v1 → v2...")

    # ===== 新增表 =====

    # API调用追踪表
    cursor.execute("""
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
    )
    """)
    print("  ✓ api_calls表创建完成")

    # 用户反馈表
    cursor.execute("""
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
    )
    """)
    print("  ✓ user_feedback表创建完成")

    # 系统健康快照表
    cursor.execute("""
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
    )
    """)
    print("  ✓ system_health表创建完成")

    # 质量评估表
    cursor.execute("""
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
    )
    """)
    print("  ✓ quality_assessments表创建完成")

    # 数据保留策略表
    cursor.execute("""
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
    )
    """)
    print("  ✓ data_retention_policy表创建完成")

    # 小时聚合表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics_hourly (
        hour_timestamp TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        avg_value REAL,
        min_value REAL,
        max_value REAL,
        sum_value REAL,
        count_value INTEGER,
        PRIMARY KEY (hour_timestamp, metric_name)
    )
    """)
    print("  ✓ metrics_hourly表创建完成")

    # 日聚合表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics_daily (
        day_date TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        avg_value REAL,
        min_value REAL,
        max_value REAL,
        sum_value REAL,
        count_value INTEGER,
        PRIMARY KEY (day_date, metric_name)
    )
    """)
    print("  ✓ metrics_daily表创建完成")

    # ===== 修改现有表（添加字段）=====
    # SQLite不支持IF NOT EXISTS for ALTER TABLE，需要检查字段是否存在

    # 检查audit_logs是否有query_id字段
    cursor.execute("PRAGMA table_info(audit_logs)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'query_id' not in columns:
        cursor.execute("ALTER TABLE audit_logs ADD COLUMN query_id TEXT")
        print("  ✓ audit_logs添加query_id字段")

    # 检查sessions是否有新字段
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'session_type' not in columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN session_type TEXT DEFAULT 'qa'")
        print("  ✓ sessions添加session_type字段")

    if 'client_ip' not in columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN client_ip TEXT")
        print("  ✓ sessions添加client_ip字段")

    if 'user_agent' not in columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN user_agent TEXT")
        print("  ✓ sessions添加user_agent字段")

    # ===== 新增索引 =====

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_query ON audit_logs(query_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_session_time ON audit_logs(session_id, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_type_time ON audit_logs(event_type, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_coverage ON metrics(metric_name, timestamp, metric_value, category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_session ON api_calls(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_timestamp ON api_calls(request_timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_status ON api_calls(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_session ON user_feedback(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON user_feedback(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_time ON system_health(snapshot_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_session ON quality_assessments(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_type ON quality_assessments(assessment_type)")
    print("  ✓ 索引创建完成")

    # ===== 初始化数据保留策略 =====
    retention_policies = [
        ('audit_logs', 90, '/archive/audit_logs/', 'parquet'),
        ('metrics', 30, '/archive/metrics/', 'parquet'),
        ('sessions', 365, '/archive/sessions/', 'parquet'),
        ('retrieval_records', 90, '/archive/retrieval/', 'parquet'),
        ('api_calls', 90, '/archive/api_calls/', 'parquet'),
        ('injection_attacks', 365, '/archive/injection/', 'parquet'),
    ]

    for table_name, retention_days, archive_location, archive_format in retention_policies:
        cursor.execute("""
            INSERT OR REPLACE INTO data_retention_policy
            (table_name, retention_days, archive_location, archive_format, archive_condition, created_at)
            VALUES (?, ?, ?, ?, '1=1', ?)
        """, (table_name, retention_days, archive_location, archive_format, datetime.now().isoformat()))

    print("  ✓ 数据保留策略初始化完成")

    conn.commit()
    conn.close()

    print("\n✓ Schema迁移完成 v1 → v2")
    print("新增表: api_calls, user_feedback, system_health, quality_assessments, data_retention_policy, metrics_hourly, metrics_daily")


if __name__ == "__main__":
    migrate_v1_to_v2()