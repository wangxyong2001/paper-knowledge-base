"""
测试 PaperMemoryManager 三层记忆功能
- Working Memory 测试
- Episodic Memory 测试
- 跨会话复用测试
"""

import unittest
import sys
import os

# 添加项目路径
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb')

from core.memory_manager import PaperMemoryManager, create_memory_manager


class TestPaperMemoryManager(unittest.TestCase):
    """测试三层记忆管理器"""

    @classmethod
    def setUpClass(cls):
        """测试前初始化"""
        cls.session_id = "test-session-001"
        cls.manager = PaperMemoryManager(cls.session_id)

    def setUp(self):
        """每个测试前清空工作记忆"""
        self.manager.clear_working_memory()

    # ==================== Working Memory Tests ====================

    def test_add_working_memory(self):
        """测试添加工作记忆"""
        message = {"role": "user", "content": "分析这篇论文"}
        self.manager.add_working_memory(message)

        memory = self.manager.get_working_memory()
        self.assertEqual(len(memory), 1)
        self.assertEqual(memory[0]["role"], "user")
        self.assertIn("timestamp", memory[0])

    def test_working_memory_limit(self):
        """测试工作记忆保持10轮对话"""
        # 添加15条消息
        for i in range(15):
            self.manager.add_working_memory({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"消息 {i}"
            })

        memory = self.manager.get_working_memory()
        # 应该保持最近10条
        self.assertEqual(len(memory), 10)
        # 第一条应该是第5条（索引5）
        self.assertEqual(memory[0]["content"], "消息 5")

    def test_get_session_context(self):
        """测试获取会话上下文"""
        self.manager.add_working_memory({"role": "user", "content": "测试"})
        self.manager.add_working_memory({"role": "assistant", "content": "回复"})

        context = self.manager.get_session_context()
        self.assertEqual(context["session_id"], self.session_id)
        self.assertEqual(context["message_count"], 2)
        self.assertEqual(len(context["working_memory"]), 2)

    def test_clear_working_memory(self):
        """测试清空工作记忆"""
        self.manager.add_working_memory({"role": "user", "content": "测试"})
        self.manager.clear_working_memory()

        memory = self.manager.get_working_memory()
        self.assertEqual(len(memory), 0)

    # ==================== Episodic Memory Tests ====================

    def test_add_episodic(self):
        """测试添加情景记忆"""
        analysis = {
            "summary": "测试论文摘要",
            "key_points": ["要点1", "要点2"],
            "formulas": ["F=ma"],
            "concepts": ["物理学", "力学"],
            "metadata": {"author": "test"}
        }

        record_id = self.manager.add_episodic("paper-001", analysis)
        self.assertIsNotNone(record_id)
        self.assertGreater(record_id, 0)

    def test_get_episodic_by_paper(self):
        """测试根据论文ID获取情景记忆"""
        # 添加两条情景记忆
        self.manager.add_episodic("paper-002", {
            "summary": "论文A摘要",
            "key_points": ["A1", "A2"],
            "formulas": [],
            "concepts": ["AI"]
        })

        self.manager.add_episodic("paper-002", {
            "summary": "论文A更新摘要",
            "key_points": ["A3"],
            "formulas": [],
            "concepts": ["ML"]
        })

        results = self.manager.get_episodic_by_paper("paper-002")
        self.assertEqual(len(results), 2)

    def test_get_episodic_by_session(self):
        """测试根据会话ID获取情景记忆"""
        session_id = "test-session-002"
        manager2 = PaperMemoryManager(session_id)

        manager2.add_episodic("paper-003", {
            "summary": "论文B摘要",
            "key_points": ["B1"],
            "formulas": [],
            "concepts": ["NLP"]
        })

        results = manager2.get_episodic_by_session(session_id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["paper_id"], "paper-003")

    # ==================== Semantic Memory Tests ====================

    def test_retrieve_relevant(self):
        """测试语义检索"""
        # 添加情景记忆
        self.manager.add_episodic("paper-004", {
            "summary": "深度学习在图像识别中的应用",
            "key_points": ["CNN模型", "ResNet结构"],
            "formulas": [],
            "concepts": ["深度学习", "计算机视觉"]
        })

        self.manager.add_episodic("paper-005", {
            "summary": "自然语言处理的Transformer模型",
            "key_points": ["注意力机制", "BERT"],
            "formulas": [],
            "concepts": ["NLP", "Transformer"]
        })

        # 检索"深度学习"
        results = self.manager.retrieve_relevant("深度学习")
        self.assertGreater(len(results), 0)
        self.assertTrue(
            "深度学习" in results[0]["summary"] or
            "深度学习" in str(results[0]["concepts"])
        )

    def test_add_semantic_embedding(self):
        """测试添加向量embedding"""
        # 先添加情景记忆
        self.manager.add_episodic("paper-006", {
            "summary": "测试摘要",
            "key_points": [],
            "formulas": [],
            "concepts": []
        })

        # 添加向量
        embedding = [0.1] * 128
        success = self.manager.add_semantic_embedding("paper-006", embedding)
        self.assertTrue(success)

    def test_get_all_episodic(self):
        """测试获取所有情景记忆"""
        # 添加多条情景记忆
        self.manager.add_episodic("paper-007", {
            "summary": "摘要1",
            "key_points": [],
            "formulas": [],
            "concepts": []
        })
        self.manager.add_episodic("paper-008", {
            "summary": "摘要2",
            "key_points": [],
            "formulas": [],
            "concepts": []
        })

        # 跨会话再添加一条
        manager2 = PaperMemoryManager("test-session-003")
        manager2.add_episodic("paper-009", {
            "summary": "摘要3",
            "key_points": [],
            "formulas": [],
            "concepts": []
        })

        # 获取所有情景记忆
        all_episodic = self.manager.get_all_episodic(limit=10)
        self.assertGreaterEqual(len(all_episodic), 3)

    # ==================== Cross-Session Tests ====================

    def test_cross_session_reuse(self):
        """测试跨会话复用"""
        # 会话1: 添加情景记忆
        session1 = PaperMemoryManager("session-A")
        session1.add_episodic("paper-cross-1", {
            "summary": "跨会话论文",
            "key_points": ["跨会话要点"],
            "formulas": [],
            "concepts": ["测试"]
        })

        # 会话2: 检索同一论文
        session2 = PaperMemoryManager("session-B")
        results = session2.get_episodic_by_paper("paper-cross-1")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["summary"], "跨会话论文")

    def test_working_memory_isolation(self):
        """测试工作记忆会话隔离"""
        manager1 = PaperMemoryManager("session-1")
        manager2 = PaperMemoryManager("session-2")

        # manager1添加工作记忆
        manager1.add_working_memory({"role": "user", "content": "会话1消息"})

        # manager2应该是独立的
        self.assertEqual(len(manager2.get_working_memory()), 0)

    def test_create_helper_function(self):
        """测试便捷创建函数"""
        manager = create_memory_manager("helper-test")
        self.assertEqual(manager.session_id, "helper-test")

        manager.add_working_memory({"role": "user", "content": "测试"})
        self.assertEqual(len(manager.get_working_memory()), 1)


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
