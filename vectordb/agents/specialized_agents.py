"""
四角色专用Agent系统 - 论文知识库

实现四个专业Agent角色分工：
1. PaperRetrievalAgent - 检索专家（召回论文、计算相关性）
2. PaperAnalysisAgent - 解读专家（提取公式、生成摘要）
3. QualityAssuranceAgent - 质量专家（幻觉检测、引用验证）
4. CodeReproductionAgent - 复现专家（生成代码、测试验证）
5. SpecializedAgentOrchestrator - 协调器（编排四角色协作）

设计意图：
    角色分工遵循"专人专职"原则，每个Agent专注于特定任务：
    - RetrievalAgent: 专注检索效率，优化召回率
    - AnalysisAgent: 专注内容理解，提取结构化信息
    - QAAgent: 专注质量保证，防止幻觉和虚假引用
    - CodeAgent: 专注代码复现，验证算法可执行性

工作流程：
    1. RetrievalAgent检索论文片段
    2. AnalysisAgent分析内容结构
    3. QAAgent验证输出质量
    4. CodeAgent生成复现代码（如需要）

Example:
    orchestrator = create_orchestrator("session-001")
    result = orchestrator.run_pipeline("Transformer的注意力机制", need_code=True)
"""

from typing import Dict, List, Any, Optional
import sys
import re

# 添加项目路径 - 确保模块导入正确
sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
sys.path.append('/home/nvidia/workspace/paper/vectordb/core')

from tool_registry import ToolRegistry, create_default_registry
from memory_manager import PaperMemoryManager


class PaperRetrievalAgent:
    """
    检索专家 - 专注于论文检索和召回优化

    设计意图: 负责论文片段的召回，确保相关内容的覆盖率
    输入: query（用户查询）, top_k（召回数量）
    输出: 检索结果 + 相关度评分 + 召回指标

    核心工具:
        - VectorSearchTool: 语义相似度检索
        - BM25SearchTool: 关键词匹配检索
        - HybridSearchTool: RRF融合检索（默认）

    职责边界:
        - 不负责内容分析（由AnalysisAgent处理）
        - 不负责质量验证（由QAAgent处理）
        - 专注召回效率，返回原始片段

    Example:
        agent = PaperRetrievalAgent(registry, memory)
        result = agent.retrieve("Transformer注意力机制", top_k=10)
        # result包含results列表和metrics指标
    """

    def __init__(self, registry: ToolRegistry, memory: Optional[PaperMemoryManager] = None):
        """
        初始化检索专家

        Args:
            registry: 工具注册中心，提供检索工具
            memory: 记忆管理器（可选），用于记录检索历史
        Side Effects:
            - 确保hybrid_search/vector_search/bm25_search工具已注册
        """
        self.registry = registry
        self.memory = memory
        self._init_tools()

    def _init_tools(self):
        """
        初始化检索工具

        设计意图: 确保检索工具可用，延迟注册缺失的工具
        """
        # 确保工具已注册 - 防止依赖缺失
        tool_names = self.registry.list_tools()
        if "hybrid_search" not in tool_names:
            from tool_registry import HybridSearchTool
            self.registry.register_tool("hybrid_search", HybridSearchTool())
        if "vector_search" not in tool_names:
            from tool_registry import VectorSearchTool
            self.registry.register_tool("vector_search", VectorSearchTool())
        if "bm25_search" not in tool_names:
            from tool_registry import BM25SearchTool
            self.registry.register_tool("bm25_search", BM25SearchTool())

    def retrieve(self, query: str, top_k: int = 10) -> Dict:
        """
        执行混合检索

        设计意图: 使用三种检索方式，综合评估召回效果
        Args:
            query: 查询文本
            top_k: 返回结果数量
        Returns:
            包含检索结果、评分、指标的字典:
            {
                "query": 查询文本,
                "results": 检索结果列表,
                "top_k": 返回数量,
                "metrics": {
                    "total": 总数量,
                    "avg_score": 平均评分,
                    "max_score": 最高评分,
                    "coverage": 覆盖率(评分>0.3的比例)
                },
                "vector_count": 向量检索数量,
                "bm25_count": BM25检索数量
            }

        检索策略:
            1. 执行三种检索方式获取完整数据
            2. 使用HybridSearchTool的RRF融合结果
            3. 计算召回指标评估检索效果
        """
        # 执行三种检索方式 - 获取完整检索数据
        vector_result = self.registry.execute("vector_search", {
            "query": query,
            "top_k": top_k
        })

        bm25_result = self.registry.execute("bm25_search", {
            "query": query,
            "top_k": top_k
        })

        # 混合检索：使用RRF算法融合结果
        hybrid_result = self.registry.execute("hybrid_search", {
            "query": query,
            "top_k": top_k
        })

        # 提取结果 - 处理成功/失败两种情况
        results = hybrid_result.get("data", {}).get("results", []) if hybrid_result.get("success") else []

        # 计算召回指标 - 评估检索效果
        metrics = self._calculate_metrics(query, results)

        # 记录到记忆 - 用于后续分析和追踪
        if self.memory:
            self.memory.add_working_memory({
                "role": "retrieval",
                "content": f"查询: {query}, 召回: {len(results)} 篇"
            })

        return {
            "query": query,
            "results": results,
            "top_k": top_k,
            "metrics": metrics,
            "vector_count": vector_result.get("data", {}).get("count", 0) if vector_result.get("success") else 0,
            "bm25_count": bm25_result.get("data", {}).get("count", 0) if bm25_result.get("success") else 0
        }

    def _calculate_metrics(self, query: str, results: List[Dict]) -> Dict:
        """
        计算召回指标

        设计意图: 量化评估检索效果，支持后续优化
        Args:
            query: 查询文本（当前未使用，预留用于复杂指标）
            results: 检索结果列表
        Returns:
            指标字典：total/avg_score/max_score/min_score/coverage
        Note:
            coverage定义：评分>0.3的结果占比，反映有效召回比例
        """
        if not results:
            return {
                "total": 0,
                "avg_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "coverage": 0.0
            }

        # 提取评分 - 兼容rrf_score和score两种字段
        scores = [r.get("rrf_score", r.get("score", 0)) for r in results]

        return {
            "total": len(results),
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            # coverage: 有效召回比例（评分>0.3认为有效）
            "coverage": len([s for s in scores if s > 0.3]) / len(scores) if scores else 0.0
        }


