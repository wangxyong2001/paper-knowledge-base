"""
ToolRegistry - 统一工具注册中心

提供统一的工具接口，用于论文知识库系统的各种工具调用。
"""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import json
import traceback


class BaseTool(ABC):
    """工具基类"""

    @abstractmethod
    def run(self, params: Dict) -> Dict:
        """
        执行工具

        Args:
            params: 工具参数字典

        Returns:
            包含 'success', 'data', 'error' 键的结果字典
        """
        pass

    def validate(self, params: Dict) -> bool:
        """
        验证参数

        Args:
            params: 待验证的参数

        Returns:
            是否验证通过
        """
        return True

    @abstractmethod
    def get_schema(self) -> Dict:
        """
        获取工具的JSON Schema

        Returns:
            工具的参数schema
        """
        pass


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._schemas: Dict[str, Dict] = {}

    def register_tool(self, name: str, tool: BaseTool) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            tool: 工具实例
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"工具必须继承自BaseTool: {name}")

        self._tools[name] = tool
        self._schemas[name] = tool.get_schema()

    def execute(self, name: str, params: Dict) -> Dict:
        """
        执行工具

        Args:
            name: 工具名称
            params: 工具参数

        Returns:
            执行结果字典
        """
        # 检查工具是否存在
        if name not in self._tools:
            return {
                "success": False,
                "error": f"工具未注册: {name}",
                "data": None
            }

        # 参数验证
        tool = self._tools[name]
        if not tool.validate(params):
            return {
                "success": False,
                "error": f"参数验证失败: {name}",
                "data": None
            }

        # 执行工具
        try:
            result = tool.run(params)
            return {
                "success": True,
                "data": result,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"执行错误: {str(e)}",
                "data": None,
                "traceback": traceback.format_exc()
            }

    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def get_schema(self, name: str) -> Optional[Dict]:
        """
        获取工具的schema

        Args:
            name: 工具名称

        Returns:
            工具的JSON Schema，如果不存在返回None
        """
        return self._schemas.get(name)

    def get_all_schemas(self) -> Dict[str, Dict]:
        """
        获取所有工具的schema

        Returns:
            工具名称到schema的映射
        """
        return self._schemas.copy()

    def validate_params(self, name: str, params: Dict) -> bool:
        """
        验证工具参数

        Args:
            name: 工具名称
            params: 待验证的参数

        Returns:
            是否验证通过
        """
        if name not in self._tools:
            return False

        return self._tools[name].validate(params)

    def unregister_tool(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            是否成功注销
        """
        if name in self._tools:
            del self._tools[name]
            del self._schemas[name]
            return True
        return False


# ===== 工具实现 =====

class VectorSearchTool(BaseTool):
    """向量检索工具"""

    def __init__(self):
        self.searcher = None

    def _get_searcher(self):
        """延迟加载搜索器"""
        if self.searcher is None:
            import sys
            sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
            from search import HybridSearcher
            self.searcher = HybridSearcher(use_bge=True)
        return self.searcher

    def get_schema(self) -> Dict:
        return {
            "name": "vector_search",
            "description": "基于向量的语义检索工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询文本"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }

    def validate(self, params: Dict) -> bool:
        return "query" in params and isinstance(params["query"], str)

    def run(self, params: Dict) -> Dict:
        query = params["query"]
        top_k = params.get("top_k", 10)

        searcher = self._get_searcher()
        result = searcher.vector_search(query, top_k=top_k)

        return {
            "results": result,
            "query": query,
            "count": len(result)
        }


class BM25SearchTool(BaseTool):
    """BM25关键词检索工具"""

    def __init__(self):
        self.searcher = None

    def _get_searcher(self):
        """延迟加载搜索器"""
        if self.searcher is None:
            import sys
            sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
            from search import HybridSearcher
            self.searcher = HybridSearcher(use_bge=True)
        return self.searcher

    def get_schema(self) -> Dict:
        return {
            "name": "bm25_search",
            "description": "基于BM25算法的关键词检索工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询文本"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }

    def validate(self, params: Dict) -> bool:
        return "query" in params and isinstance(params["query"], str)

    def run(self, params: Dict) -> Dict:
        query = params["query"]
        top_k = params.get("top_k", 10)

        searcher = self._get_searcher()
        result = searcher.bm25_search(query, top_k=top_k)

        return {
            "results": result,
            "query": query,
            "count": len(result)
        }


class HybridSearchTool(BaseTool):
    """混合检索工具（向量 + BM25 + RRF融合）"""

    def __init__(self):
        self.searcher = None

    def _get_searcher(self):
        """延迟加载搜索器"""
        if self.searcher is None:
            import sys
            sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
            from search import HybridSearcher
            self.searcher = HybridSearcher(use_bge=True)
        return self.searcher

    def get_schema(self) -> Dict:
        return {
            "name": "hybrid_search",
            "description": "混合检索：向量检索 + BM25 + RRF融合",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询文本"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }

    def validate(self, params: Dict) -> bool:
        return "query" in params and isinstance(params["query"], str)

    def run(self, params: Dict) -> Dict:
        query = params["query"]
        top_k = params.get("top_k", 10)

        searcher = self._get_searcher()
        result = searcher.search(query, top_k=top_k)

        return result


class TableExtractTool(BaseTool):
    """表格提取工具 - 从文本中提取表格结构"""

    def get_schema(self) -> Dict:
        return {
            "name": "table_extract",
            "description": "从文本中提取表格结构",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "包含表格的文本"
                    },
                    "format": {
                        "type": "string",
                        "description": "输出格式：markdown/html/json",
                        "default": "json"
                    }
                },
                "required": ["text"]
            }
        }

    def validate(self, params: Dict) -> bool:
        return "text" in params and isinstance(params["text"], str)

    def run(self, params: Dict) -> Dict:
        text = params["text"]
        output_format = params.get("format", "json")

        # 简单的表格提取逻辑
        tables = self._extract_tables(text)

        if output_format == "markdown":
            result = self._to_markdown(tables)
        elif output_format == "html":
            result = self._to_html(tables)
        else:
            result = tables

        return {
            "tables": result,
            "count": len(tables)
        }

    def _extract_tables(self, text: str) -> List[Dict]:
        """提取表格"""
        tables = []
        lines = text.split('\n')
        current_table = None
        headers = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测表格分隔符
            if '|' in line and ('---' in line or '—' in line):
                continue

            # 检测表格行
            if '|' in line:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if headers is None:
                    headers = cells
                    current_table = {"headers": headers, "rows": []}
                else:
                    if current_table:
                        current_table["rows"].append(cells)

            elif current_table and current_table["rows"]:
                tables.append(current_table)
                current_table = None
                headers = None

        if current_table and current_table["rows"]:
            tables.append(current_table)

        return tables

    def _to_markdown(self, tables: List[Dict]) -> str:
        """转换为markdown"""
        result = []
        for table in tables:
            # 表头
            result.append("| " + " | ".join(table["headers"]) + " |")
            # 分隔符
            result.append("| " + " | ".join(["---"] * len(table["headers"])) + " |")
            # 数据行
            for row in table["rows"]:
                result.append("| " + " | ".join(row) + " |")
            result.append("")
        return "\n".join(result)

    def _to_html(self, tables: List[Dict]) -> str:
        """转换为HTML"""
        result = ['<table>']
        for table in tables:
            result.append('<thead><tr>')
            for h in table["headers"]:
                result.append(f'<th>{h}</th>')
            result.append('</tr></thead>')
            result.append('<tbody>')
            for row in table["rows"]:
                result.append('<tr>')
                for cell in row:
                    result.append(f'<td>{cell}</td>')
                result.append('</tr>')
            result.append('</tbody>')
        result.append('</table>')
        return '\n'.join(result)


class CitationCheckTool(BaseTool):
    """引用验证工具 - 验证答案中的引用是否有效"""

    def get_schema(self) -> Dict:
        return {
            "name": "citation_check",
            "description": "验证答案中的引用是否有效",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "待验证的答案文本"
                    },
                    "contexts": {
                        "type": "array",
                        "description": "检索到的上下文列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "chunk_id": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["answer", "contexts"]
            }
        }

    def validate(self, params: Dict) -> bool:
        return "answer" in params and "contexts" in params

    def run(self, params: Dict) -> Dict:
        answer = params["answer"]
        contexts = params["contexts"]

        # 提取答案中的引用标记
        citations = self._extract_citations(answer)

        # 验证每个引用
        validated = []
        for cite in citations:
            is_valid, source = self._validate_citation(cite, contexts)
            validated.append({
                "citation": cite,
                "valid": is_valid,
                "source": source
            })

        # 计算引用准确率
        valid_count = sum(1 for v in validated if v["valid"])
        accuracy = valid_count / len(validated) if validated else 1.0

        return {
            "citations": validated,
            "total": len(validated),
            "valid_count": valid_count,
            "accuracy": accuracy,
            "has_unverified": accuracy < 1.0
        }

    def _extract_citations(self, text: str) -> List[str]:
        """提取引用标记"""
        import re
        # 匹配 [1], [2], 等引用格式
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, text)
        return list(set(matches))

    def _validate_citation(self, cite: str, contexts: List[Dict]) -> tuple:
        """验证单个引用"""
        try:
            idx = int(cite) - 1
            if 0 <= idx < len(contexts):
                return True, contexts[idx].get("chunk_id", "")
        except (ValueError, IndexError):
            pass
        return False, None


class HallucinationDetectTool(BaseTool):
    """幻觉检测工具 - 检测答案是否包含幻觉内容"""

    def get_schema(self) -> Dict:
        return {
            "name": "hallucination_detect",
            "description": "检测答案是否包含幻觉内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "待检测的答案文本"
                    },
                    "contexts": {
                        "type": "array",
                        "description": "支撑上下文列表",
                        "items": {
                            "type": "string"
                        }
                    },
                    "threshold": {
                        "type": "number",
                        "description": "判定阈值",
                        "default": 0.7
                    }
                },
                "required": ["answer", "contexts"]
            }
        }

    def validate(self, params: Dict) -> bool:
        return "answer" in params and "contexts" in params

    def run(self, params: Dict) -> Dict:
        answer = params["answer"]
        contexts = params["contexts"]
        threshold = params.get("threshold", 0.7)

        # 简化的幻觉检测实现
        # 1. 检查答案中的实体是否出现在上下文中
        answer_entities = self._extract_entities(answer)
        context_text = " ".join(contexts)

        supported_entities = []
        hallucinated_entities = []

        for entity in answer_entities:
            if entity.lower() in context_text.lower():
                supported_entities.append(entity)
            else:
                hallucinated_entities.append(entity)

        # 计算支持率
        total = len(answer_entities)
        support_rate = len(supported_entities) / total if total > 0 else 1.0

        # 2. 检查答案长度是否合理
        answer_length = len(answer)
        context_length = sum(len(c) for c in contexts)
        length_ratio = answer_length / context_length if context_length > 0 else 1.0

        is_hallucination = support_rate < threshold or length_ratio > 3.0

        return {
            "is_hallucination": is_hallucination,
            "support_rate": support_rate,
            "threshold": threshold,
            "supported_entities": supported_entities,
            "hallucinated_entities": hallucinated_entities,
            "length_ratio": length_ratio,
            "risk_level": self._get_risk_level(support_rate)
        }

    def _extract_entities(self, text: str) -> List[str]:
        """提取实体（简化版：提取大写开头的词组）"""
        import re
        # 提取大写开头的词组
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        matches = re.findall(pattern, text)
        # 过滤常见词
        stop_words = {"The", "This", "That", "A", "An", "In", "On", "At", "To", "For", "Of", "With", "By"}
        return [m for m in matches if m not in stop_words]

    def _get_risk_level(self, support_rate: float) -> str:
        """获取风险等级"""
        if support_rate >= 0.9:
            return "low"
        elif support_rate >= 0.7:
            return "medium"
        else:
            return "high"


class PythonExecTool(BaseTool):
    """Python执行工具 - 安全地执行Python代码"""

    def __init__(self, timeout: int = 10, memory_limit: int = 50 * 1024 * 1024):
        self.timeout = timeout
        self.memory_limit = memory_limit

    def get_schema(self) -> Dict:
        return {
            "name": "python_exec",
            "description": "安全地执行Python代码",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "待执行的Python代码"
                    },
                    "globals": {
                        "type": "object",
                        "description": "全局变量上下文",
                        "default": {}
                    },
                    "locals": {
                        "type": "object",
                        "description": "局部变量上下文",
                        "default": {}
                    }
                },
                "required": ["code"]
            }
        }

    def validate(self, params: Dict) -> bool:
        if "code" not in params:
            return False
        code = params["code"]
        # 简单的安全检查
        dangerous_patterns = ["import os", "import sys", "import subprocess", "open(", "__import__", "eval("]
        for pattern in dangerous_patterns:
            if pattern in code:
                return False
        return True

    def run(self, params: Dict) -> Dict:
        code = params["code"]
        globals_ctx = params.get("globals", {})
        locals_ctx = params.get("locals", {})

        import io
        import sys

        # 捕获输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # 执行代码
            exec(code, globals_ctx, locals_ctx)

            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            return {
                "success": True,
                "stdout": stdout_output,
                "stderr": stderr_output,
                "locals": {k: str(v) for k, v in locals_ctx.items() if not k.startswith('_')}
            }

        except Exception as e:
            return {
                "success": False,
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "error": str(e),
                "error_type": type(e).__name__
            }

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


# ===== 创建默认注册中心 =====

def create_default_registry() -> ToolRegistry:
    """
    创建默认的工具注册中心

    Returns:
        包含所有标准工具的注册中心
    """
    registry = ToolRegistry()

    # 注册所有工具
    registry.register_tool("vector_search", VectorSearchTool())
    registry.register_tool("bm25_search", BM25SearchTool())
    registry.register_tool("hybrid_search", HybridSearchTool())
    registry.register_tool("table_extract", TableExtractTool())
    registry.register_tool("citation_check", CitationCheckTool())
    registry.register_tool("hallucination_detect", HallucinationDetectTool())
    registry.register_tool("python_exec", PythonExecTool())

    return registry


if __name__ == "__main__":
    # 测试ToolRegistry
    registry = create_default_registry()

    print("已注册的工具:", registry.list_tools())

    # 测试向量检索
    result = registry.execute("vector_search", {"query": "MCP协议", "top_k": 3})
    print("\n向量检索结果:")
    print(f"成功: {result['success']}")
    if result['success']:
        print(f"返回数量: {result['data']['count']}")

    # 测试参数验证
    is_valid = registry.validate_params("vector_search", {"query": "test"})
    print(f"\n参数验证: {is_valid}")

    # 测试错误处理
    result = registry.execute("nonexistent_tool", {"query": "test"})
    print(f"\n错误处理: {result['error']}")
