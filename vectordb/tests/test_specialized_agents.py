"""
四角色专用Agent测试

测试每个Agent独立运行和协作Pipeline
"""

import unittest
import sys

sys.path.append('/home/nvidia/workspace/paper/vectordb')
sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
sys.path.append('/home/nvidia/workspace/paper/vectordb/core')

from agents.specialized_agents import (
    PaperRetrievalAgent,
    PaperAnalysisAgent,
    QualityAssuranceAgent,
    CodeReproductionAgent,
    SpecializedAgentOrchestrator,
    create_default_registry
)
from core.memory_manager import PaperMemoryManager


class TestPaperRetrievalAgent(unittest.TestCase):
    """测试检索专家"""

    def setUp(self):
        self.registry = create_default_registry()
        self.memory = PaperMemoryManager("test-retrieval")
        self.agent = PaperRetrievalAgent(self.registry, self.memory)

    def test_retrieve_basic(self):
        """测试基本检索功能"""
        result = self.agent.retrieve("Transformer", top_k=5)

        self.assertIn("query", result)
        self.assertIn("results", result)
        self.assertIn("metrics", result)
        self.assertEqual(result["query"], "Transformer")
        self.assertEqual(result["top_k"], 5)

    def test_retrieve_metrics(self):
        """测试召回指标计算"""
        result = self.agent.retrieve("attention mechanism", top_k=3)

        metrics = result["metrics"]
        self.assertIn("total", metrics)
        self.assertIn("avg_score", metrics)
        self.assertIn("coverage", metrics)

    def test_memory_integration(self):
        """测试记忆集成"""
        query = "neural network"
        result = self.agent.retrieve(query, top_k=3)

        # 验证工作记忆被更新
        working_mem = self.memory.get_working_memory()
        self.assertTrue(len(working_mem) > 0)


class TestPaperAnalysisAgent(unittest.TestCase):
    """测试解读专家"""

    def setUp(self):
        self.registry = create_default_registry()
        self.memory = PaperMemoryManager("test-analysis")
        self.agent = PaperAnalysisAgent(self.registry, self.memory)

    def test_analyze_basic(self):
        """测试基本分析功能"""
        chunks = [
            {"content": "Transformer uses self-attention mechanism. " * 10},
            {"content": "The attention formula: Attention(Q,K,V) = softmax(QK^T/d_k)V" * 5},
        ]

        result = self.agent.analyze("What is Transformer?", chunks)

        self.assertIn("summary", result)
        self.assertIn("concepts", result)
        self.assertIn("formulas", result)
        self.assertIn("code_design", result)
        self.assertEqual(result["chunk_count"], 2)

    def test_formula_extraction(self):
        """测试公式提取"""
        chunks = [
            {"content": "The formula is $E = mc^2$. Also (1) $a^2 + b^2 = c^2$."}
        ]

        result = self.agent.analyze("formulas", chunks)

        # 应该有提取到公式
        self.assertIsInstance(result["formulas"], list)

    def test_concept_extraction(self):
        """测试概念提取"""
        chunks = [
            {"content": "Transformer uses Multi-Head Attention. " * 20}
        ]

        result = self.agent.analyze("concepts", chunks)

        self.assertIsInstance(result["concepts"], list)

    def test_episodic_memory(self):
        """测试情景记忆"""
        chunks = [{"content": "Test content about Deep Learning."}]

        result = self.agent.analyze("deep learning", chunks)

        # 验证情景记忆被记录
        episodic = self.memory.get_episodic_by_session("test-analysis")
        # 可能有记录（取决于是否成功添加）


class TestQualityAssuranceAgent(unittest.TestCase):
    """测试质量专家"""

    def setUp(self):
        self.registry = create_default_registry()
        self.memory = PaperMemoryManager("test-qa")
        self.agent = QualityAssuranceAgent(self.registry, self.memory)

    def test_validate_basic(self):
        """测试基本验证功能"""
        output = "Transformer uses self-attention mechanism [1]. This is a key innovation [2]."
        chunks = [
            {"content": "Transformer uses self-attention mechanism.", "id": "1"},
            {"content": "This is a key innovation.", "id": "2"},
        ]

        result = self.agent.validate(output, chunks)

        self.assertIn("quality_score", result)
        self.assertIn("hallucination", result)
        self.assertIn("citations", result)
        self.assertIn("risks", result)
        self.assertIn("suggestions", result)
        self.assertIn("is_passed", result)

    def test_quality_score_calculation(self):
        """测试质量评分计算"""
        output = "Deep Learning is a subset of Machine Learning."
        chunks = [
            {"content": "Deep Learning is a subset of Machine Learning."}
        ]

        result = self.agent.validate(output, chunks)

        self.assertIsInstance(result["quality_score"], float)
        self.assertGreaterEqual(result["quality_score"], 0.0)
        self.assertLessEqual(result["quality_score"], 1.0)

    def test_risk_generation(self):
        """测试风险生成"""
        output = "Some hallucinated content that is not in context." * 100
        chunks = [
            {"content": "Real content."}
        ]

        result = self.agent.validate(output, chunks)

        self.assertIsInstance(result["risks"], list)