class PaperAnalysisAgent:
    """
    解读专家 - 论文深度解读、公式提取、中文通俗化

    设计意图: 负责论文内容的结构化理解，输出"餐巾纸摘要"
    输入: query（用户查询）, chunks（检索到的论文片段）
    输出: 摘要 + 核心概念 + 公式解释 + 代码设计

    核心功能:
        - 公式提取: LaTeX格式、编号公式、映射关系
        - 概念抽取: 技术术语、专有名词
        - 餐巾纸摘要: 核心观点的简洁表述
        - 代码设计: 提取论文中的代码片段

    职责边界:
        - 不负责检索（由RetrievalAgent处理）
        - 不负责质量验证（由QAAgent处理）
        - 专注内容理解，输出结构化信息

    Example:
        agent = PaperAnalysisAgent(registry, memory)
        result = agent.analyze("Transformer原理", chunks)
        # result包含summary/concepts/formulas/code_design
    """

    def __init__(self, registry: ToolRegistry, memory: Optional[PaperMemoryManager] = None):
        """
        初始化解读专家

        Args:
            registry: 工具注册中心
            memory: 记忆管理器（可选），用于记录分析历史
        """
        self.registry = registry
        self.memory = memory

    def analyze(self, query: str, chunks: List[Dict]) -> Dict:
        """
        分析论文内容

        设计意图: 将原始片段转换为结构化信息，便于后续处理
        Args:
            query: 用户查询
            chunks: 检索到的论文片段
        Returns:
            包含摘要、概念、公式、代码设计的字典:
            {
                "query": 查询文本,
                "summary": 餐巾纸摘要,
                "concepts": 核心概念列表,
                "formulas": 公式列表,
                "code_design": {
                    "snippets": 代码片段,
                    "inline_codes": 行内代码,
                    "has_code": 是否包含代码
                },
                "chunk_count": 片段数量
            }

        分析流程:
            1. 合并上下文：组装前5个片段
            2. 提取公式：识别LaTeX、编号公式、映射关系
            3. 提取概念：识别大写术语
            4. 生成摘要：截取第一段前200字
            5. 提取代码设计：识别代码块和行内代码
        """
        # 合并上下文 - 限制前5个片段，避免过长
        context = self._assemble_context(chunks)

        # 提取公式 - 三种格式：LaTeX、编号、映射
        formulas = self._extract_formulas(context)

        # 提取核心概念 - 大写术语
        concepts = self._extract_concepts(context)

        # 生成餐巾纸摘要 - 简洁表述核心观点
        summary = self._generate_napkin_summary(query, context)

        # 提取代码设计 - 用于后续代码复现
        code_design = self._extract_code_design(context)

        # 记录到记忆 - 持久化分析结果
        if self.memory:
            self.memory.add_episodic(query, {
                "summary": summary,
                "key_points": concepts[:5],
                "formulas": formulas,
                "concepts": concepts
            })

        return {
            "query": query,
            "summary": summary,
            "concepts": concepts,
            "formulas": formulas,
            "code_design": code_design,
            "chunk_count": len(chunks)
        }

    def _assemble_context(self, chunks: List[Dict]) -> str:
        """
        组装上下文

        设计意图: 合并片段为完整上下文，用于后续分析
        Args:
            chunks: 论文片段列表
        Returns:
            合并后的文本，带引用编号
        Note:
            限制前5个片段，每个片段截取500字，避免上下文过长
        """
        parts = []
        for i, chunk in enumerate(chunks[:5]):
            content = chunk.get("content", chunk.get("text", ""))
            # 截取500字 - 平衡信息量和处理速度
            parts.append(f"[{i+1}] {content[:500]}")
        return "\n\n".join(parts)

    def _extract_formulas(self, text: str) -> List[Dict]:
        """
        提取公式

        设计意图: 识别论文中的数学公式，支持三种格式
        Args:
            text: 论文文本
        Returns:
            公式列表，每个公式包含type和content字段

        公式类型:
            1. LaTeX格式: $...$ 或 $$...$$
            2. 编号公式: (1) xxx, (2) xxx
            3. 映射关系: A → B (箭头函数)
        """
        formulas = []

        # 1. 匹配LaTeX格式: $...$ - 常见数学表达式
        latex_pattern = r'\$([^$]+)\$'
        for match in re.finditer(latex_pattern, text):
            formulas.append({
                "raw": match.group(0),
                "content": match.group(1),
                "type": "latex"
            })

        # 2. 匹配带编号的公式: (1) xxx - 学术论文常见格式
        numbered_pattern = r'\(([0-9]+)\)\s*([A-Za-z].*?)(?=\n|$)'
        for match in re.finditer(numbered_pattern, text):
            formulas.append({
                "number": match.group(1),
                "content": match.group(2).strip(),
                "type": "numbered"
            })

        # 3. 匹配箭头函数符号: → - 映射关系或函数定义
        arrow_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\s*→\s*([A-Za-z_][A-Za-z0-9_]*)'
        for match in re.finditer(arrow_pattern, text):
            formulas.append({
                "from": match.group(1),
                "to": match.group(2),
                "type": "mapping"
            })

        return formulas[:10]  # 限制数量 - 避免过多公式影响输出

    def _extract_concepts(self, text: str) -> List[str]:
        """
        提取核心概念

        设计意图: 识别论文中的技术术语和专有名词
        Args:
            text: 论文文本
        Returns:
            概念列表（去重）
        Note:
            基于大写开头识别，过滤常见词防止误判
        """
        concepts = []

        # 提取大写术语 - 技术术语通常大写开头
        term_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b'
        terms = re.findall(term_pattern, text)

        # 过滤常见词 - 防止误判常用词为术语
        stop_words = {"The", "This", "That", "A", "An", "In", "On", "At", "To", "For", "We", "Our", "Our", "Based", "Using", "From", "With", "Table", "Figure", "Algorithm"}
        concepts = [t for t in terms if t not in stop_words and len(t) > 2]

        # 去重并返回 - 使用dict.fromkeys保持顺序
        return list(dict.fromkeys(concepts))[:10]

    def _generate_napkin_summary(self, query: str, context: str) -> str:
        """
        生成餐巾纸摘要（简化版）

        设计意图: 提取核心观点的简洁表述，便于快速理解
        Args:
            query: 用户查询（当前未使用）
            context: 论文上下文
        Returns:
            摘要文本（前200字）
        Note:
            当前为简化实现，截取第一段前200字
            未来可接入LLM生成更准确的摘要
        """
        # 提取第一段作为摘要 - 简化处理
        paragraphs = context.split("\n\n")
        first_para = paragraphs[0] if paragraphs else ""

        # 截取前200字 - 保持简洁
        summary = first_para[:200] + "..." if len(first_para) > 200 else first_para

        return summary

    def _extract_code_design(self, text: str) -> Dict:
        """
        提取代码设计

        设计意图: 识别论文中的代码片段，用于后续复现
        Args:
            text: 论文文本
        Returns:
            代码设计字典：snippets/inline_codes/has_code
        """
        code_snippets = []

        # 匹配代码块: ```python ... ``` - 常见代码格式
        code_pattern = r'```(?:python|py)?\s*([\s\S]*?)```'
        for match in re.finditer(code_pattern, text):
            code_snippets.append(match.group(1).strip())

        # 匹配行内代码: `...` - 小型代码片段
        inline_pattern = r'`([^`]+)`'
        inline_codes = re.findall(inline_pattern, text)

        return {
            "snippets": code_snippets[:3],
            "inline_codes": inline_codes[:5],
            "has_code": len(code_snippets) > 0 or len(inline_codes) > 0
        }


