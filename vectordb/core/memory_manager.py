"""
三层记忆架构 - MemoryManager

实现论文知识库系统的三层记忆模型，模拟人类认知过程：
- Working Memory: 当前会话上下文（保持10轮对话）
- Episodic Memory: 论文分析快照（SQLite持久化）
- Semantic Memory: 向量知识库集成接口

设计意图：
    三层架构对应人类记忆的三个层次：
    1. Working Memory: 类似短期记忆，保持最近对话上下文，用于多轮对话连贯性
    2. Episodic Memory: 类似情景记忆，持久化论文分析历史，用于跨会话复用
    3. Semantic Memory: 类似语义记忆，向量检索接口，用于知识关联查询

使用场景：
    - RAG系统的上下文管理
    - 论文分析历史的持久化存储
    - 多轮对话的上下文追踪

Example:
    manager = PaperMemoryManager("session-001")
    manager.add_working_memory({"role": "user", "content": "查询Transformer论文"})
    manager.add_episodic("paper-123", {"summary": "...", "concepts": ["Attention"]})
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque

# 数据库路径 - 所有情景记忆数据统一存储在RAG系统数据库
DB_PATH = "/home/nvidia/workspace/paper/vectordb/rag_system.db"

# 工作记忆容量 - 保持最近10轮对话，平衡内存占用与上下文完整性
WORKING_MEMORY_SIZE = 10  # 保持最近10轮对话


class PaperMemoryManager:
    """
    三层记忆管理器

    设计意图: 统一管理论文知识库的三层记忆，提供检索、存储、查询接口
    输入: session_id - 会话唯一标识，用于区分不同用户/会话的记忆空间
    输出:
        - 工作记忆: 当前会话的对话历史列表
        - 情景记忆: 论文分析快照记录
        - 语义检索: 相关历史记录列表

    内部架构:
        - working_memory: deque双端队列，自动丢弃旧记录
        - episodic_memory表: SQLite存储，支持按session/paper查询
        - embedding字段: 预留向量索引接口

    Example:
        manager = PaperMemoryManager("user-session-001")
        manager.add_working_memory({"role": "user", "content": "查询论文"})
        manager.add_episodic("paper-id", {"summary": "核心贡献...", "concepts": ["MCP"]})
    """

    def __init__(self, session_id: str):
        """
        初始化记忆管理器

        设计意图: 创建会话专属的记忆空间，隔离不同会话的数据
        Args:
            session_id: 会话ID，用于区分不同用户/任务的记忆空间
        Side Effects:
            - 创建SQLite连接（如数据库不存在则创建）
            - 初始化episodic_memory表结构（如不存在）
            - 创建session_id和paper_id索引以优化查询性能
        """
        self.session_id = session_id
        # 使用deque实现自动丢弃策略，超出容量时自动移除最早记录
        self.working_memory = deque(maxlen=WORKING_MEMORY_SIZE)  # 工作记忆

        # 初始化情景记忆表 - 确保数据库结构完整
        self._init_episodic_table()

    def _get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接

        设计意图: 每次操作创建新连接，避免连接池管理的复杂性
        Returns:
            sqlite3.Connection: 数据库连接对象
        Note:
            这种设计适合低频写入场景，高频场景建议使用连接池
        """
        return sqlite3.connect(DB_PATH)

    def _init_episodic_table(self):
        """
        初始化情景记忆表

        设计意图: 创建持久化存储结构，支持论文分析历史的跨会话查询
        Side Effects:
            - 创建episodic_memory表（如不存在）
            - 创建session_id索引（优化按会话查询）
            - 创建paper_id索引（优化按论文查询）

        表结构设计:
            - paper_id: 论文唯一标识，支持跨会话聚合同一论文的分析
            - embedding字段: JSON存储向量，预留向量检索接口
            - key_points/formulas/concepts: JSON数组，灵活存储分析结果
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 表结构设计：支持论文分析的完整记录
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,

            -- 论文分析内容：JSON序列化存储
            summary TEXT,
            key_points TEXT,  -- JSON数组
            formulas TEXT,    -- JSON数组
            concepts TEXT,    -- JSON数组

            -- 检索向量（用于相似度检索）- 预留向量检索接口
            embedding TEXT,   -- JSON数组

            -- 元数据 - 扩展字段，支持未来新增属性
            metadata TEXT     -- JSON格式扩展
        )
        """)

        # 创建索引 - 优化高频查询场景
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_episodic_session
        ON episodic_memory(session_id)
        """)  # 按会话查询：获取用户当前会话的所有分析历史
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_episodic_paper
        ON episodic_memory(paper_id)
        """)  # 按论文查询：获取同一论文的所有分析记录

        conn.commit()
        conn.close()

    # ==================== Working Memory ====================
    # Working Memory层：短期记忆，保持当前会话上下文
    # 设计意图：支持多轮对话的连贯性，自动丢弃旧记录避免内存溢出

    def add_working_memory(self, message: Dict[str, Any]) -> None:
        """
        添加当前对话到工作记忆

        设计意图: 记录对话历史，支持后续上下文检索和连贯性分析
        Args:
            message: 消息字典，应包含 'role' 和 'content' 字段
        Side Effects:
            - 添加记录到deque队列
            - 如果超出WORKING_MEMORY_SIZE(10)，自动移除最早记录
        Note:
            使用deque的maxlen属性实现自动丢弃，无需手动管理队列大小
        """
        # 添加时间戳 - 用于后续按时间排序和对话分析
        message_with_time = {
            **message,
            'timestamp': datetime.now().isoformat()
        }
        self.working_memory.append(message_with_time)

    def get_working_memory(self) -> List[Dict[str, Any]]:
        """
        获取工作记忆所有内容

        设计意图: 提供当前会话完整对话历史，用于LLM上下文构建
        Returns:
            消息列表，每条包含role、content、timestamp字段
        Note:
            返回顺序为时间正序（先加入的在前），适合对话历史展示
        """
        return list(self.working_memory)

    def clear_working_memory(self) -> None:
        """
        清空工作记忆

        设计意图: 重置会话状态，用于新话题切换或测试场景
        Side Effects:
            - 清空deque队列，所有历史记录丢失
        """
        self.working_memory.clear()

    def get_session_context(self) -> Dict[str, Any]:
        """
        获取当前会话上下文

        设计意图: 汇总会话信息，用于调试和状态展示
        Returns:
            包含工作记忆和会话信息的字典
        Example:
            {
                'session_id': 'session-001',
                'working_memory': [...],
                'message_count': 5
            }
        """
        return {
            'session_id': self.session_id,
            'working_memory': list(self.working_memory),
            'message_count': len(self.working_memory)
        }

    # ==================== Episodic Memory ====================
    # Episodic Memory层：情景记忆，持久化论文分析历史
    # 设计意图：支持跨会话复用分析结果，避免重复分析同一论文

    def add_episodic(self, paper_id: str, analysis: Dict[str, Any]) -> int:
        """
        记录论文分析历史到情景记忆

        设计意图: 持久化分析结果，支持后续跨会话查询和复用
        Args:
            paper_id: 论文ID，通常为论文标题或唯一标识
            analysis: 分析结果字典，应包含:
                - summary: 摘要（简要描述论文核心内容）
                - key_points: 核心观点列表（主要创新点）
                - formulas: 公式列表（关键数学公式）
                - concepts: 概念列表（核心技术术语）
                - embedding: 向量（可选，用于向量检索）
                - metadata: 额外元数据（可选，如论文来源、作者等）
        Returns:
            记录的ID，可用于后续更新或删除
        Side Effects:
            - 写入SQLite数据库
            - JSON序列化数组字段
        Example:
            manager.add_episodic("arxiv-2605.18747", {
                "summary": "提出Code as Agent架构",
                "key_points": ["Harness Interface", "MCP Tool Use"],
                "formulas": ["E = mc^2"],
                "concepts": ["MCP", "Agent", "Harness"]
            })
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 序列化JSON字段 - SQLite不支持数组类型，需JSON序列化
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

        设计意图: 获取同一论文在当前会话的所有分析记录，支持分析演进追踪
        Args:
            paper_id: 论文ID
        Returns:
            分析历史列表（仅当前会话的数据），按时间倒序
        Note:
            仅返回当前会话数据，避免跨会话数据混淆
            如果需要跨会话查询，使用get_episodic_by_session或retrieve_relevant
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 查询条件：同时匹配paper_id和session_id，确保数据隔离
        cursor.execute("""
        SELECT id, session_id, paper_id, timestamp, summary, key_points, formulas, concepts, metadata
        FROM episodic_memory
        WHERE paper_id = ? AND session_id = ?
        ORDER BY timestamp DESC
        """, (paper_id, self.session_id))

        results = []
        for row in cursor.fetchall():
            # JSON反序列化 - 从SQLite读取时需要解析JSON数组
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

        设计意图: 获取整个会话的所有论文分析记录，用于会话总结和历史回顾
        Args:
            session_id: 会话ID
        Returns:
            分析历史列表，按时间倒序排列
        Note:
            跨session_id查询，用于历史数据分析或管理员查看
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
    # Semantic Memory层：语义记忆，向量检索接口
    # 设计意图：基于向量相似度检索相关历史，实现知识关联

    def retrieve_relevant(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        检索相关历史（语义记忆）

        设计意图: 根据查询文本检索相似的历史分析记录，实现知识复用
        Args:
            query: 查询文本
            top_k: 返回数量，默认5条
        Returns:
            相关情景记忆列表，按时间倒序

        Note:
            当前实现基于文本关键词匹配（LIKE查询）
            未来可接入向量检索引擎（如Milvus/Qdrant），使用embedding字段

        实现细节:
            1. 使用LIKE进行关键词匹配
            2. 同时匹配summary、key_points、concepts三个字段
            3. 按时间倒序返回最新记录
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 简单的关键词匹配检索（未来可替换为向量检索）
        # 匹配summary、key_points、concepts中的内容 - 提高匹配覆盖率
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

        设计意图: 为历史记录添加向量，支持未来的向量检索功能
        Args:
            paper_id: 论文ID
            embedding: 向量数据，通常为768或1024维的float数组
        Returns:
            是否成功更新
        Side Effects:
            - 更新episodic_memory表的embedding字段
        Note:
            当前为预留接口，实际向量检索需要配合向量数据库
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        embedding_json = json.dumps(embedding)

        cursor.execute("""
        UPDATE episodic_memory
        SET embedding = ?
        WHERE paper_id = ?
        """, (embedding_json, paper_id))

        success = cursor.rowcount > 0  # 检查是否有记录被更新
        conn.commit()
        conn.close()

        return success

    def get_all_episodic(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取所有情景记忆（用于向量索引构建）

        设计意图: 批量导出所有历史记录，用于向量数据库初始化或迁移
        Args:
            limit: 返回数量限制，避免大数据量查询
        Returns:
            所有情景记忆列表，包含embedding字段
        Note:
            包含embedding字段，用于构建向量索引
            按时间倒序返回最新的记录优先
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

    设计意图: 简化实例创建流程，统一入口
    Args:
        session_id: 会话ID
    Returns:
        PaperMemoryManager实例
    Example:
        manager = create_memory_manager("user-session-001")
    """
    return PaperMemoryManager(session_id)


if __name__ == "__main__":
    # 简单的测试 - 验证三层记忆功能完整性
    manager = PaperMemoryManager("test-session-001")

    # 测试工作记忆 - 验证deque自动丢弃机制
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

    # 测试情景记忆 - 验证SQLite持久化
    manager.add_episodic("paper-123", {
        "summary": "本文提出了一种新的深度学习模型",
        "key_points": ["创新点1", "创新点2"],
        "formulas": ["E = mc^2"],
        "concepts": ["深度学习", "Transformer"]
    })

    print("\nEpisodic Memory:", manager.get_episodic_by_paper("paper-123"))
    print("\nRetrieve Relevant:", manager.retrieve_relevant("深度学习"))
