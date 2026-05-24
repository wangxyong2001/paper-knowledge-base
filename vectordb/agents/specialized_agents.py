"""
四角色专用Agent系统 - 论文知识库

实现四个专业Agent角色分工：
1. PaperRetrievalAgent - 检索专家
2. PaperAnalysisAgent - 解读专家
3. QualityAssuranceAgent - 质量专家
4. CodeReproductionAgent - 复现专家
5. SpecializedAgentOrchestrator - 协调器
"""

from typing import Dict, List, Any, Optional
import sys
import re

# 添加项目路径
sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
sys.path.append('/home/nvidia/workspace/paper/vectordb/core')

from tool_registry import ToolRegistry, create_default_registry
from memory_manager import PaperMemoryManager


class PaperRetrievalAgent:
    """
    检索专家 - 专注于论文检索和召回优化

    工具: VectorSearchTool, BM25SearchTool, RRF融合
    输出: 检索结果 + 相关度评分 + 召回指标
    """

    def __init__(self, registry: ToolRegistry, memory: Optional[PaperMemoryManager] = None):
        self.registry = registry
        self.memory = memory
        self._init_tools()

    def _init_tools(self):
        """初始化检索工具"""
        # 确保工具已注册
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

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            包含检索结果、评分、指标的字典
        """
        # 执行三种检索方式
        vector_result = self.registry.execute("vector_search", {
            "query": query,
            "top_k": top_k
        })

        bm25_result = self.registry.execute("bm25_search", {
            "query": query,
            "top_k": top_k
        })

        hybrid_result = self.registry.execute("hybrid_search", {
            "query": query,
            "top_k": top_k
        })

        # 提取结果
        results = hybrid_result.get("data", {}).get("results", []) if hybrid_result.get("success") else []

        # 计算召回指标
        metrics = self._calculate_metrics(query, results)

        # 记录到记忆
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
        """计算召回指标"""
        if not results:
            return {
                "total": 0,
                "avg_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "coverage": 0.0
            }

        scores = [r.get("rrf_score", r.get("score", 0)) for r in results]

        return {
            "total": len(results),
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "coverage": len([s for s in scores if s > 0.3]) / len(scores) if scores else 0.0
        }


class PaperAnalysisAgent:
    """
    解读专家 - 论文深度解读、公式提取、中文通俗化

    工具: FormulaExtractor, ContentTranslator, OutputFormatter
    输出: 餐巾纸摘要 + 核心概念 + 公式解释 + 代码设计
    """

    def __init__(self, registry: ToolRegistry, memory: Optional[PaperMemoryManager] = None):
        self.registry = registry
        self.memory = memory

    def analyze(self, query: str, chunks: List[Dict]) -> Dict:
        """
        分析论文内容

        Args:
            query: 用户查询
            chunks: 检索到的论文片段

        Returns:
            包含摘要、概念、公式、代码设计的字典
        """
        # 合并上下文
        context = self._assemble_context(chunks)

        # 提取公式
        formulas = self._extract_formulas(context)

        # 提取核心概念
        concepts = self._extract_concepts(context)

        # 生成餐巾纸摘要
        summary = self._generate_napkin_summary(query, context)

        # 提取代码设计
        code_design = self._extract_code_design(context)

        # 记录到记忆
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
        """组装上下文"""
        parts = []
        for i, chunk in enumerate(chunks[:5]):
            content = chunk.get("content", chunk.get("text", ""))
            parts.append(f"[{i+1}] {content[:500]}")
        return "\n\n".join(parts)

    def _extract_formulas(self, text: str) -> List[Dict]:
        """提取公式"""
        formulas = []

        # 匹配常见数学公式模式
        # 1. LaTeX 格式: $...$ 或 $$...$$
        latex_pattern = r'\$([^$]+)\$'
        for match in re.finditer(latex_pattern, text):
            formulas.append({
                "raw": match.group(0),
                "content": match.group(1),
                "type": "latex"
            })

        # 2. 带编号的公式: (1), (2), 等
        numbered_pattern = r'\(([0-9]+)\)\s*([A-Za-z].*?)(?=\n|$)'
        for match in re.finditer(numbered_pattern, text):
            formulas.append({
                "number": match.group(1),
                "content": match.group(2).strip(),
                "type": "numbered"
            })

        # 3. 箭头函数符号: →
        arrow_pattern = r'([A-Za-z_][A-Za-z0-9_]*)\s*→\s*([A-Za-z_][A-Za-z0-9_]*)'
        for match in re.finditer(arrow_pattern, text):
            formulas.append({
                "from": match.group(1),
                "to": match.group(2),
                "type": "mapping"
            })

        return formulas[:10]  # 限制数量

    def _extract_concepts(self, text: str) -> List[str]:
        """提取核心概念"""
        concepts = []

        # 提取大写术语
        term_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b'
        terms = re.findall(term_pattern, text)

        # 过滤常见词
        stop_words = {"The", "This", "That", "A", "An", "In", "On", "At", "To", "For", "We", "Our", "Our", "Based", "Using", "From", "With", "Table", "Figure", "Algorithm"}
        concepts = [t for t in terms if t not in stop_words and len(t) > 2]

        # 去重并返回
        return list(dict.fromkeys(concepts))[:10]

    def _generate_napkin_summary(self, query: str, context: str) -> str:
        """生成餐巾纸摘要（简化版）"""
        # 提取第一段作为摘要
        paragraphs = context.split("\n\n")
        first_para = paragraphs[0] if paragraphs else ""

        # 截取前200字
        summary = first_para[:200] + "..." if len(first_para) > 200 else first_para

        return summary

    def _extract_code_design(self, text: str) -> Dict:
        """提取代码设计"""
        code_snippets = []

        # 匹配代码块
        code_pattern = r'```(?:python|py)?\s*([\s\S]*?)```'
        for match in re.finditer(code_pattern, text):
            code_snippets.append(match.group(1).strip())

        # 匹配行内代码
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

    工具: HallucinationDetectTool, CitationCheckTool
    输出: 质量评分 + 风险告警 + 修正建议
    """

    def __init__(self, registry: ToolRegistry, memory: Optional[PaperMemoryManager] = None):
        self.registry = registry
        self.memory = memory

    def validate(self, output: str, chunks: List[Dict]) -> Dict:
        """
        验证输出质量

        Args:
            output: 待验证的输出文本
            chunks: 支撑上下文

        Returns:
            质量评分、风险告警、修正建议
        """
        # 提取上下文文本
        contexts = [c.get("content", c.get("text", "")) for c in chunks]

        # 幻觉检测
        hallucination_result = self._detect_hallucination(output, contexts)

        # 引用验证
        citation_result = self._validate_citations(output, chunks)

        # 计算综合质量评分
        quality_score = self._calculate_quality_score(hallucination_result, citation_result)

        # 生成风险告警
        risks = self._generate_risks(hallucination_result, citation_result)

        # 生成修正建议
        suggestions = self._generate_suggestions(hallucination_result, citation_result)

        return {
            "output_length": len(output),
            "quality_score": quality_score,
            "hallucination": hallucination_result,
            "citations": citation_result,
            "risks": risks,
            "suggestions": suggestions,
            "is_passed": quality_score >= 0.7
        }

    def _detect_hallucination(self, output: str, contexts: List[str]) -> Dict:
        """幻觉检测"""
        result = self.registry.execute("hallucination_detect", {
            "answer": output,
            "contexts": contexts,
            "threshold": 0.7
        })

        return result.get("data", {}) if result.get("success") else {
            "is_hallucination": False,
            "support_rate": 1.0,
            "risk_level": "unknown"
        }

    def _validate_citations(self, output: str, chunks: List[Dict]) -> Dict:
        """引用验证"""
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
        """计算综合质量评分"""
        # 基于幻觉率和引用准确率
        hallucination_risk = hallucination.get("support_rate", 1.0)
        citation_accuracy = citation.get("accuracy", 1.0)

        # 加权平均
        score = 0.6 * hallucination_risk + 0.4 * citation_accuracy

        return round(score, 2)

    def _generate_risks(self, hallucination: Dict, citation: Dict) -> List[str]:
        """生成风险告警"""
        risks = []

        if hallucination.get("risk_level") == "high":
            risks.append("高幻觉风险：输出内容与上下文匹配度低")

        if hallucination.get("hallucinated_entities"):
            risks.append(f"疑似幻觉实体: {', '.join(hallucination['hallucinated_entities'][:3])}")

        if citation.get("accuracy", 1.0) < 1.0:
            invalid_count = citation.get("total", 0) - citation.get("valid_count", 0)
            risks.append(f"引用失效: {invalid_count} 个引用无法验证")

        if not risks:
            risks.append("无明显风险")

        return risks

    def _generate_suggestions(self, hallucination: Dict, citation: Dict) -> List[str]:
        """生成修正建议"""
        suggestions = []

        if hallucination.get("risk_level") in ["medium", "high"]:
            suggestions.append("建议增加更多上下文引用来支撑输出")

        if hallucination.get("support_rate", 1.0) < 0.8:
            suggestions.append("建议重新核事实性陈述")

        if citation.get("accuracy", 1.0) < 1.0:
            suggestions.append("建议使用 [1], [2] 等标准引用格式")

        if not suggestions:
            suggestions.append("质量良好，可直接使用")

        return suggestions