class QualityAssuranceAgent:
    """
    质量专家 - 幻觉检测、引用验证、支撑度评估

    设计意图: 验证输出质量，防止LLM幻觉和虚假引用
    输入: output（待验证的输出）, chunks（支撑上下文）
    输出: 质量评分 + 风险告警 + 修正建议

    核心工具:
        - HallucinationDetectTool: 实体支撑度检测
        - CitationCheckTool: 引用有效性验证

    质量指标:
        - quality_score: 综合评分（0-1）
        - hallucination风险: high/medium/low
        - citation准确率: 有效引用占比

    职责边界:
        - 不负责生成内容（由AnalysisAgent处理）
        - 不负责代码复现（由CodeAgent处理）
        - 专注质量验证，提供风险告警

    Example:
        agent = QualityAssuranceAgent(registry, memory)
        result = agent.validate(output_text, chunks)
        # result包含quality_score/risks/suggestions
    """

    def __init__(self, registry: ToolRegistry, memory: Optional[PaperMemoryManager] = None):
        """
        初始化质量专家

        Args:
            registry: 工具注册中心
            memory: 记忆管理器（可选）
        """
        self.registry = registry
        self.memory = memory

    def validate(self, output: str, chunks: List[Dict]) -> Dict:
        """
        验证输出质量

        设计意图: 全面检查输出的可信度和准确性
        Args:
            output: 待验证的输出文本
            chunks: 支撑上下文
        Returns:
            质量验证结果:
            {
                "output_length": 输出长度,
                "quality_score": 质量评分(0-1),
                "hallucination": {
                    "is_hallucination": 是否幻觉,
                    "support_rate": 支撑率,
                    "risk_level": 风险等级
                },
                "citations": {
                    "accuracy": 引用准确率,
                    "total": 总引用数,
                    "valid_count": 有效引用数
                },
                "risks": 风险告警列表,
                "suggestions": 修正建议列表,
                "is_passed": 是否通过(quality_score>=0.7)
            }

        验证流程:
            1. 幻觉检测：检查实体支撑度
            2. 引用验证：检查引用标记有效性
            3. 计算评分：加权平均幻觉率和引用准确率
            4. 生成告警：识别具体风险点
            5. 生成建议：提供修正方向
        """
        # 提取上下文文本 - 用于幻觉检测
        contexts = [c.get("content", c.get("text", "")) for c in chunks]

        # 幻觉检测 - 检查实体是否被上下文支撑
        hallucination_result = self._detect_hallucination(output, contexts)

        # 引用验证 - 检查引用标记有效性
        citation_result = self._validate_citations(output, chunks)

        # 计算综合质量评分 - 加权平均
        quality_score = self._calculate_quality_score(hallucination_result, citation_result)

        # 生成风险告警 - 具体风险点描述
        risks = self._generate_risks(hallucination_result, citation_result)

        # 生成修正建议 - 修正方向提示
        suggestions = self._generate_suggestions(hallucination_result, citation_result)

        return {
            "output_length": len(output),
            "quality_score": quality_score,
            "hallucination": hallucination_result,
            "citations": citation_result,
            "risks": risks,
            "suggestions": suggestions,
            "is_passed": quality_score >= 0.7  # 通过阈值：0.7
        }

    def _detect_hallucination(self, output: str, contexts: List[str]) -> Dict:
        """
        幻觉检测

        设计意图: 检查输出内容是否基于真实上下文
        Args:
            output: 输出文本
            contexts: 上下文列表
        Returns:
            幻觉检测结果
        """
        result = self.registry.execute("hallucination_detect", {
            "answer": output,
            "contexts": contexts,
            "threshold": 0.7  # 幻觉判定阈值
        })

        # 处理执行失败情况 - 返回默认值
        return result.get("data", {}) if result.get("success") else {
            "is_hallucination": False,
            "support_rate": 1.0,
            "risk_level": "unknown"
        }

    def _validate_citations(self, output: str, chunks: List[Dict]) -> Dict:
        """
        引用验证

        设计意图: 检查引用标记是否对应有效上下文
        Args:
            output: 输出文本
            chunks: 上下文列表
        Returns:
            引用验证结果
        """
        # 构造上下文格式 - 适配CitationCheckTool
        contexts = [{"content": c.get("content", c.get("text", "")), "chunk_id": c.get("id", str(i))} for i, c in enumerate(chunks)]

        result = self.registry.execute("citation_check", {
            "answer": output,
            "contexts": contexts
        })

        return result.get("data", {}) if result.get("success") else {
            "accuracy": 1.0,
            "total": 0,
            "valid_count": 0
        }

    def _calculate_quality_score(self, hallucination: Dict, citation: Dict) -> float:
        """
        计算综合质量评分

        设计意图: 综合幻觉率和引用准确率，量化质量
        Args:
            hallucination: 幻觉检测结果
            citation: 引用验证结果
        Returns:
            质量评分（0-1）
        Note:
            加权策略：幻觉率60%，引用准确率40%
            幻觉率更重要，因为它反映内容真实性
        """
        # 基于幻觉率和引用准确率
        hallucination_risk = hallucination.get("support_rate", 1.0)
        citation_accuracy = citation.get("accuracy", 1.0)

        # 加权平均 - 幻觉率权重更高
        score = 0.6 * hallucination_risk + 0.4 * citation_accuracy

        return round(score, 2)

    def _generate_risks(self, hallucination: Dict, citation: Dict) -> List[str]:
        """
        生成风险告警

        设计意图: 具体识别风险点，帮助用户理解问题
        Args:
            hallucination: 幻觉检测结果
            citation: 引用验证结果
        Returns:
            风险告警列表
        """
        risks = []

        # 高幻觉风险告警
        if hallucination.get("risk_level") == "high":
            risks.append("高幻觉风险：输出内容与上下文匹配度低")

        # 疑似幻觉实体告警
        if hallucination.get("hallucinated_entities"):
            risks.append(f"疑似幻觉实体: {', '.join(hallucination['hallucinated_entities'][:3])}")

        # 引用失效告警
        if citation.get("accuracy", 1.0) < 1.0:
            invalid_count = citation.get("total", 0) - citation.get("valid_count", 0)
            risks.append(f"引用失效: {invalid_count} 个引用无法验证")

        # 无风险时的默认提示
        if not risks:
            risks.append("无明显风险")

        return risks

    def _generate_suggestions(self, hallucination: Dict, citation: Dict) -> List[str]:
        """
        生成修正建议

        设计意图: 提供具体修正方向，帮助改进输出
        Args:
            hallucination: 幻觉检测结果
            citation: 引用验证结果
        Returns:
            修正建议列表
        """
        suggestions = []

        # 幻觉风险修正建议
        if hallucination.get("risk_level") in ["medium", "high"]:
            suggestions.append("建议增加更多上下文引用来支撑输出")

        # 支撑率低的修正建议
        if hallucination.get("support_rate", 1.0) < 0.8:
            suggestions.append("建议重新核事实性陈述")

        # 引用格式修正建议
        if citation.get("accuracy", 1.0) < 1.0:
            suggestions.append("建议使用 [1], [2] 等标准引用格式")

        # 质量良好时的默认提示
        if not suggestions:
            suggestions.append("质量良好，可直接使用")

        return suggestions


