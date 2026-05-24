"""
三层记忆架构 - MemoryManager
- Working Memory: 当前会话上下文（保持10轮对话）
- Episodic Memory: 论文分析快照（SQLite持久化）
- Semantic Memory: 向量知识库集成接口
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque

# 数据库路径
DB_PATH = "/home/nvidia/workspace/paper/vectordb/rag_system.db"
WORKING_MEMORY_SIZE = 10  # 保持最近10轮对话


class PaperMemoryManager:
    """三层记忆管理器"""

    def __init__(self, session_id: str):
        """
        初始化记忆管理器

        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        self.working_memory = deque(maxlen=WORKING_MEMORY_SIZE)  # 工作记忆

        # 初始化情景记忆表
        self._init_episodic_table()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(DB_PATH)

    def _init_episodic_table(self):
        """初始化情景记忆表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,

            -- 论文分析内容
            summary TEXT,
            key_points TEXT,  -- JSON数组
            formulas TEXT,    -- JSON数组
            concepts TEXT,    -- JSON数组

            -- 检索向量（用于相似度检索）
            embedding TEXT,   -- JSON数组

            -- 元数据
            metadata TEXT     -- JSON格式扩展
        )
        """)

        # 创建索引
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_episodic_session
        ON episodic_memory(session_id)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_episodic_paper
        ON episodic_memory(paper_id)
        """)

        conn.commit()
        conn.close()

    # ==================== Working Memory ====================

    def add_working_memory(self, message: Dict[str, Any]) -> None:
        """
        添加当前对话到工作记忆

        Args:
            message: 消息字典，应包含 'role' 和 'content' 字段
        """
        # 添加时间戳
        message_with_time = {
            **message,
            'timestamp': datetime.now().isoformat()
        }
        self.working_memory.append(message_with_time)

    def get_working_memory(self) -> List[Dict[str, Any]]:
        """获取工作记忆所有内容"""
        return list(self.working_memory)

    def clear_working_memory(self) -> None:
        """清空工作记忆"""
        self.working_memory.clear()

    def get_session_context(self) -> Dict[str, Any]:
        """
        获取当前会话上下文

        Returns:
            包含工作记忆和会话信息的字典
        """
        return {
            'session_id': self.session_id,
            'working_memory': list(self.working_memory),
            'message_count': len(self.working_memory)
        }

    # ==================== Episodic Memory ====================

    def add_episodic(self, paper_id: str, analysis: Dict[str, Any]) -> int:
        """
        记录论文分析历史到情景记忆

        Args:
            paper_id: 论文ID
            analysis: 分析结果字典，应包含:
                - summary: 摘要
                - key_points: 核心观点列表
                - formulas: 公式列表
                - concepts: 概念列表
                - embedding: 向量（可选）
                - metadata: 额外元数据（可选）

        Returns:
            记录的ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 序列化JSON字段
        key_points = json.dumps(analysis.get('key_points', []))
        formulas = json.dumps(analysis.get('formulas', []))
        concepts = json.dumps(analysis.get('concepts', []))
        embedding = json.dumps(analysis.get('embedding', []))
        metadata = json.dumps(analysis.get('metadata', {}))

        cursor.execute("""
        INSERT INTO episodic_memory
        (session_id, paper_id, timestamp, summary, key_points, formulas, concepts, embedding, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            paper_id,
            datetime.now().isoformat(),
            analysis.get('summary', ''),
            key_points,
            formulas,
            concepts,
            embedding,
            metadata
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    def get_episodic_by_paper(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        获取指定论文的情景记忆

        Args:
            paper_id: 论文ID

        Returns:
            分析历史列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, session_id, paper_id, timestamp, summary, key_points, formulas, concepts, metadata
        FROM episodic_memory
        WHERE paper_id = ?
        ORDER BY timestamp DESC
        """, (paper_id,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'session_id': row[1],
                'paper_id': row[2],
                'timestamp': row[3],
                'summary': row[4],
                'key_points': json.loads(row[5]) if row[5] else [],
                'formulas': json.loads(row[6]) if row[6] else [],
                'concepts': json.loads(row[7]) if row[7] else [],
                'metadata': json.loads(row[8]) if row[8] else {}
            })

        conn.close()
        return results

    def get_episodic_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取指定会话的情景记忆

        Args:
            session_id: 会话ID

        Returns:
            分析历史列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, session_id, paper_id, timestamp, summary, key_points, formulas, concepts, metadata
        FROM episodic_memory
        WHERE session_id = ?
        ORDER BY timestamp DESC
        """, (session_id,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'session_id': row[1],
                'paper_id': row[2],
                'timestamp': row[3],
                'summary': row[4],
                'key_points': json.loads(row[5]) if row[5] else [],
                'formulas': json.loads(row[6]) if row[6] else [],
                'concepts': json.loads(row[7]) if row[7] else [],
                'metadata': json.loads(row[8]) if row[8] else {}
            })

        conn.close()
        return results

    # ==================== Semantic Memory ====================

    def retrieve_relevant(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        检索相关历史（语义记忆）

        注意: 当前实现基于文本匹配，未来可接入向量检索

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            相关情景记忆列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 简单的关键词匹配检索（未来可替换为向量检索）
        # 匹配summary、key_points、concepts中的内容
        search_pattern = f"%{query}%"

        cursor.execute("""
        SELECT id, session_id, paper_id, timestamp, summary, key_points, formulas, concepts, metadata
        FROM episodic_memory
        WHERE summary LIKE ? OR key_points LIKE ? OR concepts LIKE ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (search_pattern, search_pattern, search_pattern, top_k))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'session_id': row[1],
                'paper_id': row[2],
                'timestamp': row[3],
                'summary': row[4],
                'key_points': json.loads(row[5]) if row[5] else [],
                'formulas': json.loads(row[6]) if row[6] else [],
                'concepts': json.loads(row[7]) if row[7] else [],
                'metadata': json.loads(row[8]) if row[8] else {}
            })

        conn.close()
        return results

    def add_semantic_embedding(self, paper_id: str, embedding: List[float]) -> bool:
        """
        为情景记忆添加向量embedding（语义记忆接口）

        Args:
            paper_id: 论文ID
            embedding: 向量数据

        Returns:
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        embedding_json = json.dumps(embedding)

        cursor.execute("""
        UPDATE episodic_memory
        SET embedding = ?
        WHERE paper_id = ?
        """, (embedding_json, paper_id))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def get_all_episodic(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取所有情景记忆（用于向量索引构建）

        Args:
            limit: 返回数量限制

        Returns:
            所有情景记忆列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, session_id, paper_id, timestamp, summary, key_points, formulas, concepts, embedding, metadata
        FROM episodic_memory
        ORDER BY timestamp DESC
        LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'session_id': row[1],
                'paper_id': row[2],
                'timestamp': row[3],
                'summary': row[4],
                'key_points': json.loads(row[5]) if row[5] else [],
                'formulas': json.loads(row[6]) if row[6] else [],
                'concepts': json.loads(row[7]) if row[7] else [],
                'embedding': json.loads(row[8]) if row[8] else [],
                'metadata': json.loads(row[9]) if row[9] else {}
            })

        conn.close()
        return results


# ==================== 工具函数 ====================

def create_memory_manager(session_id: str) -> PaperMemoryManager:
    """
    创建记忆管理器实例的便捷函数

    Args:
        session_id: 会话ID

    Returns:
        PaperMemoryManager实例
    """
    return PaperMemoryManager(session_id)


if __name__ == "__main__":
    # 简单的测试
    manager = PaperMemoryManager("test-session-001")

    # 测试工作记忆
    manager.add_working_memory({
        "role": "user",
        "content": "请分析这篇论文的核心贡献"
    })
    manager.add_working_memory({
        "role": "assistant",
        "content": "这篇论文提出了..."
    })

    print("Working Memory:", manager.get_working_memory())
    print("Session Context:", manager.get_session_context())

    # 测试情景记忆
    manager.add_episodic("paper-123", {
        "summary": "本文提出了一种新的深度学习模型",
        "key_points": ["创新点1", "创新点2"],
        "formulas": ["E = mc^2"],
        "concepts": ["深度学习", "Transformer"]
    })

    print("\nEpisodic Memory:", manager.get_episodic_by_paper("paper-123"))
    print("\nRetrieve Relevant:", manager.retrieve_relevant("深度学习"))