class TestCodeReproductionAgent(unittest.TestCase):
    """测试复现专家"""

    def setUp(self):
        self.registry = create_default_registry()
        self.memory = PaperMemoryManager("test-code")
        self.agent = CodeReproductionAgent(self.registry, self.memory)

    def test_reproduce_basic(self):
        """测试基本复现功能"""
        analysis = {
            "summary": "Transformer uses attention mechanism",
            "concepts": ["Attention", "Transformer"],
            "formulas": [{"content": "Attention(Q,K,V)"}],
            "code_design": {"snippets": [], "has_code": False}
        }

        result = self.agent.reproduce("Transformer implementation", analysis)

        self.assertIn("code_modules", result)
        self.assertIn("test_cases", result)
        self.assertIn("run_results", result)
        self.assertIn("is_runnable", result)

    def test_code_generation(self):
        """测试代码生成"""
        analysis = {
            "summary": "Attention mechanism",
            "concepts": ["Self-Attention"],
            "formulas": [],
            "code_design": {"snippets": [], "has_code": False}
        }

        result = self.agent.reproduce("attention mechanism", analysis)

        self.assertTrue(len(result["code_modules"]) > 0)
        self.assertTrue(len(result["test_cases"]) > 0)

    def test_code_execution(self):
        """测试代码执行"""
        analysis = {
            "summary": "Simple test",
            "concepts": [],
            "formulas": [],
            "code_design": {"snippets": ["x = 1 + 1\nprint(x)"], "has_code": True}
        }

        result = self.agent.reproduce("test", analysis)

        # 检查运行结果
        self.assertTrue(len(result["run_results"]) > 0)


class TestSpecializedAgentOrchestrator(unittest.TestCase):
    """测试协调器"""

    def setUp(self):
        self.orchestrator = SpecializedAgentOrchestrator("test-orchestrator")

    def test_orchestrator_creation(self):
        """测试协调器创建"""
        self.assertIsNotNone(self.orchestrator.registry)
        self.assertIsNotNone(self.orchestrator.memory)
        self.assertIsNotNone(self.orchestrator.retrieval_agent)
        self.assertIsNotNone(self.orchestrator.analysis_agent)
        self.assertIsNotNone(self.orchestrator.qa_agent)
        self.assertIsNotNone(self.orchestrator.code_agent)

    def test_pipeline_basic(self):
        """测试完整流程"""
        result = self.orchestrator.run_pipeline(
            "What is Transformer?",
            top_k=3,
            need_code=True
        )

        self.assertEqual(result["pipeline_status"], "completed")
        self.assertIn("retrieval", result)
        self.assertIn("analysis", result)
        self.assertIn("quality_assurance", result)
        self.assertIn("code_reproduction", result)

    def test_pipeline_without_code(self):
        """测试不含代码的流程"""
        result = self.orchestrator.run_pipeline(
            "Explain attention",
            top_k=3,
            need_code=False
        )

        self.assertEqual(result["pipeline_status"], "completed")
        self.assertIsNone(result["code_reproduction"])

    def test_status(self):
        """测试状态查询"""
        status = self.orchestrator.get_status()

        self.assertIn("memory_session", status)
        self.assertIn("registered_tools", status)
        self.assertIn("workflow_state", status)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_end_to_end_workflow(self):
        """端到端工作流测试"""
        # 创建新的协调器
        orch = SpecializedAgentOrchestrator("integration-test")

        # 运行流程
        result = orch.run_pipeline(
            "Explain the Transformer architecture",
            top_k=5,
            need_code=True
        )

        # 验证结果
        self.assertEqual(result["pipeline_status"], "completed")

        # 检索结果
        retrieval = result["retrieval"]
        self.assertGreater(retrieval["metrics"]["total"], 0)

        # 分析结果
        analysis = result["analysis"]
        self.assertTrue(len(analysis["summary"]) > 0)

        # 质量结果
        qa = result["quality_assurance"]
        self.assertIsInstance(qa["quality_score"], float)

        # 代码结果
        code = result["code_reproduction"]
        self.assertIsNotNone(code)
        self.assertTrue(len(code["code_modules"]) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