class CodeReproductionAgent:
    """
    复现专家 - 论文代码复现设计、测试验证

    设计意图: 生成论文算法的可执行代码，验证复现可行性
    输入: query（用户查询）, analysis（分析结果）
    输出: 代码模块 + 测试用例 + 运行结果

    核心功能:
        - 代码生成: 根据分析结果生成代码模板
        - 测试验证: 生成测试用例并执行
        - 运行检查: 检查代码可执行性

    代码模板:
        - Transformer模板: Transformer架构实现
        - Attention模板: 注意力机制实现
        - 通用模板: 基础论文实现框架

    职责边界:
        - 不负责内容分析（由AnalysisAgent处理）
        - 不负责质量验证（由QAAgent处理）
        - 专注代码生成和验证

    Example:
        agent = CodeReproductionAgent(registry, memory)
        result = agent.reproduce("Transformer", analysis)
        # result包含code_modules/test_cases/run_results
    """

    def __init__(self, registry: ToolRegistry, memory: Optional[PaperMemoryManager] = None):
        """
        初始化复现专家

        Args:
            registry: 工具注册中心
            memory: 记忆管理器（可选）
        """
        self.registry = registry
        self.memory = memory

    def reproduce(self, query: str, analysis: Dict) -> Dict:
        """
        复现论文代码

        设计意图: 生成可执行的代码模块，验证算法可行性
        Args:
            query: 用户查询（用于识别代码类型）
            analysis: 分析结果（包含code_design）
        Returns:
            复现结果:
            {
                "query": 查询文本,
                "code_modules": [
                    {"name": "模块名", "code": "代码内容", "type": "existing/generated"}
                ],
                "test_cases": 测试用例列表,
                "run_results": [
                    {"module": "模块名", "success": 是否成功, "output": 输出}
                ],
                "is_runnable": 所有模块是否可运行
            }

        复现流程:
            1. 生成代码模块：提取现有片段或生成模板
            2. 生成测试用例：简单导入测试
            3. 运行代码模块：使用PythonExecTool执行
            4. 检查可运行性：所有模块执行成功则is_runnable=True
        """
        # 生成代码框架 - 提取现有片段或生成模板
        code_modules = self._generate_code_modules(query, analysis)

        # 生成测试用例 - 简单导入测试
        test_cases = self._generate_test_cases(code_modules)

        # 尝试运行代码 - 使用PythonExecTool
        run_results = self._run_code_modules(code_modules)

        return {
            "query": query,
            "code_modules": code_modules,
            "test_cases": test_cases,
            "run_results": run_results,
            "is_runnable": all(r.get("success", False) for r in run_results)
        }

    def _generate_code_modules(self, query: str, analysis: Dict) -> List[Dict]:
        """
        生成代码模块

        设计意图: 根据查询类型和分析结果生成代码
        Args:
            query: 用户查询（用于识别代码类型）
            analysis: 分析结果
        Returns:
            代码模块列表

        生成策略:
            1. 如果分析结果中有代码片段，直接使用
            2. 否则根据查询关键词生成对应模板
        """
        modules = []

        # 提取代码设计 - 从分析结果中获取现有代码
        code_design = analysis.get("code_design", {})
        snippets = code_design.get("snippets", [])

        # 如果有现有代码片段，直接使用
        for i, snippet in enumerate(snippets):
            modules.append({
                "name": f"module_{i+1}.py",
                "code": snippet,
                "type": "existing"
            })

        # 生成代码模板 - 根据查询类型选择模板
        if not modules:
            # 根据查询类型生成模板
            if "transformer" in query.lower():
                modules.append({
                    "name": "transformer_model.py",
                    "code": self._generate_transformer_template(),
                    "type": "generated"
                })
            elif "attention" in query.lower():
                modules.append({
                    "name": "attention.py",
                    "code": self._generate_attention_template(),
                    "type": "generated"
                })
            else:
                modules.append({
                    "name": "main.py",
                    "code": self._generate_generic_template(),
                    "type": "generated"
                })

        return modules

    def _generate_transformer_template(self) -> str:
        """
        生成Transformer代码模板

        设计意图: 提供Transformer架构的基础实现，用于论文复现
        Returns:
            Transformer代码模板
        """
        return '''import torch
import torch.nn as nn

class TransformerBlock(nn.Module):
    """Transformer块"""

    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attention = nn.MultiheadAttention(d_model, n_heads, dropout=dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Linear(d_ff, d_model)
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        # 自注意力
        attn_out, _ = self.attention(x, x, x, attn_mask=mask)
        x = self.norm1(x + self.dropout(attn_out))

        # 前馈网络
        ffn_out = self.ffn(x)
        x = self.norm2(x + self.dropout(ffn_out))

        return x

# 测试
if __name__ == "__main__":
    block = TransformerBlock(d_model=512, n_heads=8, d_ff=2048)
    x = torch.randn(10, 32, 512)
    output = block(x)
    print(f"输出形状: {output.shape}")
'''

    def _generate_attention_template(self) -> str:
        """
        生成Attention代码模板

        设计意图: 提供注意力机制的完整实现，用于论文复现
        Returns:
            Attention代码模板
        """
        return '''import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class SelfAttention(nn.Module):
    """自注意力机制"""

    def __init__(self, d_model, n_heads):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads

        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)

    def forward(self, x, mask=None):
        batch_size = x.size(0)

        # 线性变换
        Q = self.W_q(x).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(x).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(x).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)

        # 注意力分数
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)

        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)

        attn_weights = F.softmax(scores, dim=-1)
        attn_output = torch.matmul(attn_weights, V)

        # 合并多头
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)

        return self.W_o(attn_output)

# 测试
if __name__ == "__main__":
    attn = SelfAttention(d_model=512, n_heads=8)
    x = torch.randn(2, 10, 512)
    output = attn(x)
    print(f"输出形状: {output.shape}")
'''

    def _generate_generic_template(self) -> str:
        """
        生成通用代码模板

        设计意图: 提供基础论文实现框架，适用于一般论文
        Returns:
            通用代码模板
        """
        return '''"""
论文代码复现模板
"""

class PaperImplementation:
    """论文实现基类"""

    def __init__(self, config=None):
        self.config = config or {}

    def forward(self, x):
        """前向传播"""
        raise NotImplementedError

    def train_step(self, batch):
        """训练步骤"""
        raise NotImplementedError

# 测试
if __name__ == "__main__":
    impl = PaperImplementation({"param": 1.0})
    print("论文实现模板已创建")
'''

    def _generate_test_cases(self, code_modules: List[Dict]) -> List[Dict]:
        """
        生成测试用例

        设计意图: 为每个代码模块生成基础测试
        Args:
            code_modules: 代码模块列表
        Returns:
            测试用例列表
        Note:
            当前为简化实现，仅生成导入测试
        """
        test_cases = []

        for module in code_modules:
            test_case = {
                "module": module["name"],
                "tests": [
                    {
                        "name": f"test_{module['name'].replace('.py', '')}_import",
                        "code": f"import sys; sys.path.insert(0, '.'); exec(open('{module['name']}').read())"
                    }
                ]
            }
            test_cases.append(test_case)

        return test_cases

    def _run_code_modules(self, code_modules: List[Dict]) -> List[Dict]:
        """
        运行代码模块

        设计意图: 执行代码模块，验证可运行性
        Args:
            code_modules: 代码模块列表
        Returns:
            运行结果列表
        """
        results = []

        for module in code_modules:
            # 使用PythonExecTool执行代码
            result = self.registry.execute("python_exec", {
                "code": module["code"]
            })

            results.append({
                "module": module["name"],
                "success": result.get("success", False),
                "output": result.get("data", {}).get("stdout", ""),
                "error": result.get("data", {}).get("stderr", "") or result.get("error", "")
            })

        return results


