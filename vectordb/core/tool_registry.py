"""
ToolRegistry - 统一工具注册中心

提供统一的工具接口，用于论文知识库系统的各种工具调用。

设计意图：
    实现工具的统一注册和执行，遵循"单一接口原则"：
    1. 所有工具通过BaseTool抽象类统一接口
    2. 执行结果通过统一格式（success/data/error）返回
    3. 工具参数通过JSON Schema标准化

核心架构：
    - BaseTool: 抽象基类，定义run/validate/get_schema三个核心方法
    - ToolRegistry: 注册中心，管理工具的生命周期
    - 工具实现: 7个专用工具类，覆盖检索、分析、验证、执行场景

使用场景：
    - Agent调用工具时的统一入口
    - 工具的动态注册和卸载
    - 参数验证和错误处理

Example:
    registry = create_default_registry()
    result = registry.execute("hybrid_search", {"query": "MCP协议", "top_k": 10})
"""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import json
import traceback


class BaseTool(ABC):
    """
    工具基类 - 所有工具的统一接口

    设计意图: 定义工具的标准接口，确保所有工具具有统一的调用方式和
    结果格式，便于上层Agent统一处理。

    核心方法：
        - run(): 执行工具逻辑，返回结果
        - validate(): 参数验证，防止无效输入
        - get_schema(): JSON Schema定义，用于参数校验和文档生成

    输入输出规范：
        输入: params字典，参数内容由具体工具定义
        输出: run()返回工具特定结果，execute()包装为统一格式

    Example:
        class MyTool(BaseTool):
            def run(self, params):
                return {"result": params["input"]}
            def get_schema(self):
                return {"name": "my_tool", "parameters": {...}}
    """

    @abstractmethod
    def run(self, params: Dict) -> Dict:
        """
        执行工具

        设计意图: 工具的核心执行逻辑，由子类实现
        Args:
            params: 工具参数字典，内容由具体工具定义
        Returns:
            工具特定结果（由ToolRegistry.execute包装为统一格式）
        """
        pass

    def validate(self, params: Dict) -> bool:
        """
        验证参数

        设计意图: 防止无效参数进入执行流程，提前发现错误
        Args:
            params: 待验证的参数
        Returns:
            是否验证通过（默认返回True，子类可覆写实现具体验证）
        Note:
            基类提供默认实现，复杂验证逻辑由子类覆写
        """
        return True

    @abstractmethod
    def get_schema(self) -> Dict:
        """
        获取工具的JSON Schema

        设计意图: 标准化工具参数定义，支持参数校验和文档生成
        Returns:
            工具的参数schema，遵循OpenAI/Anthropic工具定义格式
        Example:
            {
                "name": "hybrid_search",
                "description": "混合检索工具",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "查询文本"}
                    },
                    "required": ["query"]
                }
            }
        """
        pass


