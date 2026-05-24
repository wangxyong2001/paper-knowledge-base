"""
ToolRegistry 测试套件

测试工具注册中心的各项功能：
1. 工具注册和执行
2. 参数验证
3. 错误处理
4. 工具schema
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb')
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb/core')

from tool_registry import (
    ToolRegistry,
    BaseTool,
    VectorSearchTool,
    BM25SearchTool,
    HybridSearchTool,
    TableExtractTool,
    CitationCheckTool,
    HallucinationDetectTool,
    PythonExecTool,
    create_default_registry
)


class TestBaseTool(unittest.TestCase):
    """测试BaseTool基类"""

    def test_abstract_methods(self):
        """测试抽象方法必须实现"""

        class DummyTool(BaseTool):
            def run(self, params):
                return {"result": "ok"}

            def get_schema(self):
                return {"name": "dummy"}

        tool = DummyTool()
        self.assertIsInstance(tool, BaseTool)
        result = tool.run({})
        self.assertEqual(result["result"], "ok")

    def test_validate_default(self):
        """测试默认验证总是返回True"""

        class DummyTool(BaseTool):
            def run(self, params):
                return {}

            def get_schema(self):
                return {}

        tool = DummyTool()
        self.assertTrue(tool.validate({}))
        self.assertTrue(tool.validate({"any": "params"}))


class TestToolRegistry(unittest.TestCase):
    """测试ToolRegistry核心功能"""

    def setUp(self):
        self.registry = ToolRegistry()

    def test_register_tool(self):
        """测试工具注册"""

        class DummyTool(BaseTool):
            def run(self, params):
                return {"result": "dummy"}

            def get_schema(self):
                return {"name": "dummy", "description": "测试工具"}

        tool = DummyTool()
        self.registry.register_tool("dummy", tool)

        self.assertIn("dummy", self.registry.list_tools())

    def test_register_invalid_tool(self):
        """测试注册无效工具"""

        with self.assertRaises(TypeError):
            self.registry.register_tool("invalid", {})

    def test_execute(self):
        """测试工具执行"""

        class EchoTool(BaseTool):
            def run(self, params):
                return {"echo": params.get("message", "")}

            def get_schema(self):
                return {"name": "echo"}

        self.registry.register_tool("echo", EchoTool())

        result = self.registry.execute("echo", {"message": "hello"})
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["echo"], "hello")

    def test_execute_nonexistent_tool(self):
        """测试执行不存在的工具"""

        result = self.registry.execute("not_exists", {})
        self.assertFalse(result["success"])
        self.assertIn("未注册", result["error"])

    def test_list_tools(self):
        """测试列出工具"""

        class ToolA(BaseTool):
            def run(self, params): return {}
            def get_schema(self): return {}

        class ToolB(BaseTool):
            def run(self, params): return {}
            def get_schema(self): return {}

        self.registry.register_tool("tool_a", ToolA())
        self.registry.register_tool("tool_b", ToolB())

        tools = self.registry.list_tools()
        self.assertEqual(len(tools), 2)
        self.assertIn("tool_a", tools)
        self.assertIn("tool_b", tools)

    def test_validate_params(self):
        """测试参数验证"""

        class ValidatedTool(BaseTool):
            def run(self, params):
                return {}

            def validate(self, params):
                return "required_field" in params

            def get_schema(self):
                return {}

        self.registry.register_tool("validated", ValidatedTool())

        self.assertTrue(self.registry.validate_params("validated", {"required_field": "value"}))
        self.assertFalse(self.registry.validate_params("validated", {"other": "value"}))

    def test_validate_params_nonexistent(self):
        """测试验证不存在的工具"""

        self.assertFalse(self.registry.validate_params("not_exists", {}))

    def test_get_schema(self):
        """测试获取工具schema"""

        class SchemaTool(BaseTool):
            def run(self, params): return {}

            def get_schema(self):
                return {"name": "schema_tool", "description": "测试", "parameters": {}}

        self.registry.register_tool("schema_tool", SchemaTool())

        schema = self.registry.get_schema("schema_tool")
        self.assertIsNotNone(schema)
        self.assertEqual(schema["name"], "schema_tool")

    def test_get_all_schemas(self):
        """测试获取所有schema"""

        class ToolA(BaseTool):
            def run(self, params): return {}
            def get_schema(self): return {"name": "a"}

        class ToolB(BaseTool):
            def run(self, params): return {}
            def get_schema(self): return {"name": "b"}

        self.registry.register_tool("a", ToolA())
        self.registry.register_tool("b", ToolB())

        all_schemas = self.registry.get_all_schemas()
        self.assertEqual(len(all_schemas), 2)

    def test_unregister_tool(self):
        """测试注销工具"""

        class Tool(BaseTool):
            def run(self, params): return {}
            def get_schema(self): return {}

        self.registry.register_tool("to_remove", Tool())

        self.assertTrue(self.registry.unregister_tool("to_remove"))
        self.assertNotIn("to_remove", self.registry.list_tools())

    def test_execute_with_exception(self):
        """测试执行时异常处理"""

        class FailingTool(BaseTool):
            def run(self, params):
                raise ValueError("执行失败")

            def get_schema(self):
                return {}

        self.registry.register_tool("failing", FailingTool())

        result = self.registry.execute("failing", {})
        self.assertFalse(result["success"])
        self.assertIn("执行错误", result["error"])


class TestVectorSearchTool(unittest.TestCase):
    """测试向量检索工具"""

    def test_get_schema(self):
        tool = VectorSearchTool()
        schema = tool.get_schema()

        self.assertEqual(schema["name"], "vector_search")
        self.assertIn("query", schema["parameters"]["properties"])
        self.assertIn("top_k", schema["parameters"]["properties"])

    def test_validate(self):
        tool = VectorSearchTool()

        self.assertTrue(tool.validate({"query": "test"}))
        self.assertFalse(tool.validate({}))
        self.assertFalse(tool.validate({"query": 123}))

    @patch('tool_registry.HybridSearcher')
    def test_run(self, mock_searcher):
        mock_instance = MagicMock()
        mock_instance.vector_search.return_value = [{"chunk_id": "1", "content": "test"}]
        mock_searcher.return_value = mock_instance

        tool = VectorSearchTool()
        result = tool.run({"query": "test", "top_k": 5})

        self.assertIn("results", result)
        self.assertEqual(result["count"], 1)


class TestBM25SearchTool(unittest.TestCase):
    """测试BM25检索工具"""

    def test_get_schema(self):
        tool = BM25SearchTool()
        schema = tool.get_schema()

        self.assertEqual(schema["name"], "bm25_search")

    def test_validate(self):
        tool = BM25SearchTool()

        self.assertTrue(tool.validate({"query": "test"}))
        self.assertFalse(tool.validate({}))


class TestTableExtractTool(unittest.TestCase):
    """测试表格提取工具"""

    def test_get_schema(self):
        tool = TableExtractTool()
        schema = tool.get_schema()

        self.assertEqual(schema["name"], "table_extract")
        self.assertIn("text", schema["parameters"]["properties"])

    def test_validate(self):
        tool = TableExtractTool()

        self.assertTrue(tool.validate({"text": "some text"}))
        self.assertFalse(tool.validate({}))

    def test_run_with_table(self):
        tool = TableExtractTool()

        text = """
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| a   | b   | c   |
| d   | e   | f   |
"""

        result = tool.run({"text": text})
        self.assertEqual(result["count"], 1)
        self.assertIn("tables", result)

    def test_run_no_table(self):
        tool = TableExtractTool()

        text = "这是一段普通文本，没有表格"
        result = tool.run({"text": text})

        self.assertEqual(result["count"], 0)

    def test_to_markdown(self):
        tool = TableExtractTool()

        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = tool.run({"text": text, "format": "markdown"})

        self.assertIn("|", result["tables"])


class TestCitationCheckTool(unittest.TestCase):
    """测试引用验证工具"""

    def test_get_schema(self):
        tool = CitationCheckTool()
        schema = tool.get_schema()

        self.assertEqual(schema["name"], "citation_check")

    def test_validate(self):
        tool = CitationCheckTool()

        self.assertTrue(tool.validate({"answer": "text [1]", "contexts": []}))
        self.assertFalse(tool.validate({"answer": "text"}))

    def test_run(self):
        tool = CitationCheckTool()

        result = tool.run({
            "answer": "答案来自[1]和[2]",
            "contexts": [
                {"content": "context 1", "chunk_id": "c1"},
                {"content": "context 2", "chunk_id": "c2"}
            ]
        })

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["valid_count"], 2)

    def test_run_invalid_citation(self):
        tool = CitationCheckTool()

        result = tool.run({
            "answer": "答案来自[1]和[5]",
            "contexts": [
                {"content": "context 1", "chunk_id": "c1"}
            ]
        })

        self.assertEqual(result["valid_count"], 1)


class TestHallucinationDetectTool(unittest.TestCase):
    """测试幻觉检测工具"""

    def test_get_schema(self):
        tool = HallucinationDetectTool()
        schema = tool.get_schema()

        self.assertEqual(schema["name"], "hallucination_detect")

    def test_validate(self):
        tool = HallucinationDetectTool()

        self.assertTrue(tool.validate({"answer": "text", "contexts": ["ctx"]}))
        self.assertFalse(tool.validate({"answer": "text"}))

    def test_run_supported(self):
        tool = HallucinationDetectTool()

        result = tool.run({
            "answer": "Transformer 是 Google 提出的模型",
            "contexts": ["Transformer 是 Google 提出的模型，用于NLP任务"]
        })

        self.assertFalse(result["is_hallucination"])
        self.assertEqual(result["risk_level"], "low")

    def test_run_unsupported(self):
        tool = HallucinationDetectTool()

        result = tool.run({
            "answer": "XYZ模型有1000亿参数",
            "contexts": ["这是一些不相关的上下文"]
        })

        self.assertTrue(result["is_hallucination"])
        self.assertEqual(result["risk_level"], "high")

    def test_extract_entities(self):
        tool = HallucinationDetectTool()

        entities = tool._extract_entities("Transformer 是 Google 提出的")
        self.assertIn("Transformer", entities)
        self.assertIn("Google", entities)


class TestPythonExecTool(unittest.TestCase):
    """测试Python执行工具"""

    def test_get_schema(self):
        tool = PythonExecTool()
        schema = tool.get_schema()

        self.assertEqual(schema["name"], "python_exec")
        self.assertIn("code", schema["parameters"]["properties"])

    def test_validate_safe_code(self):
        tool = PythonExecTool()

        self.assertTrue(tool.validate({"code": "print(1 + 1)"}))
        self.assertTrue(tool.validate({"code": "result = [x for x in range(10)]"}))

    def test_validate_dangerous_code(self):
        tool = PythonExecTool()

        self.assertFalse(tool.validate({"code": "import os"}))
        self.assertFalse(tool.validate({"code": "import sys"}))
        self.assertFalse(tool.validate({"code": "open('file.txt')"}))
        self.assertFalse(tool.validate({"code": "eval('1+1')"}))

    def test_run_basic(self):
        tool = PythonExecTool()

        result = tool.run({"code": "print('hello world')"})

        self.assertTrue(result["success"])
        self.assertIn("hello world", result["stdout"])

    def test_run_calculation(self):
        tool = PythonExecTool()

        result = tool.run({"code": "x = 2 + 3"})

        self.assertTrue(result["success"])
        self.assertIn("locals", result)

    def test_run_error(self):
        tool = PythonExecTool()

        result = tool.run({"code": "raise ValueError('test error')"})

        self.assertFalse(result["success"])
        self.assertIn("test error", result["error"])


class TestCreateDefaultRegistry(unittest.TestCase):
    """测试默认注册中心创建"""

    def test_create_registry(self):
        registry = create_default_registry()

        tools = registry.list_tools()

        # 验证所有必需工具都已注册
        expected_tools = [
            "vector_search",
            "bm25_search",
            "hybrid_search",
            "table_extract",
            "citation_check",
            "hallucination_detect",
            "python_exec"
        ]

        for tool_name in expected_tools:
            self.assertIn(tool_name, tools, f"工具 {tool_name} 未注册")

    def test_all_tools_executable(self):
        registry = create_default_registry()

        # 测试每个工具的schema都可以获取
        for tool_name in registry.list_tools():
            schema = registry.get_schema(tool_name)
            self.assertIsNotNone(schema)
            self.assertIn("name", schema)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestBaseTool))
    suite.addTests(loader.loadTestsFromTestCase(TestToolRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorSearchTool))
    suite.addTests(loader.loadTestsFromTestCase(TestBM25SearchTool))
    suite.addTests(loader.loadTestsFromTestCase(TestTableExtractTool))
    suite.addTests(loader.loadTestsFromTestCase(TestCitationCheckTool))
    suite.addTests(loader.loadTestsFromTestCase(TestHallucinationDetectTool))
    suite.addTests(loader.loadTestsFromTestCase(TestPythonExecTool))
    suite.addTests(loader.loadTestsFromTestCase(TestCreateDefaultRegistry))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("ToolRegistry 测试套件")
    print("=" * 60)

    result = run_tests()

    print("\n" + "=" * 60)
    print(f"测试结果: {result.testsRun} 个测试, {len(result.failures)} 个失败, {len(result.errors)} 个错误")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)