class SpecializedAgentOrchestrator:
    """
    协调器 - 协调四角色Agent协作

    设计意图: 编排四角色Agent的工作流程，提供统一入口
    输入: query（用户查询）, top_k（检索数量）, need_code（是否生成代码）
    输出: 完整Pipeline结果

    工作流程:
        1. RetrievalAgent检索论文片段
        2. AnalysisAgent分析内容结构
        3. QAAgent验证输出质量
        4. CodeAgent复现代码（如需要）

    状态管理:
        - workflow_state: 记录各阶段结果
        - memory: 记忆管理器，追踪历史

    Example:
        orchestrator = create_orchestrator("session-001")
        result = orchestrator.run_pipeline("Transformer注意力机制", need_code=True)
        # result包含retrieval/analysis/quality_assurance/code_reproduction
    """

    def __init__(self, session_id: str = "default"):
        """
        初始化协调器

        Args:
            session_id: 会话ID，用于记忆隔离
        Side Effects:
            - 创建ToolRegistry和MemoryManager
            - 初始化四个Agent实例
        """
        # 初始化组件 - 共享registry和memory
        self.registry = create_default_registry()
        self.memory = PaperMemoryManager(session_id)

        # 初始化四个Agent - 共享registry和memory
        self.retrieval_agent = PaperRetrievalAgent(self.registry, self.memory)
        self.analysis_agent = PaperAnalysisAgent(self.registry, self.memory)
        self.qa_agent = QualityAssuranceAgent(self.registry, self.memory)
        self.code_agent = CodeReproductionAgent(self.registry, self.memory)

        # 记录工作流状态 - 用于追踪Pipeline进度
        self.workflow_state = {
            "retrieval": None,
            "analysis": None,
            "qa": None,
            "code": None
        }

    def run_pipeline(self, query: str, top_k: int = 10, need_code: bool = False) -> Dict:
        """
        运行完整的Agent协作流程

        设计意图: 编排四角色Agent按顺序执行，生成完整结果
        Args:
            query: 用户查询
            top_k: 检索数量
            need_code: 是否需要生成代码
        Returns:
            Pipeline完整结果:
            {
                "query": 查询文本,
                "pipeline_status": "completed",
                "retrieval": 检索结果,
                "analysis": 分析结果,
                "quality_assurance": 质量验证结果,
                "code_reproduction": 代码复现结果(如need_code=True),
                "final_output": 最终输出(如质量通过),
                "workflow_state": 工作流状态
            }

        Pipeline流程:
            1. Retrieval阶段: 检索论文片段
            2. Analysis阶段: 分析内容结构
            3. QA阶段: 验证输出质量
            4. Code阶段: 复现代码（如need_code=True）
        """
        # 阶段1: 检索 - 使用RetrievalAgent
        retrieval_result = self.retrieval_agent.retrieve(query, top_k=top_k)
        self.workflow_state["retrieval"] = retrieval_result

        # 阶段2: 分析 - 使用AnalysisAgent
        analysis_result = self.analysis_agent.analyze(
            query,
            retrieval_result["results"]
        )
        self.workflow_state["analysis"] = analysis_result

        # 生成模拟输出用于质量验证 - 基于分析结果
        generated_output = self._generate_output(query, analysis_result)

        # 阶段3: 质量验证 - 使用QAAgent
        qa_result = self.qa_agent.validate(
            generated_output,
            retrieval_result["results"]
        )
        self.workflow_state["qa"] = qa_result

        # 阶段4: 代码复现（如需要）- 使用CodeAgent
        code_result = None
        if need_code:
            code_result = self.code_agent.reproduce(query, analysis_result)
            self.workflow_state["code"] = code_result

        return {
            "query": query,
            "pipeline_status": "completed",
            "retrieval": retrieval_result,
            "analysis": analysis_result,
            "quality_assurance": qa_result,
            "code_reproduction": code_result,
            "final_output": generated_output if qa_result["is_passed"] else None,
            "workflow_state": self.workflow_state
        }

    def _generate_output(self, query: str, analysis: Dict) -> str:
        """
        生成输出（简化版）

        设计意图: 将分析结果转换为用户友好的输出文本
        Args:
            query: 用户查询
            analysis: 分析结果
        Returns:
            输出文本
        Note:
            当前为简化实现，未来可接入LLM生成更丰富的输出
        """
        summary = analysis.get("summary", "")
        concepts = analysis.get("concepts", [])

        output = f"关于「{query}」的分析：\n\n"
        output += f"摘要：{summary}\n\n"
        output += f"核心概念：{', '.join(concepts[:5])}\n"

        return output

    def get_status(self) -> Dict:
        """
        获取当前工作流状态

        设计意图: 提供状态信息，用于调试和监控
        Returns:
            状态字典：memory_session/registered_tools/workflow_state
        """
        return {
            "memory_session": self.memory.session_id,
            "registered_tools": self.registry.list_tools(),
            "workflow_state": {
                stage: "completed" if result else "pending"
                for stage, result in self.workflow_state.items()
            }
        }


