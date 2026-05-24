"""
LangGraph Agent Framework - 论文知识库RAG系统

基于设计文档实现的核心Agent架构
"""

from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END

# 状态定义
class PaperRAGState(TypedDict):
    """论文RAG Agent状态"""
    query: str                        # 用户查询
    intent: str                       # 查询意图
    chunks: List[Dict]                # 检索结果
    grades: List[str]                 # 文档分级
    evidence: List[Dict]              # 收集的证据
    citations: List[Dict]             # 引用列表
    answer: str                       # 生成的答案
    reflection: Dict                  # 自省结果
    decision: str                     # 决策: continue/retry/escalate
    retry_count: int                  # 重试次数
    parent_context: str               # 父块上下文


# 导入现有组件
import sys
sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
from search import HybridSearcher
from embed_local import LocalEmbedding


class PaperRAGAgent:
    """论文RAG Agent - LangGraph实现"""

    MAX_RETRIES = 3

    def __init__(self):
        self.searcher = HybridSearcher(use_bge=True)
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流"""

        # 创建状态图
        workflow = StateGraph(PaperRAGState)

        # 添加节点
        workflow.add_node("interpret", self._interpret_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("grade_docs", self._grade_docs_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("reflect", self._reflect_node)
        workflow.add_node("cite_check", self._cite_check_node)

        # 定义边
        workflow.set_entry_point("interpret")
        workflow.add_edge("interpret", "retrieve")
        workflow.add_edge("retrieve", "grade_docs")

        # 条件路由
        workflow.add_conditional_edges(
            "grade_docs",
            self._route_after_grade,
            {
                "generate": "generate",
                "retry": "retrieve",
            }
        )

        workflow.add_edge("generate", "reflect")

        workflow.add_conditional_edges(
            "reflect",
            self._route_after_reflect,
            {
                "cite_check": "cite_check",
                "retry": "retrieve",
                "escalate": END,
            }
        )

        workflow.add_edge("cite_check", END)

        return workflow.compile()

    # ===== 节点实现 =====

    def _interpret_node(self, state: PaperRAGState) -> PaperRAGState:
        """查询意图解析"""
        query = state["query"]

        # 意图分类
        intent = self._classify_intent(query)

        state["intent"] = intent
        state["retry_count"] = 0

        return state

    def _retrieve_node(self, state: PaperRAGState) -> PaperRAGState:
        """混合检索"""
        query = state["query"]

        # 调用现有HybridSearcher
        results = self.searcher.search(query, top_k=10)

        state["chunks"] = results["results"]
        state["retry_count"] += 1

        return state

    def _grade_docs_node(self, state: PaperRAGState) -> PaperRAGState:
        """文档分级"""
        chunks = state["chunks"]
        query = state["query"]

        grades = []
        for chunk in chunks:
            grade = self._grade_relevance(query, chunk)
            grades.append(grade)

        state["grades"] = grades

        return state

    def _generate_node(self, state: PaperRAGState) -> PaperRAGState:
        """答案生成"""
        query = state["query"]
        chunks = state["chunks"]

        # 组装上下文
        context = self._assemble_context(chunks)

        # 调用LLM生成 (待实现)
        answer = self._call_llm(query, context)

        state["answer"] = answer

        return state

    def _reflect_node(self, state: PaperRAGState) -> PaperRAGState:
        """自省评估"""
        answer = state["answer"]
        chunks = state["chunks"]

        reflection = {
            "support_score": self._check_support(answer, chunks),
            "hallucination_risk": self._detect_hallucination(answer, chunks),
            "completeness": self._check_completeness(answer),
        }

        decision = self._make_decision(reflection, state["retry_count"])

        state["reflection"] = reflection
        state["decision"] = decision

        return state

    def _cite_check_node(self, state: PaperRAGState) -> PaperRAGState:
        """Citation强制检查"""
        answer = state["answer"]
        chunks = state["chunks"]

        citations = self._extract_and_validate_citations(answer, chunks)

        state["citations"] = citations

        return state

    # ===== 路由函数 =====

    def _route_after_grade(self, state: PaperRAGState) -> str:
        """文档分级后路由"""
        grades = state["grades"]
        relevant_count = sum(1 for g in grades if g == "relevant")

        if relevant_count >= 3:
            return "generate"
        elif state["retry_count"] < self.MAX_RETRIES:
            return "retry"
        else:
            return "generate"  # 强制生成

    def _route_after_reflect(self, state: PaperRAGState) -> str:
        """自省后路由"""
        reflection = state["reflection"]
        retry_count = state["retry_count"]

        if reflection["support_score"] >= 0.8 and reflection["hallucination_risk"] < 0.05:
            return "cite_check"
        elif retry_count < self.MAX_RETRIES:
            return "retry"
        else:
            return "escalate"  # 熔断

    # ===== 辅助方法 =====

    def _classify_intent(self, query: str) -> str:
        """分类查询意图"""
        if "代码" in query or "实现" in query:
            return "code_generation"
        elif "对比" in query or "区别" in query:
            return "comparison"
        elif "公式" in query:
            return "formula_explanation"
        else:
            return "qa"

    def _grade_relevance(self, query: str, chunk: Dict) -> str:
        """评估文档相关性"""
        # 简化实现: 基于similarity score
        score = chunk.get("rrf_score", 0)
        if score > 0.5:
            return "relevant"
        elif score > 0.3:
            return "ambiguous"
        else:
            return "irrelevant"

    def _assemble_context(self, chunks: List[Dict]) -> str:
        """组装上下文"""
        context_parts = []
        for i, chunk in enumerate(chunks[:5]):
            context_parts.append(f"[{i+1}] {chunk['content']}")
        return "\n\n".join(context_parts)

    def _check_support(self, answer: str, chunks: List[Dict]) -> float:
        """检查支撑度"""
        # 简化实现
        return 0.85

    def _detect_hallucination(self, answer: str, chunks: List[Dict]) -> float:
        """幻觉检测"""
        # 简化实现
        return 0.03

    def _check_completeness(self, answer: str) -> float:
        """检查完整性"""
        return 0.90

    def _make_decision(self, reflection: Dict, retry_count: int) -> str:
        """决策"""
        if reflection["support_score"] >= 0.8:
            return "continue"
        elif retry_count < self.MAX_RETRIES:
            return "retry"
        else:
            return "escalate"

    def _call_llm(self, query: str, context: str) -> str:
        """调用LLM"""
        # 待实现: 连接云端API或本地Ollama
        return f"关于'{query}'的回答将基于提供的上下文生成。"

    def _extract_and_validate_citations(self, answer: str, chunks: List[Dict]) -> List[Dict]:
        """提取并验证Citations"""
        # 待实现
        return []

    def run(self, query: str) -> Dict:
        """运行Agent"""
        initial_state = {
            "query": query,
            "intent": "",
            "chunks": [],
            "grades": [],
            "evidence": [],
            "citations": [],
            "answer": "",
            "reflection": {},
            "decision": "",
            "retry_count": 0,
            "parent_context": "",
        }

        final_state = self.workflow.invoke(initial_state)
        return final_state


# 测试入口
if __name__ == "__main__":
    agent = PaperRAGAgent()

    # 测试查询
    test_queries = [
        "Transformer的核心创新是什么?",
        "自注意力机制的数学公式是什么?",
        "请生成Transformer的代码实现",
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        result = agent.run(query)
        print(f"意图: {result['intent']}")
        print(f"检索chunks: {len(result['chunks'])}")
        print(f"答案: {result['answer'][:200]}...")
        print(f"决策: {result['decision']}")