class ToolRegistry:
    """
    工具注册中心 - 管理工具的生命周期

    设计意图: 统一管理所有工具的注册、执行、注销，提供单一入口点
    输入:
        - register_tool(): 工具名称 + BaseTool实例
        - execute(): 工具名称 + 参数字典
    输出:
        - execute(): 统一格式结果 {"success": bool, "data": any, "error": str}

    核心功能：
        1. 工具注册：检查类型并存储到内部字典
        2. 工具执行：验证参数、调用run()、包装结果
        3. 工具查询：列出工具、获取schema、验证参数
        4. 工具注销：从字典移除工具和schema

    错误处理：
        - 工具不存在：返回 {"success": False, "error": "工具未注册"}
        - 参数验证失败：返回 {"success": False, "error": "参数验证失败"}
        - 执行异常：捕获并返回 {"success": False, "error": "执行错误", "traceback": ...}

    Example:
        registry = ToolRegistry()
        registry.register_tool("search", VectorSearchTool())
        result = registry.execute("search", {"query": "test"})
    """

    def __init__(self):
        # 内部存储：工具实例和schema分别存储，便于快速查询
        self._tools: Dict[str, BaseTool] = {}
        self._schemas: Dict[str, Dict] = {}

    def register_tool(self, name: str, tool: BaseTool) -> None:
        """
        注册工具

        设计意图: 将工具添加到注册中心，供后续调用
        Args:
            name: 工具名称，唯一标识，用于execute调用
            tool: 工具实例，必须继承自BaseTool
        Raises:
            TypeError: 如果工具不继承自BaseTool
        Side Effects:
            - 存储工具实例到_tools字典
            - 存储工具schema到_schemas字典
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"工具必须继承自BaseTool: {name}")

        self._tools[name] = tool
        self._schemas[name] = tool.get_schema()

    def execute(self, name: str, params: Dict) -> Dict:
        """
        执行工具

        设计意图: 工具执行的统一入口，处理验证、调用、错误包装
        Args:
            name: 工具名称
            params: 工具参数
        Returns:
            执行结果字典，统一格式:
            {
                "success": True/False,
                "data": 工具返回结果（成功时）,
                "error": 错误信息（失败时）,
                "traceback": 异常堆栈（执行错误时）
            }

        执行流程：
            1. 检查工具是否存在
            2. 调用validate()验证参数
            3. 调用run()执行工具
            4. 包装结果为统一格式
            5. 异常时捕获并返回错误信息
        """
        # 检查工具是否存在 - 防止调用未注册工具
        if name not in self._tools:
            return {
                "success": False,
                "error": f"工具未注册: {name}",
                "data": None
            }

        # 参数验证 - 提前发现无效参数
        tool = self._tools[name]
        if not tool.validate(params):
            return {
                "success": False,
                "error": f"参数验证失败: {name}",
                "data": None
            }

        # 执行工具 - 捕获所有异常，确保不会崩溃
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
                "traceback": traceback.format_exc()  # 保留堆栈用于调试
            }

    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具

        设计意图: 提供工具清单，用于Agent决策或用户展示
        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def get_schema(self, name: str) -> Optional[Dict]:
        """
        获取工具的schema

        设计意图: 获取单个工具的参数定义，用于参数校验或文档展示
        Args:
            name: 工具名称
        Returns:
            工具的JSON Schema，如果不存在返回None
        """
        return self._schemas.get(name)

    def get_all_schemas(self) -> Dict[str, Dict]:
        """
        获取所有工具的schema

        设计意图: 批量获取所有schema，用于LLM工具调用或文档生成
        Returns:
            工具名称到schema的映射字典
        Note:
            返回副本，避免外部修改影响内部状态
        """
        return self._schemas.copy()

    def validate_params(self, name: str, params: Dict) -> bool:
        """
        验证工具参数

        设计意图: 单独验证参数，用于前端校验或提前提示用户
        Args:
            name: 工具名称
            params: 待验证的参数
        Returns:
            是否验证通过
        Note:
            工具不存在时返回False
        """
        if name not in self._tools:
            return False

        return self._tools[name].validate(params)

    def unregister_tool(self, name: str) -> bool:
        """
        注销工具

        设计意图: 从注册中心移除工具，用于动态更新或测试清理
        Args:
            name: 工具名称
        Returns:
            是否成功注销（工具不存在时返回False）
        Side Effects:
            - 从_tools和_schemas字典移除工具
        """
        if name in self._tools:
            del self._tools[name]
            del self._schemas[name]
            return True
        return False


# ===== 工具实现 =====
# 7个专用工具实现，覆盖论文知识库的核心功能

class VectorSearchTool(BaseTool):
    """
    向量检索工具 - 基于语义相似度的检索

    设计意图: 使用向量相似度进行语义检索，适合模糊查询和概念关联
    输入: query（查询文本）, top_k（返回数量）
    输出: 检索结果列表，包含content、score、paper_id等字段

    实现细节:
        - 延迟加载HybridSearcher，避免启动时依赖
        - 调用HybridSearcher.vector_search()方法
        - 使用BGE-M3模型生成embedding

    使用场景:
        - 用户模糊查询（如"注意力机制的原理"）
        - 跨论文概念关联检索
    """

    def __init__(self):
        self.searcher = None  # 延迟加载，避免启动时初始化耗时资源

    def _get_searcher(self):
        """
        延迟加载搜索器

        设计意图: 避免启动时加载重型资源，按需初始化
        Returns:
            HybridSearcher实例
        Side Effects:
            - 首次调用时初始化searcher并缓存
        """
        if self.searcher is None:
            import sys
            sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
            from search import HybridSearcher
            self.searcher = HybridSearcher(use_bge=True)  # 使用BGE-M3模型
        return self.searcher

    def get_schema(self) -> Dict:
        """返回JSON Schema定义"""
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
        """验证参数：必须有query字段且为字符串"""
        return "query" in params and isinstance(params["query"], str)

    def run(self, params: Dict) -> Dict:
        """执行向量检索"""
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
    """
    BM25关键词检索工具 - 基于词频的精准检索

    设计意图: 使用BM25算法进行关键词匹配，适合精确查询和术语检索
    输入: query（查询文本）, top_k（返回数量）
    输出: 检索结果列表，包含content、score、paper_id等字段

    实现细节:
        - 延迟加载HybridSearcher
        - 调用HybridSearcher.bm25_search()方法
        - BM25基于词频和文档长度计算相关性

    使用场景:
        - 用户精确查询（如"Transformer架构"）
        - 特定术语检索
    """

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
        """执行BM25检索"""
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
    """
    混合检索工具 - 向量 + BM25 + RRF融合

    设计意图: 结合向量语义检索和BM25关键词检索的优势，使用RRF算法融合结果
    输入: query（查询文本）, top_k（返回数量）
    输出: 融合后的检索结果列表，包含rrf_score融合评分

    实现细节:
        - 同时执行vector_search和bm25_search
        - 使用RRF（Reciprocal Rank Fusion）算法合并结果
        - rrf_score反映两种检索方法的综合排名

    使用场景:
        - 默认检索方式，兼顾语义和关键词匹配
        - 复杂查询场景（既有概念又有术语）
    """

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
        """执行混合检索"""
        query = params["query"]
        top_k = params.get("top_k", 10)

        searcher = self._get_searcher()
        result = searcher.search(query, top_k=top_k)

        return result


class TableExtractTool(BaseTool):
    """
    表格提取工具 - 从文本中提取表格结构

    设计意图: 解析文本中的表格数据，转换为结构化格式，便于后续处理
    输入: text（包含表格的文本）, format（输出格式：markdown/html/json）
    输出: tables列表，包含headers和rows字段

    实现细节:
        - 使用分隔符'|'识别表格行
        - 第一行作为表头，后续行作为数据
        - 支持三种输出格式：JSON结构、Markdown表格、HTML表格

    使用场景:
        - 论文表格数据提取
        - Markdown表格转换
    """

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
        """执行表格提取"""
        text = params["text"]
        output_format = params.get("format", "json")

        # 简单的表格提取逻辑 - 基于分隔符'|'识别
        tables = self._extract_tables(text)

        # 根据格式转换输出
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
        """
        提取表格 - 基于分隔符识别

        设计意图: 从文本中解析Markdown风格表格
        Args:
            text: 包含表格的文本
        Returns:
            表格列表，每个表格包含headers和rows
        """
        tables = []
        lines = text.split('\n')
        current_table = None
        headers = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测表格分隔符 - Markdown表格的分隔行（如 |---|---|）
            if '|' in line and ('---' in line or '—' in line):
                continue

            # 检测表格行 - 包含'|'分隔符的行
            if '|' in line:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if headers is None:
                    # 第一行作为表头
                    headers = cells
                    current_table = {"headers": headers, "rows": []}
                else:
                    # 后续行作为数据行
                    if current_table:
                        current_table["rows"].append(cells)

            # 非表格行，结束当前表格
            elif current_table and current_table["rows"]:
                tables.append(current_table)
                current_table = None
                headers = None

        # 处理最后一个表格
        if current_table and current_table["rows"]:
            tables.append(current_table)

        return tables

    def _to_markdown(self, tables: List[Dict]) -> str:
        """转换为markdown格式"""
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
        """转换为HTML格式"""
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
    """
    引用验证工具 - 验证答案中的引用是否有效

    设计意图: 检查生成的答案中的引用标记是否对应有效的上下文，防止虚假引用
    输入: answer（待验证的答案文本）, contexts（检索到的上下文列表）
    输出: 引用验证结果，包含valid_count、accuracy、has_unverified字段

    实现细节:
        - 提取答案中的引用标记（如[1]、[2]）
        - 验证每个引用是否对应有效的上下文索引
        - 计算引用准确率

    使用场景:
        - RAG系统质量验证
        - 幻觉检测的补充验证
    """

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
        """执行引用验证"""
        answer = params["answer"]
        contexts = params["contexts"]

        # 提取答案中的引用标记 - 匹配[1]、[2]等格式
        citations = self._extract_citations(answer)

        # 验证每个引用是否对应有效上下文
        validated = []
        for cite in citations:
            is_valid, source = self._validate_citation(cite, contexts)
            validated.append({
                "citation": cite,
                "valid": is_valid,
                "source": source
            })

        # 计算引用准确率 - 有效引用数 / 总引用数
        valid_count = sum(1 for v in validated if v["valid"])
        accuracy = valid_count / len(validated) if validated else 1.0

        return {
            "citations": validated,
            "total": len(validated),
            "valid_count": valid_count,
            "accuracy": accuracy,
            "has_unverified": accuracy < 1.0  # 是否存在未验证引用
        }

    def _extract_citations(self, text: str) -> List[str]:
        """
        提取引用标记

        设计意图: 从文本中识别引用编号，如[1]、[2]
        Args:
            text: 待提取的文本
        Returns:
            引用编号列表（去重）
        """
        import re
        # 匹配 [1], [2], 等引用格式 - 学术写作常见格式
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, text)
        return list(set(matches))

    def _validate_citation(self, cite: str, contexts: List[Dict]) -> tuple:
        """
        防止虚假引用：验证单个引用

        设计意图: 检查引用编号是否对应有效的上下文索引
        Args:
            cite: 引用编号（如"1"）
            contexts: 上下文列表
        Returns:
            (is_valid, source_chunk_id)
        """
        try:
            idx = int(cite) - 1  # 引用编号从1开始，索引从0开始
            if 0 <= idx < len(contexts):
                return True, contexts[idx].get("chunk_id", "")
        except (ValueError, IndexError):
            pass
        return False, None


class HallucinationDetectTool(BaseTool):
    """
    幻觉检测工具 - 检测答案是否包含幻觉内容

    设计意图: 验证生成的答案是否基于真实的检索上下文，防止LLM虚构信息
    输入: answer（待检测的答案）, contexts（支撑上下文）, threshold（判定阈值）
    输出: 幻觉检测结果，包含is_hallucination、support_rate、risk_level字段

    实现细节:
        1. 提取答案中的实体（大写词组、技术术语）
        2. 检查实体是否出现在上下文中
        3. 计算支持率（supported_entities / total_entities）
        4. 根据阈值判定是否幻觉

    使用场景:
        - RAG系统质量验证的核心组件
        - 与引用验证配合使用
    """

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
                        "description": "判定阈值（推荐0.8以上）",
                        "default": 0.8
                    }
                },
                "required": ["answer", "contexts"]
            }
        }

    def validate(self, params: Dict) -> bool:
        return "answer" in params and "contexts" in params

    def run(self, params: Dict) -> Dict:
        """执行幻觉检测"""
        answer = params["answer"]
        contexts = params["contexts"]
        threshold = params.get("threshold", 0.8)

        # 增强的幻觉检测实现
        # 1. 检查答案中的实体是否出现在上下文中
        answer_entities = self._extract_entities(answer)
        context_text = " ".join(contexts)

        supported_entities = []
        hallucinated_entities = []

        for entity in answer_entities:
            # 更严格的匹配：实体必须完整出现在上下文中
            if self._entity_in_context(entity, context_text):
                supported_entities.append(entity)
            else:
                hallucinated_entities.append(entity)

        # 计算支持率 - 支撑实体数 / 总实体数
        total = len(answer_entities)
        support_rate = len(supported_entities) / total if total > 0 else 1.0

        # 2. 检查答案长度是否合理 - 防止过度扩展
        answer_length = len(answer)
        context_length = sum(len(c) for c in contexts)
        length_ratio = answer_length / context_length if context_length > 0 else 1.0

        # 判定幻觉：支持率低于阈值 或 答案长度异常扩展
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
        """
        提取实体（增强版）

        设计意图: 从文本中识别可能虚构的实体，包括大写词组和技术术语
        Args:
            text: 待提取的文本
        Returns:
            实体列表（去重）
        """
        import re
        # 提取大写开头的词组 - 可能是专有名词或技术术语
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        matches = re.findall(pattern, text)
        # 过滤常见词 - 防误判常用词为实体
        stop_words = {
            "The", "This", "That", "A", "An", "In", "On", "At", "To", "For",
            "Of", "With", "By", "And", "Or", "But", "If", "Then", "When"
        }
        entities = [m for m in matches if m not in stop_words]

        # 增加技术术语提取 - 包含数字和特殊字符的术语（如API-123）
        tech_pattern = r'\b([A-Z][A-Z0-9\-]+)\b'
        tech_matches = re.findall(tech_pattern, text)
        entities.extend([m for m in tech_matches if len(m) > 2])

        return list(set(entities))

    def _entity_in_context(self, entity: str, context: str) -> bool:
        """
        检查实体是否完整出现在上下文中

        设计意图: 精确匹配实体，避免部分匹配误判
        Args:
            entity: 待检查的实体
            context: 上下文文本
        Returns:
            是否出现
        """
        # 精确匹配（忽略大小写）- 防止大小写差异误判
        return entity.lower() in context.lower()

    def _get_risk_level(self, support_rate: float) -> str:
        """
        获取风险等级

        设计意图: 将支持率转换为风险等级，便于用户理解
        Args:
            support_rate: 支持率
        Returns:
            risk_level: low/medium/high
        """
        if support_rate >= 0.95:
            return "low"
        elif support_rate >= 0.8:
            return "medium"
        else:
            return "high"


class PythonExecTool(BaseTool):
    """
    Python执行工具 - 安全地执行Python代码

    设计意图: 在隔离环境中执行Python代码，用于代码复现和测试验证
    输入: code（Python代码）, globals/locals（可选上下文）
    输出: 执行结果，包含success、stdout、stderr、locals字段

    安全措施:
        1. 禁止导入os、sys、subprocess等危险模块
        2. 禁止使用open()、__import__、eval()等危险函数
        3. 捕获stdout/stderr，避免输出泄露

    使用场景:
        - 论文代码复现验证
        - 公式计算测试
    """

    def __init__(self, timeout: int = 10, memory_limit: int = 50 * 1024 * 1024):
        """
        初始化Python执行工具

        Args:
            timeout: 执行超时时间（秒）
            memory_limit: 内存限制（字节）
        Note:
            timeout和memory_limit当前为预留参数，实际限制未实现
        """
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
        """
        验证参数 - 安全检查

        设计意图: 防止执行危险代码，保护系统安全
        """
        if "code" not in params:
            return False
        code = params["code"]
        # 简单的安全检查 - 禁止导入危险模块和使用危险函数
        dangerous_patterns = ["import os", "import sys", "import subprocess", "open(", "__import__", "eval("]
        for pattern in dangerous_patterns:
            if pattern in code:
                return False
        return True

    def run(self, params: Dict) -> Dict:
        """
        执行Python代码

        设计意图: 在隔离环境中执行代码，捕获输出和错误
        """
        code = params["code"]
        globals_ctx = params.get("globals", {})
        locals_ctx = params.get("locals", {})

        import io
        import sys

        # 捕获输出 - 重定向stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # 执行代码 - 使用exec函数
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
            # 恢复stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr


# ===== 创建默认注册中心 =====

def create_default_registry() -> ToolRegistry:
    """
    创建默认的工具注册中心

    设计意图: 提供预配置的工具集，简化系统初始化
    Returns:
        包含所有标准工具的注册中心（7个工具）
    Example:
        registry = create_default_registry()
        result = registry.execute("hybrid_search", {"query": "MCP协议"})
    """
    registry = ToolRegistry()

    # 注册所有工具 - 7个核心工具
    registry.register_tool("vector_search", VectorSearchTool())
    registry.register_tool("bm25_search", BM25SearchTool())
    registry.register_tool("hybrid_search", HybridSearchTool())
    registry.register_tool("table_extract", TableExtractTool())
    registry.register_tool("citation_check", CitationCheckTool())
    registry.register_tool("hallucination_detect", HallucinationDetectTool())
    registry.register_tool("python_exec", PythonExecTool())

    return registry


if __name__ == "__main__":
    # 测试ToolRegistry - 验证工具注册和执行功能
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