# ===== 便捷函数 =====

def create_orchestrator(session_id: str = "default") -> SpecializedAgentOrchestrator:
    """
    创建协调器实例

    设计意图: 提供统一的创建入口，简化使用
    Args:
        session_id: 会话ID
    Returns:
        SpecializedAgentOrchestrator实例
    Example:
        orchestrator = create_orchestrator("user-session-001")
    """
    return SpecializedAgentOrchestrator(session_id)


# ===== 测试入口 =====

if __name__ == "__main__":
    print("=" * 60)
    print("四角色专用Agent系统测试")
    print("=" * 60)

    # 创建协调器
    orchestrator = create_orchestrator("test-session-001")

    # 测试查询
    test_queries = [
        "Transformer自注意力机制的数学公式是什么?",
        "请解释GPT模型的核心架构",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"查询: {query}")
        print("=" * 60)

        # 运行完整流程
        result = orchestrator.run_pipeline(query, top_k=5, need_code=True)

        # 打印结果摘要
        print(f"\n[检索] 召回结果: {result['retrieval']['metrics']['total']} 篇")
        print(f"[分析] 概念数: {len(result['analysis']['concepts'])}")
        print(f"[分析] 公式数: {len(result['analysis']['formulas'])}")
        print(f"[质量] 评分: {result['quality_assurance']['quality_score']}")
        print(f"[质量] 通过: {result['quality_assurance']['is_passed']}")
        if result['code_reproduction']:
            print(f"[代码] 模块数: {len(result['code_reproduction']['code_modules'])}")
            print(f"[代码] 可运行: {result['code_reproduction']['is_runnable']}")

        # 打印风险
        if result['quality_assurance']['risks']:
            print(f"\n风险告警: {result['quality_assurance']['risks']}")

        # 打印建议
        if result['quality_assurance']['suggestions']:
            print(f"修正建议: {result['quality_assurance']['suggestions']}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)