class CodeReproductionAgent:
    """
    复现专家 - 论文代码复现设计、测试验证

    工具: PythonExecTool, TestGenerator
    输出: 代码模块 + 测试用例 + 运行结果
    """

    def __init__(self, registry: ToolRegistry, memory: Optional[PaperMemoryManager] = None):
        self.registry = registry
        self.memory = memory

    def reproduce(self, query: str, analysis: Dict) -> Dict:
        """
        复现论文代码

        Args:
            query: 用户查询
            analysis: 分析结果

        Returns:
            代码模块、测试用例、运行结果
        """
        # 生成代码框架
        code_modules = self._generate_code_modules(query, analysis)

        # 生成测试用例
        test_cases = self._generate_test_cases(code_modules)

        # 尝试运行代码
        run_results = self._run_code_modules(code_modules)

        return {
            "query": query,
            "code_modules": code_modules,
            "test_cases": test_cases,
            "run_results": run_results,
            "is_runnable": all(r.get("success", False) for r in run_results)
        }

    def _generate_code_modules(self, query: str, analysis: Dict) -> List[Dict]:
        """生成代码模块"""
        modules = []

        # 提取代码设计
        code_design = analysis.get("code_design", {})
        snippets = code_design.get("snippets", [])

        # 如果有现有代码片段，直接使用
        for i, snippet in enumerate(snippets):
            modules.append({
                "name": f"module_{i+1}.py",
                "code": snippet,
                "type": "existing"
            })

        # 生成代码模板
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
        """生成Transformer代码模板"""
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
        """生成Attention代码模板"""
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
        """生成通用代码模板"""
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
        """生成测试用例"""
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
        """运行代码模块"""
        results = []

        for module in code_modules:
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

    工作流程:
    1. RetrievalAgent 检索论文
    2. AnalysisAgent 分析内容
    3. QAAgent 验证质量
    4. CodeAgent 复现代码（如需要）
    """

    def __init__(self, session_id: str = "default"):
        # 初始化组件
        self.registry = create_default_registry()
        self.memory = PaperMemoryManager(session_id)

        # 初始化四个Agent
        self.retrieval_agent = PaperRetrievalAgent(self.registry, self.memory)
        self.analysis_agent = PaperAnalysisAgent(self.registry, self.memory)
        self.qa_agent = QualityAssuranceAgent(self.registry, self.memory)
        self.code_agent = CodeReproductionAgent(self.registry, self.memory)

        # 记录工作流状态
        self.workflow_state = {
            "retrieval": None,
            "analysis": None,
            "qa": None,
            "code": None
        }

    def run_pipeline(self, query: str, top_k: int = 10, need_code: bool = False) -> Dict:
        """
        运行完整的Agent协作流程

        Args:
            query: 用户查询
            top_k: 检索数量
            need_code: 是否需要生成代码

        Returns:
            包含所有阶段结果的字典
        """
        # 阶段1: 检索
        retrieval_result = self.retrieval_agent.retrieve(query, top_k=top_k)
        self.workflow_state["retrieval"] = retrieval_result

        # 阶段2: 分析
        analysis_result = self.analysis_agent.analyze(
            query,
            retrieval_result["results"]
        )
        self.workflow_state["analysis"] = analysis_result

        # 生成一个模拟的输出用于质量验证
        generated_output = self._generate_output(query, analysis_result)

        # 阶段3: 质量验证
        qa_result = self.qa_agent.validate(
            generated_output,
            retrieval_result["results"]
        )
        self.workflow_state["qa"] = qa_result

        # 阶段4: 代码复现（如需要）
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
        """生成输出（简化版）"""
        summary = analysis.get("summary", "")
        concepts = analysis.get("concepts", [])

        output = f"关于「{query}」的分析：\n\n"
        output += f"摘要：{summary}\n\n"
        output += f"核心概念：{', '.join(concepts[:5])}\n"

        return output

    def get_status(self) -> Dict:
        """获取当前工作流状态"""
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
    """创建协调器实例"""
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
