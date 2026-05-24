# LangChain/LangGraph Integration Design Document

> ADR-002: Framework Selection and Integration for Agentic RAG System

**Status**: Proposed
**Date**: 2026-05-24
**Author**: Software Architect Agent

---

## Executive Summary

This document provides a comprehensive evaluation of LangChain and LangGraph frameworks for integration with the existing Paper RAG system. After thorough analysis, we recommend a **hybrid approach**: use LangGraph for workflow orchestration while maintaining custom implementations for retrieval and citation components.

**Key Decision**: Adopt LangGraph for StateGraph-based workflow management, but build custom agent logic to maintain flexibility and avoid LangChain's abstraction overhead.

---

## 1. Framework Selection: LangChain vs LangGraph

### 1.1 Comparison Matrix

| Dimension | LangChain | LangGraph | Recommendation |
|-----------|-----------|-----------|----------------|
| **Primary Use Case** | Sequential chains, simple pipelines | State machines, cyclic workflows | LangGraph for complex RAG |
| **Workflow Complexity** | Linear chains only | Cyclic graphs with conditions | LangGraph supports reflection loops |
| **State Management** | Memory modules (external) | Built-in StateGraph | LangGraph native state tracking |
| **Self-Reflection** | Requires manual recursion | Native cycle support | LangGraph better for agentic RAG |
| **Learning Curve** | Moderate (many abstractions) | Steeper but clearer mental model | LangGraph more explicit |
| **Community Activity** | Very active (2024-2026) | Growing rapidly (LangChain team) | Both well-maintained |
| **Production Cases** | 1000+ documented | 500+ growing | Both production-ready |
| **Debugging** | Chain trace | Graph visualization | LangGraph better visibility |
| **Customization** | Many hooks but constrained | Full control of nodes/edges | LangGraph more flexible |
| **Performance** | High overhead (many layers) | Lower overhead | LangGraph more efficient |

### 1.2 Detailed Analysis

#### LangChain Characteristics

**Strengths:**
- Rich ecosystem of integrations (100+ LLM providers, vector stores, tools)
- Mature documentation and community support
- Chain abstraction simplifies common patterns
- Built-in prompt templates, output parsers

**Weaknesses:**
- Sequential chain model cannot express cyclic reflection loops
- Memory abstraction adds complexity without solving state management
- High abstraction overhead makes debugging difficult
- Breaking changes common between versions (v0.1 -> v0.2 -> v0.3)

**Use Case Fit:**
- Simple linear RAG pipelines
- Quick prototyping
- Integration-heavy applications

**Code Example (LangChain Chain):**
```python
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama

# LangChain forces linear flow
chain = RetrievalQA.from_chain_type(
    llm=Ollama(model="qwen3.6:35b"),
    retriever=chroma.as_retriever(),
    chain_type="stuff"
)
# Cannot express: retrieve -> evaluate -> retry if poor quality
```

#### LangGraph Characteristics

**Strengths:**
- Native state machine with StateGraph
- Conditional edges for routing logic
- Cyclic graphs enable reflection loops
- Clear mental model: nodes = functions, edges = transitions
- Built-in checkpointing for state persistence
- LangSmith integration for visualization

**Weaknesses:**
- Steeper learning curve
- Less integration ecosystem (growing)
- More boilerplate for simple cases
- Newer framework, fewer production examples

**Use Case Fit:**
- Agentic RAG with reflection
- Multi-step reasoning with validation
- Complex workflow orchestration

**Code Example (LangGraph StateGraph):**
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class RAGState(TypedDict):
    query: str
    documents: list
    answer: str
    iterations: int

def retrieve(state: RAGState) -> RAGState:
    # Retrieve documents
    pass

def grade_documents(state: RAGState) -> RAGState:
    # Grade document relevance
    pass

def generate(state: RAGState) -> RAGState:
    # Generate answer
    pass

def reflect(state: RAGState) -> RAGState:
    # Self-reflection
    pass

# Build graph with cycles
graph = StateGraph(RAGState)
graph.add_node("retrieve", retrieve)
graph.add_node("grade", grade_documents)
graph.add_node("generate", generate)
graph.add_node("reflect", reflect)

# Conditional edges enable reflection loops
graph.add_conditional_edges(
    "reflect",
    lambda s: "retry" if s["iterations"] < 3 else "end",
    {"retry": "retrieve", "end": END}
)
```

### 1.3 Decision: LangGraph for Orchestration

**Rationale:**

1. **Reflection Requirement**: Your use case explicitly requires "Self-Reflection self-correction" and "Execution Trace feedback" - these necessitate cyclic workflows that LangChain chains cannot express.

2. **State Management**: LangGraph's StateGraph provides native state tracking, essential for:
   - Tracking iteration count (prevent infinite loops)
   - Storing intermediate results for debugging
   - Checkpointing for fault tolerance

3. **Control Flow**: Conditional edges enable:
   - Route to retry based on quality score
   - Escalate to human review on uncertainty
   - Early termination on confidence threshold

4. **Lower Abstraction**: Less "magic" than LangChain, making debugging and customization easier.

5. **Future-Proof**: LangGraph is the direction LangChain team is moving for agentic workflows.

---

## 2. Requirement Mapping Analysis

### 2.1 Core Requirements vs Framework Capabilities

| Requirement | LangChain | LangGraph | Our Implementation |
|-------------|-----------|-----------|-------------------|
| **Paper -> Interpret -> Code -> Test -> Deliver** | Chain possible | StateGraph better | Custom nodes |
| **Agentic Iterative Retrieval** | Not supported | Native cycles | LangGraph + Custom |
| **Self-Reflection Self-Correction** | Manual recursion | Native cycles | LangGraph |
| **Citation Enforcement** | Not built-in | Not built-in | Custom validator |
| **Execution Trace Feedback** | LangSmith trace | LangSmith + State | Both support |
| **Hybrid Retrieval (Vector + BM25)** | Requires custom | Requires custom | Reuse existing |
| **Parent-Child Chunking** | Not built-in | Not built-in | Reuse existing |
| **Local/Cloud Backend Switching** | Not built-in | Not built-in | Reuse MCP server |

### 2.2 What LangGraph Provides

1. **StateGraph**: State machine for workflow orchestration
2. **Conditional Edges**: Dynamic routing based on state
3. **Checkpointing**: State persistence for fault recovery
4. **LangSmith Integration**: Visualization and debugging
5. **Human-in-the-loop**: Built-in interruption points

### 2.3 What We Must Build Custom

1. **Citation Validator**: Enforce citation requirements
2. **Hybrid Retriever**: Our existing RRF fusion
3. **Document Grader**: Quality assessment for retrieved chunks
4. **Reflection Evaluator**: Self-assessment logic
5. **Execution Tracer**: Store traces for feedback

### 2.4 Integration Strategy

```
                    +-------------------+
                    |   LangGraph       |
                    |   (Orchestration) |
                    +--------+----------+
                             |
          +------------------+------------------+
          |                  |                  |
    +-----v------+    +------v------+    +------v------+
    |   Retrieval |    |  Generation |    |  Reflection |
    |   Node      |    |    Node     |    |    Node     |
    +-----+-------+    +------+------+    +------+------+
          |                  |                  |
          |                  |                  |
    +-----v------------------v------------------v------+
    |              Custom Components Layer             |
    |  +-------------+  +-------------+  +------------+ |
    |  | Hybrid      |  | Citation    |  | Execution  | |
    |  | Retriever   |  | Validator   |  | Tracer     | |
    |  | (Existing)  |  | (New)       |  | (New)      | |
    |  +-------------+  +-------------+  +------------+ |
    +---------------------------------------------------+
                             |
                    +--------v----------+
                    |   MCP Server      |
                    |   (LLM Backend)   |
                    +-------------------+
```

---

## 3. LangGraph Detailed Design

### 3.1 State Definition

```python
from typing import TypedDict, List, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Chunk:
    """Retrieved document chunk"""
    chunk_id: str
    content: str
    metadata: dict
    score: float
    source: str  # 'vector' | 'bm25' | 'hybrid'
    parent_context: str

@dataclass
class Grade:
    """Document quality grade"""
    chunk_id: str
    relevance_score: float  # 0.0 - 1.0
    reasoning: str
    is_relevant: bool
    grade_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Citation:
    """Citation record"""
    chunk_id: str
    quote: str  # Exact text from source
    paper_title: str
    arxiv_id: Optional[str]
    page_number: Optional[int]
    section: Optional[str]

@dataclass
class ReflectionResult:
    """Self-reflection result"""
    quality_score: float  # 0.0 - 1.0
    completeness: float   # 0.0 - 1.0
    citation_coverage: float
    hallucination_risk: float
    reasoning: str
    needs_retry: bool
    retry_query: Optional[str] = None

@dataclass
class ExecutionTrace:
    """Execution trace for feedback"""
    node_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    input_state: dict = field(default_factory=dict)
    output_state: dict = field(default_factory=dict)
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

class PaperRAGState(TypedDict):
    """Complete state for Paper RAG workflow"""

    # Input
    query: str                              # Original user query
    query_intent: Optional[str]             # Parsed intent
    conversation_history: List[dict]       # Previous turns

    # Retrieval Stage
    chunks: List[Chunk]                     # Retrieved chunks
    retrieval_method: str                   # 'vector' | 'bm25' | 'hybrid'

    # Grading Stage
    grades: List[Grade]                     # Quality grades
    relevant_chunks: List[Chunk]            # Filtered chunks

    # Generation Stage
    generated_answer: Optional[str]         # Raw generated answer
    citations: List[Citation]               # Extracted citations

    # Reflection Stage
    reflection: Optional[ReflectionResult] # Self-assessment
    iteration_count: int                    # Current iteration
    max_iterations: int                     # Max retries (default: 3)

    # Quality Gates
    quality_score: float                    # Overall quality
    citation_enforced: bool                 # All claims cited?
    ready_for_delivery: bool                # Ready to output?

    # Tracing
    traces: List[ExecutionTrace]            # Execution history
    total_tokens: int                       # Token usage

    # Routing
    decision: Optional[Literal[
        "continue",     # Continue to next stage
        "retry",        # Retry retrieval with refined query
        "escalate",     # Escalate to human review
        "complete"      # Workflow complete
    ]]
```

### 3.2 Node Implementations

```python
"""
LangGraph Nodes for Paper RAG System
"""
import httpx
import asyncio
from typing import Dict, Any
from datetime import datetime

# Import existing components
import sys
sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')
from search import HybridSearcher
from config import RETRIEVAL_CONFIG

class PaperRAGNodes:
    """Node implementations for Paper RAG workflow"""

    def __init__(
        self,
        mcp_base_url: str = "http://localhost:8080",
        use_bge: bool = True,
        max_iterations: int = 3
    ):
        self.searcher = HybridSearcher(use_bge=use_bge)
        self.mcp_base_url = mcp_base_url
        self.max_iterations = max_iterations

    async def interpret_query(self, state: PaperRAGState) -> PaperRAGState:
        """
        Node: Interpret user query and extract intent

        Input: query, conversation_history
        Output: query_intent
        """
        trace = ExecutionTrace(
            node_name="interpret",
            start_time=datetime.now(),
            input_state={"query": state["query"]}
        )

        try:
            # Call LLM via MCP server for intent classification
            prompt = f"""Analyze the following query and extract:
1. Primary intent (question, code_request, explanation, comparison)
2. Key concepts/terms
3. Required answer type (code, explanation, list, comparison)

Query: {state['query']}

Format: JSON with keys: intent, concepts, answer_type"""

            response = await self._call_llm(prompt)
            state["query_intent"] = response

            trace.success = True
            trace.output_state = {"query_intent": response}

        except Exception as e:
            trace.success = False
            trace.error = str(e)
            state["query_intent"] = "unknown"

        trace.end_time = datetime.now()
        trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
        state["traces"].append(trace)

        return state

    async def retrieve_documents(self, state: PaperRAGState) -> PaperRAGState:
        """
        Node: Retrieve documents using hybrid search

        Input: query, query_intent
        Output: chunks, retrieval_method
        """
        trace = ExecutionTrace(
            node_name="retrieve",
            start_time=datetime.now(),
            input_state={"query": state["query"]}
        )

        try:
            # Use existing hybrid search
            result = self.searcher.search(
                query=state["query"],
                top_k=RETRIEVAL_CONFIG['final_top_k']
            )

            # Convert to Chunk objects
            chunks = [
                Chunk(
                    chunk_id=item['chunk_id'],
                    content=item['content'],
                    metadata=item['metadata'],
                    score=item.get('rrf_score', 0),
                    source=item.get('source', 'hybrid'),
                    parent_context=item.get('parent_context', '')
                )
                for item in result['results']
            ]

            state["chunks"] = chunks
            state["retrieval_method"] = "hybrid"

            trace.success = True
            trace.output_state = {
                "chunk_count": len(chunks),
                "stats": result['stats']
            }

        except Exception as e:
            trace.success = False
            trace.error = str(e)
            state["chunks"] = []

        trace.end_time = datetime.now()
        trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
        state["traces"].append(trace)

        return state

    async def grade_documents(self, state: PaperRAGState) -> PaperRAGState:
        """
        Node: Grade document relevance

        Input: chunks
        Output: grades, relevant_chunks
        """
        trace = ExecutionTrace(
            node_name="grade_docs",
            start_time=datetime.now(),
            input_state={"chunk_count": len(state["chunks"])}
        )

        try:
            grades = []
            relevant_chunks = []

            for chunk in state["chunks"]:
                # Grade each chunk
                grade = await self._grade_single_chunk(
                    state["query"],
                    chunk
                )
                grades.append(grade)

                if grade.is_relevant:
                    relevant_chunks.append(chunk)

            state["grades"] = grades
            state["relevant_chunks"] = relevant_chunks

            trace.success = True
            trace.output_state = {
                "total_chunks": len(state["chunks"]),
                "relevant_chunks": len(relevant_chunks)
            }

        except Exception as e:
            trace.success = False
            trace.error = str(e)
            state["grades"] = []
            state["relevant_chunks"] = []

        trace.end_time = datetime.now()
        trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
        state["traces"].append(trace)

        return state

    async def generate_answer(self, state: PaperRAGState) -> PaperRAGState:
        """
        Node: Generate answer with citations

        Input: query, relevant_chunks
        Output: generated_answer, citations
        """
        trace = ExecutionTrace(
            node_name="generate",
            start_time=datetime.now(),
            input_state={"relevant_chunk_count": len(state["relevant_chunks"])}
        )

        try:
            # Build context from relevant chunks
            context = "\n\n".join([
                f"[{i+1}] {chunk.content}\nSource: {chunk.metadata.get('paper_title', 'Unknown')}"
                for i, chunk in enumerate(state["relevant_chunks"])
            ])

            prompt = f"""Answer the following question using ONLY the provided sources.
Each claim MUST be followed by a citation [n] referencing the source number.

Question: {state['query']}

Sources:
{context}

Requirements:
1. Answer comprehensively
2. Every factual claim must have a citation [n]
3. Quote exact text when making specific claims
4. If sources are insufficient, state clearly

Format your answer with inline citations like [1], [2], etc."""

            response = await self._call_llm(prompt)
            state["generated_answer"] = response

            # Extract citations from response
            citations = self._extract_citations(response, state["relevant_chunks"])
            state["citations"] = citations

            trace.success = True
            trace.output_state = {
                "answer_length": len(response),
                "citation_count": len(citations)
            }

        except Exception as e:
            trace.success = False
            trace.error = str(e)
            state["generated_answer"] = ""
            state["citations"] = []

        trace.end_time = datetime.now()
        trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
        state["traces"].append(trace)

        return state

    async def reflect_on_answer(self, state: PaperRAGState) -> PaperRAGState:
        """
        Node: Self-reflection on generated answer

        Input: generated_answer, citations, relevant_chunks
        Output: reflection, decision
        """
        trace = ExecutionTrace(
            node_name="reflect",
            start_time=datetime.now(),
            input_state={"iteration": state["iteration_count"]}
        )

        try:
            prompt = f"""Evaluate the following answer for quality:

Question: {state['query']}

Answer: {state['generated_answer']}

Citations: {len(state['citations'])} citations found

Evaluate on:
1. COMPLETENESS (0-1): Does the answer fully address the question?
2. CITATION_COVERAGE (0-1): Are all claims properly cited?
3. HALLUCINATION_RISK (0-1): Risk of fabricated information?
4. OVERALL_QUALITY (0-1): Overall answer quality

Also determine:
- needs_retry: Should we retry with refined query?
- retry_query: If retry, what refined query to use?

Return JSON format."""

            response = await self._call_llm(prompt)

            # Parse reflection result
            reflection = self._parse_reflection(response)
            state["reflection"] = reflection

            # Make decision based on reflection
            state["quality_score"] = reflection.quality_score

            if reflection.needs_retry and state["iteration_count"] < state["max_iterations"]:
                state["decision"] = "retry"
                state["query"] = reflection.retry_query or state["query"]
            elif reflection.quality_score < 0.6:
                state["decision"] = "escalate"
            else:
                state["decision"] = "complete"
                state["ready_for_delivery"] = True

            trace.success = True
            trace.output_state = {
                "quality_score": reflection.quality_score,
                "decision": state["decision"]
            }

        except Exception as e:
            trace.success = False
            trace.error = str(e)
            state["decision"] = "complete"  # Fail gracefully
            state["ready_for_delivery"] = True

        trace.end_time = datetime.now()
        trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
        state["traces"].append(trace)

        return state

    async def enforce_citations(self, state: PaperRAGState) -> PaperRAGState:
        """
        Node: Citation enforcement gate

        Input: generated_answer, citations
        Output: citation_enforced, decision
        """
        trace = ExecutionTrace(
            node_name="cite_check",
            start_time=datetime.now()
        )

        try:
            # Check if all claims have citations
            answer = state["generated_answer"]
            citations = state["citations"]

            # Validate citation coverage
            uncited_claims = self._find_uncited_claims(answer, citations)

            if uncited_claims:
                state["citation_enforced"] = False
                # Generate clarification for uncited claims
                state["decision"] = "retry"
            else:
                state["citation_enforced"] = True
                state["decision"] = "complete"
                state["ready_for_delivery"] = True

            trace.success = True

        except Exception as e:
            trace.success = False
            trace.error = str(e)
            state["citation_enforced"] = True  # Fail open

        trace.end_time = datetime.now()
        state["traces"].append(trace)

        return state

    async def prepare_retry(self, state: PaperRAGState) -> PaperRAGState:
        """
        Node: Prepare for retry iteration

        Input: reflection, iteration_count
        Output: updated iteration_count, refined query
        """
        state["iteration_count"] += 1

        # Use refined query from reflection if available
        if state["reflection"] and state["reflection"].retry_query:
            state["query"] = state["reflection"].retry_query

        state["decision"] = "continue"

        return state

    # Helper methods

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM via MCP server"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.mcp_base_url}/chat",
                json={"prompt": prompt}
            )
            return response.json().get("response", "")

    async def _grade_single_chunk(self, query: str, chunk: Chunk) -> Grade:
        """Grade a single chunk for relevance"""
        prompt = f"""Grade this document for relevance to the query.

Query: {query}

Document: {chunk.content[:500]}...

Return JSON: {{"relevance_score": 0.0-1.0, "is_relevant": true/false, "reasoning": "..."}}"""

        response = await self._call_llm(prompt)

        # Parse response
        import json
        try:
            result = json.loads(response)
            return Grade(
                chunk_id=chunk.chunk_id,
                relevance_score=result.get("relevance_score", 0.5),
                reasoning=result.get("reasoning", ""),
                is_relevant=result.get("is_relevant", False)
            )
        except:
            return Grade(
                chunk_id=chunk.chunk_id,
                relevance_score=0.5,
                reasoning="Failed to parse grade",
                is_relevant=False
            )

    def _extract_citations(self, answer: str, chunks: List[Chunk]) -> List[Citation]:
        """Extract citations from answer"""
        import re
        citations = []

        # Find all [n] citations
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, answer)

        for match in set(matches):
            idx = int(match) - 1
            if 0 <= idx < len(chunks):
                chunk = chunks[idx]
                citations.append(Citation(
                    chunk_id=chunk.chunk_id,
                    quote="",  # Would extract exact quote
                    paper_title=chunk.metadata.get('paper_title', 'Unknown'),
                    arxiv_id=chunk.metadata.get('arxiv_id'),
                    page_number=chunk.metadata.get('page_number'),
                    section=chunk.metadata.get('section_title')
                ))

        return citations

    def _parse_reflection(self, response: str) -> ReflectionResult:
        """Parse reflection response"""
        import json
        try:
            result = json.loads(response)
            return ReflectionResult(
                quality_score=result.get("OVERALL_QUALITY", 0.5),
                completeness=result.get("COMPLETENESS", 0.5),
                citation_coverage=result.get("CITATION_COVERAGE", 0.5),
                hallucination_risk=result.get("HALLUCINATION_RISK", 0.5),
                reasoning=result.get("reasoning", ""),
                needs_retry=result.get("needs_retry", False),
                retry_query=result.get("retry_query")
            )
        except:
            return ReflectionResult(
                quality_score=0.5,
                completeness=0.5,
                citation_coverage=0.5,
                hallucination_risk=0.5,
                reasoning="Failed to parse reflection",
                needs_retry=False
            )

    def _find_uncited_claims(self, answer: str, citations: List[Citation]) -> List[str]:
        """Find claims without citations"""
        # Simplified - would need NLP for proper implementation
        return []
```

### 3.3 Edge Definitions

```python
"""
LangGraph Edge Definitions for Paper RAG
"""
from typing import Literal

def route_after_interpret(state: PaperRAGState) -> Literal["retrieve", "complete"]:
    """Route after query interpretation"""
    # If query is too vague, ask for clarification
    if state.get("query_intent") == "unclear":
        return "complete"
    return "retrieve"

def route_after_grading(state: PaperRAGState) -> Literal["generate", "retry", "complete"]:
    """Route after document grading"""
    relevant_count = len(state.get("relevant_chunks", []))

    if relevant_count == 0:
        # No relevant documents found
        if state["iteration_count"] >= state["max_iterations"]:
            return "complete"  # Give up after max retries
        return "retry"

    return "generate"

def route_after_reflection(state: PaperRAGState) -> Literal["retry", "cite_check", "complete", "escalate"]:
    """Route after self-reflection"""
    decision = state.get("decision", "complete")

    if decision == "retry" and state["iteration_count"] < state["max_iterations"]:
        return "retry"
    elif decision == "escalate":
        return "escalate"
    elif decision == "complete":
        return "cite_check"

    return "cite_check"

def route_after_citation_check(state: PaperRAGState) -> Literal["retry", "complete"]:
    """Route after citation enforcement check"""
    if state.get("citation_enforced", False):
        return "complete"
    elif state["iteration_count"] < state["max_iterations"]:
        return "retry"
    else:
        return "complete"  # Fail gracefully

def should_retry(state: PaperRAGState) -> bool:
    """Check if should retry"""
    return (
        state["iteration_count"] < state["max_iterations"] and
        state.get("decision") == "retry"
    )
```

### 3.4 Complete StateGraph Construction

```python
"""
Complete LangGraph StateGraph for Paper RAG
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def build_paper_rag_graph(
    mcp_base_url: str = "http://localhost:8080",
    use_bge: bool = True,
    max_iterations: int = 3
) -> StateGraph:
    """
    Build the complete Paper RAG workflow graph

    Architecture:
    -----------
    START -> interpret -> retrieve -> grade_docs -> generate -> reflect
                                                              |
                        retry <- cite_check <- <---------------+
                                   |
                                   v
                                END/escalate
    """

    # Initialize nodes
    nodes = PaperRAGNodes(
        mcp_base_url=mcp_base_url,
        use_bge=use_bge,
        max_iterations=max_iterations
    )

    # Create StateGraph
    graph = StateGraph(PaperRAGState)

    # Add nodes
    graph.add_node("interpret", nodes.interpret_query)
    graph.add_node("retrieve", nodes.retrieve_documents)
    graph.add_node("grade_docs", nodes.grade_documents)
    graph.add_node("generate", nodes.generate_answer)
    graph.add_node("reflect", nodes.reflect_on_answer)
    graph.add_node("cite_check", nodes.enforce_citations)
    graph.add_node("prepare_retry", nodes.prepare_retry)

    # Set entry point
    graph.set_entry_point("interpret")

    # Add edges
    graph.add_conditional_edges(
        "interpret",
        route_after_interpret,
        {
            "retrieve": "retrieve",
            "complete": END
        }
    )

    graph.add_edge("retrieve", "grade_docs")

    graph.add_conditional_edges(
        "grade_docs",
        route_after_grading,
        {
            "generate": "generate",
            "retry": "prepare_retry",
            "complete": END
        }
    )

    graph.add_edge("generate", "reflect")

    graph.add_conditional_edges(
        "reflect",
        route_after_reflection,
        {
            "retry": "prepare_retry",
            "cite_check": "cite_check",
            "escalate": END,  # Human review needed
            "complete": "cite_check"
        }
    )

    graph.add_conditional_edges(
        "cite_check",
        route_after_citation_check,
        {
            "retry": "prepare_retry",
            "complete": END
        }
    )

    graph.add_edge("prepare_retry", "retrieve")

    return graph

def create_rag_executor(
    max_iterations: int = 3,
    enable_checkpointing: bool = True
):
    """
    Create executable RAG workflow with optional checkpointing

    Usage:
    ------
    executor = create_rag_executor()

    # Run workflow
    result = executor.invoke({
        "query": "What is MCP protocol?",
        "iteration_count": 0,
        "max_iterations": 3,
        "traces": [],
        "chunks": [],
        "grades": [],
        "citations": []
    })
    """

    # Build graph
    graph = build_paper_rag_graph(max_iterations=max_iterations)

    # Add checkpointing for state persistence
    if enable_checkpointing:
        checkpointer = MemorySaver()
        return graph.compile(checkpointer=checkpointer)

    return graph.compile()

# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create executor
        executor = create_rag_executor(max_iterations=3)

        # Initial state
        initial_state = {
            "query": "How does the MCP protocol implement tool calling?",
            "query_intent": None,
            "conversation_history": [],
            "chunks": [],
            "retrieval_method": "hybrid",
            "grades": [],
            "relevant_chunks": [],
            "generated_answer": None,
            "citations": [],
            "reflection": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "quality_score": 0.0,
            "citation_enforced": False,
            "ready_for_delivery": False,
            "traces": [],
            "total_tokens": 0,
            "decision": None
        }

        # Run workflow
        result = executor.invoke(initial_state)

        # Print results
        print("=" * 60)
        print("FINAL ANSWER:")
        print("=" * 60)
        print(result["generated_answer"])
        print()
        print("CITATIONS:")
        for c in result["citations"]:
            print(f"  - {c.paper_title} [{c.chunk_id}]")
        print()
        print("QUALITY SCORE:", result["quality_score"])
        print("ITERATIONS:", result["iteration_count"])
        print()
        print("EXECUTION TRACE:")
        for trace in result["traces"]:
            print(f"  {trace.node_name}: {trace.duration_ms:.0f}ms")

    asyncio.run(main())
```

### 3.5 Visual Graph Representation

```
                                    START
                                      |
                                      v
                              +---------------+
                              |   interpret   |
                              | (Query Intent)|
                              +-------+-------+
                                      |
                    +-----------------+-----------------+
                    | (unclear)                         | (clear)
                    v                                   v
                  END                          +---------------+
                                               |   retrieve   |
                                               | (Hybrid RRF) |
                                               +-------+-------+
                                                       |
                                                       v
                                               +---------------+
                                               |  grade_docs   |
                                               | (Relevance)   |
                                               +-------+-------+
                                                       |
                     +-----------------+---------------+-----------------+
                     | (no relevant)   | (has relevant)                  |
                     v                 v                                v
              +------------+    +---------------+                +------------+
              | prepare_   |    |   generate   |                |    END     |
              |   retry    |    | (Answer+Cite)|                | (give up)  |
              +-----+------+    +-------+-------+                +------------+
                    |                   |
                    |                   v
                    |           +---------------+
                    |           |   reflect     |
                    |           | (Self-Check)  |
                    |           +-------+-------+
                    |                   |
                    |    +--------------+--------------+---------------+
                    |    | (retry)      | (escalate)   | (complete)   |
                    |    v             v              v               |
                    +--->+             END    +---------------+        |
                         |                    |  cite_check   |        |
                         |                    | (Enforce)     |        |
                         |                    +-------+-------+        |
                         |                            |                |
                         |              +-------------+-------------+  |
                         |              | (enforced)  | (not enforced)| |
                         |              v             v               | |
                         |           +-----+   +------------+          | |
                         +---------->| END |   | prepare_  |<---------+ |
                                     +-----+   |   retry   |            |
                                               +------------+            |
                                                      |                  |
                                                      v                  |
                                                      +------------------+
                                                        (back to retrieve)
```

---

## 4. Integration with Existing Components

### 4.1 ChromaDB Integration

```python
"""
Integration with existing ChromaDB + BM25 hybrid retrieval
"""
import sys
sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')

from search import HybridSearcher
from config import RETRIEVAL_CONFIG

class IntegratedRetriever:
    """
    Wrapper for existing HybridSearcher with LangGraph compatibility
    """

    def __init__(self, use_bge: bool = True):
        self.searcher = HybridSearcher(use_bge=use_bge)

    def retrieve(self, query: str, top_k: int = None) -> list:
        """Retrieve chunks using hybrid search"""
        result = self.searcher.search(query, top_k=top_k)

        # Convert to Chunk format
        chunks = []
        for item in result['results']:
            chunks.append(Chunk(
                chunk_id=item['chunk_id'],
                content=item['content'],
                metadata=item['metadata'],
                score=item.get('rrf_score', 0),
                source=item.get('source', 'hybrid'),
                parent_context=item.get('parent_context', '')
            ))

        return chunks

    def get_parent_context(self, chunk_id: str) -> str:
        """Get parent chunk context"""
        return self.searcher.get_parent_context(chunk_id)
```

### 4.2 MCP Server Integration

```python
"""
Integration with existing Dual-Backend MCP Server
"""
import httpx

class MCPClient:
    """
    Client for Dual-Backend MCP Server
    Supports local Ollama and cloud DashScope
    """

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url

    async def chat(self, messages: list, use_local: bool = True) -> str:
        """Chat via MCP server"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            endpoint = "local_chat" if use_local else "cloud_chat"
            response = await client.post(
                f"{self.base_url}/mcp/{endpoint}",
                json={"messages": messages}
            )
            return response.json().get("content", "")

    async def generate(self, prompt: str, use_local: bool = True) -> str:
        """Generate via MCP server"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            endpoint = "local_generate" if use_local else "cloud_generate"
            response = await client.post(
                f"{self.base_url}/mcp/{endpoint}",
                json={"prompt": prompt}
            )
            return response.json().get("content", "")

    async def sensitive_chat(self, messages: list) -> str:
        """
        Sensitive data - force local processing
        Data never leaves the machine
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/mcp/sensitive_chat",
                json={"messages": messages}
            )
            return response.json().get("content", "")

    async def get_status(self) -> dict:
        """Get MCP server status"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/mcp/get_status")
            return response.json()
```

### 4.3 BGE Embedding Integration

```python
"""
Integration with existing BGE-large-zh embedding
"""
import sys
sys.path.append('/home/nvidia/workspace/paper/vectordb/scripts')

from embed_local import LocalEmbedding

class EmbeddingService:
    """
    Wrapper for BGE embedding with LangGraph compatibility
    """

    def __init__(self, use_bge: bool = True):
        self.embedder = LocalEmbedding(use_bge=use_bge)

    def embed(self, texts: list) -> list:
        """Generate embeddings for texts"""
        return self.embedder.encode(texts)

    def embed_query(self, query: str) -> list:
        """Embed single query"""
        return self.embedder.encode([query])[0]

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return 1024  # BGE-large-zh dimension
```

### 4.4 Complete Integration Example

```python
"""
Complete integration of all components with LangGraph
"""
from langgraph.graph import StateGraph, END

class PaperRAGSystem:
    """
    Complete Paper RAG system integrating:
    - LangGraph workflow orchestration
    - ChromaDB + BM25 hybrid retrieval
    - BGE-large-zh embedding
    - Dual-backend MCP server
    - Citation enforcement
    - Execution tracing
    """

    def __init__(
        self,
        mcp_base_url: str = "http://localhost:8080",
        use_bge: bool = True,
        prefer_local_llm: bool = True,
        max_iterations: int = 3
    ):
        # Initialize components
        self.retriever = IntegratedRetriever(use_bge=use_bge)
        self.embedder = EmbeddingService(use_bge=use_bge)
        self.mcp_client = MCPClient(mcp_base_url)
        self.prefer_local_llm = prefer_local_llm

        # Build workflow
        self.workflow = build_paper_rag_graph(
            mcp_base_url=mcp_base_url,
            use_bge=use_bge,
            max_iterations=max_iterations
        )

    async def query(
        self,
        question: str,
        conversation_history: list = None
    ) -> dict:
        """
        Execute a query through the RAG pipeline

        Returns:
        --------
        {
            "answer": str,
            "citations": List[Citation],
            "quality_score": float,
            "iterations": int,
            "traces": List[ExecutionTrace]
        }
        """
        initial_state = {
            "query": question,
            "query_intent": None,
            "conversation_history": conversation_history or [],
            "chunks": [],
            "retrieval_method": "hybrid",
            "grades": [],
            "relevant_chunks": [],
            "generated_answer": None,
            "citations": [],
            "reflection": None,
            "iteration_count": 0,
            "max_iterations": 3,
            "quality_score": 0.0,
            "citation_enforced": False,
            "ready_for_delivery": False,
            "traces": [],
            "total_tokens": 0,
            "decision": None
        }

        result = self.workflow.invoke(initial_state)

        return {
            "answer": result["generated_answer"],
            "citations": result["citations"],
            "quality_score": result["quality_score"],
            "iterations": result["iteration_count"],
            "traces": result["traces"]
        }

    async def query_with_retry(
        self,
        question: str,
        min_quality: float = 0.7
    ) -> dict:
        """
        Query with quality threshold - retry if below threshold
        """
        result = await self.query(question)

        if result["quality_score"] < min_quality:
            # Could implement additional retry logic here
            pass

        return result

# Usage
async def main():
    rag = PaperRAGSystem(
        mcp_base_url="http://localhost:8080",
        use_bge=True,
        prefer_local_llm=True
    )

    result = await rag.query("What is the MCP protocol architecture?")

    print("Answer:", result["answer"])
    print("Quality:", result["quality_score"])
    print("Citations:", len(result["citations"]))
```

---

## 5. Implementation Risks and Mitigation

### 5.1 Dependency Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LangGraph API changes | High | Medium | Pin version, abstract interface |
| ChromaDB version conflict | Medium | Low | Use existing stable version |
| LangSmith dependency | Low | Low | Optional, not required |
| Python version compatibility | Medium | Low | Target Python 3.10+ |

**Recommended Versions:**
```txt
langgraph>=0.2.0,<0.3.0
langchain-core>=0.3.0,<0.4.0
chromadb>=1.5.0,<2.0.0
sentence-transformers>=2.2.0
whoosh>=2.7.0
```

### 5.2 Learning Curve Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Team unfamiliar with LangGraph | Medium | Training session, documentation |
| StateGraph debugging complexity | Medium | LangSmith integration, logging |
| Edge case handling | High | Comprehensive test coverage |

**Recommended Training:**
1. LangGraph tutorial (2 days)
2. State machine patterns (1 day)
3. Integration with existing code (1 day)

### 5.3 Performance Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM call latency | High | Async processing, caching |
| Multiple iteration overhead | Medium | Early termination, max iteration limit |
| Memory usage for traces | Medium | Trace compression, offloading |
| Concurrency limits | Medium | Connection pooling, rate limiting |

**Performance Optimization:**
```python
# Enable caching for repeated queries
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_retrieve(query_hash: str):
    return retriever.retrieve(query_hash)

# Async batch processing
async def batch_process_queries(queries: list):
    tasks = [rag.query(q) for q in queries]
    return await asyncio.gather(*tasks)
```

### 5.4 Version Compatibility Risks

| Component | Current | Recommended | Risk |
|-----------|---------|-------------|------|
| Python | 3.12 | 3.10+ | Low |
| LangGraph | N/A | 0.2.x | Medium |
| LangChain Core | N/A | 0.3.x | Medium |
| ChromaDB | 1.5.9 | 1.5.x | Low |
| Whoosh | 2.7.x | 2.7.x | Low |

---

## 6. Alternative Solutions

### 6.1 Alternative 1: Pure Custom Implementation

**Approach:** Build complete agent framework without LangChain/LangGraph

```python
"""
Custom State Machine for RAG - No External Framework
"""
from enum import Enum
from dataclasses import dataclass
from typing import Callable, Dict, Any

class State(Enum):
    START = "start"
    INTERPRET = "interpret"
    RETRIEVE = "retrieve"
    GRADE = "grade"
    GENERATE = "generate"
    REFLECT = "reflect"
    END = "end"

@dataclass
class Transition:
    from_state: State
    to_state: State
    condition: Callable[[dict], bool]

class CustomRAGStateMachine:
    """
    Simple state machine without LangGraph dependency
    """

    def __init__(self):
        self.transitions = [
            Transition(State.START, State.INTERPRET, lambda s: True),
            Transition(State.INTERPRET, State.RETRIEVE, lambda s: s.get("intent") != "unclear"),
            Transition(State.INTERPRET, State.END, lambda s: s.get("intent") == "unclear"),
            Transition(State.RETRIEVE, State.GRADE, lambda s: True),
            Transition(State.GRADE, State.GENERATE, lambda s: len(s.get("relevant_chunks", [])) > 0),
            Transition(State.GRADE, State.RETRIEVE, lambda s: s["iteration"] < s["max_iter"]),
            Transition(State.GENERATE, State.REFLECT, lambda s: True),
            Transition(State.REFLECT, State.END, lambda s: s.get("quality", 0) >= 0.7),
            Transition(State.REFLECT, State.RETRIEVE, lambda s: s["iteration"] < s["max_iter"]),
        ]

    def run(self, initial_state: dict, nodes: Dict[State, Callable]) -> dict:
        state = initial_state.copy()
        current = State.START

        while current != State.END:
            # Execute node
            if current in nodes:
                state = nodes[current](state)

            # Find next transition
            for t in self.transitions:
                if t.from_state == current and t.condition(state):
                    current = t.to_state
                    break
            else:
                current = State.END  # No valid transition

        return state
```

**Pros:**
- Zero external dependency risk
- Full control over implementation
- Simpler debugging
- Smaller footprint

**Cons:**
- More code to maintain
- No visualization tools
- No checkpointing built-in
- Manual state management

### 6.2 Alternative 2: LiteLLM + Custom Orchestration (PaperQA2 Style)

**Approach:** Use LiteLLM for LLM abstraction + custom workflow

```python
"""
LiteLLM-based RAG - Similar to PaperQA2 approach
"""
from litellm import completion
from typing import Dict, Any

class LiteLLMRAG:
    """
    RAG using LiteLLM for LLM calls and custom orchestration
    """

    def __init__(self, model: str = "ollama/qwen3.6:35b"):
        self.model = model
        self.history = []

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate using LiteLLM (supports many providers)"""
        response = await completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content

    async def run_workflow(self, query: str, max_iterations: int = 3):
        """Custom workflow without framework"""
        state = {"query": query, "iteration": 0}

        # Step 1: Retrieve
        state["chunks"] = self.retrieve(query)

        # Step 2: Grade and filter
        state["relevant"] = await self.grade(state["chunks"])

        # Step 3: Generate with retry
        for i in range(max_iterations):
            state["answer"] = await self.generate(
                self._build_prompt(query, state["relevant"])
            )

            # Step 4: Self-reflect
            quality = await self.evaluate_quality(state["answer"], state["relevant"])

            if quality > 0.7:
                break

            # Refine query
            query = await self.refine_query(query, state["answer"])
            state["iteration"] += 1

        return state
```

**Pros:**
- LiteLLM provides excellent LLM abstraction
- Multi-provider support (OpenAI, Anthropic, Ollama, etc.)
- Simple, linear workflow
- PaperQA2 proven pattern

**Cons:**
- No built-in state management
- Manual retry logic
- No visualization
- Less structured than LangGraph

### 6.3 Alternative Comparison Matrix

| Criterion | LangGraph | Custom State Machine | LiteLLM + Custom |
|-----------|-----------|---------------------|------------------|
| **Development Time** | Medium | High | Low |
| **Flexibility** | High | Highest | High |
| **Learning Curve** | Steep | Flat | Medium |
| **Maintenance** | Low | High | Medium |
| **Visualization** | Excellent | None | None |
| **State Persistence** | Built-in | Manual | Manual |
| **Debugging** | Good | Best | Good |
| **Dependency Risk** | Medium | None | Low |
| **Proven Production** | Growing | N/A | High (PaperQA2) |

### 6.4 Recommendation

**Primary Recommendation: LangGraph with Custom Components**

Rationale:
1. Your requirements (reflection loops, iteration, state tracking) map directly to LangGraph's strengths
2. Custom implementation would require significant effort to achieve equivalent functionality
3. LiteLLM approach lacks state management for complex workflows

**Fallback Recommendation: LiteLLM + Custom Orchestration**

If LangGraph proves problematic, adopt PaperQA2's approach:
- Use LiteLLM for LLM abstraction
- Build simple retry loop for reflection
- Maintain our existing retrieval components

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goals:**
- Set up LangGraph environment
- Integrate with existing retrieval components
- Basic workflow without reflection

**Tasks:**
1. Install LangGraph and dependencies
2. Define state schema
3. Implement interpret and retrieve nodes
4. Test basic retrieval flow
5. Integration tests with existing ChromaDB

**Deliverables:**
- Working linear RAG workflow
- Integration tests passing
- Basic documentation

### Phase 2: Reflection Loop (Week 3-4)

**Goals:**
- Implement document grading
- Add self-reflection node
- Conditional edge routing

**Tasks:**
1. Implement grade_documents node
2. Implement reflect_on_answer node
3. Add conditional edges for retry
4. Test reflection loop with real queries
5. Tune quality thresholds

**Deliverables:**
- Working reflection loop
- Quality metrics logging
- Iteration limits enforced

### Phase 3: Citation Enforcement (Week 5-6)

**Goals:**
- Implement citation extraction
- Add citation validation gate
- Integrate with existing metadata

**Tasks:**
1. Implement citation extraction logic
2. Add citation validation node
3. Map citations to source chunks
4. Test citation coverage
5. Handle edge cases (no sources, multiple sources)

**Deliverables:**
- Citation-enforced answers
- Citation quality metrics
- Source tracing

### Phase 4: Execution Tracing (Week 7-8)

**Goals:**
- Comprehensive trace logging
- Performance metrics
- Feedback integration

**Tasks:**
1. Enhance trace data collection
2. Add timing metrics
3. Implement trace storage
4. Build trace analysis dashboard
5. Integrate traces into retrieval improvement

**Deliverables:**
- Complete execution traces
- Performance dashboard
- Feedback loop documentation

### Phase 5: Production Hardening (Week 9-10)

**Goals:**
- Error handling
- Monitoring and alerting
- Documentation

**Tasks:**
1. Add comprehensive error handling
2. Implement circuit breakers
3. Add monitoring endpoints
4. Write user documentation
5. Write developer documentation

**Deliverables:**
- Production-ready system
- Monitoring dashboard
- Complete documentation

---

## 8. Architecture Decision Record

```markdown
# ADR-002: LangGraph Integration for Agentic RAG

## Status
Proposed

## Context

We have a working Paper RAG system with:
- ChromaDB vector storage
- BGE-large-zh embedding
- Hybrid retrieval (Vector + BM25 + RRF)
- Parent-child chunking
- Dual-backend MCP server (local/cloud)

We need to add:
- Agentic iterative retrieval
- Self-reflection self-correction
- Citation enforcement
- Execution trace feedback

## Decision

We will adopt LangGraph for workflow orchestration with the following approach:

1. **Use LangGraph StateGraph** for workflow management
   - Native support for cyclic reflection loops
   - Built-in state management
   - Conditional edges for routing logic

2. **Retain custom implementations** for:
   - Hybrid retrieval (existing HybridSearcher)
   - Embedding (existing LocalEmbedding)
   - LLM calls (existing MCP server)
   - Citation validation (new component)

3. **Build new components**:
   - Document grader node
   - Reflection evaluator node
   - Citation validator node
   - Execution tracer

## Consequences

### Positive
- Clear mental model for workflow
- Native support for reflection loops
- Built-in checkpointing for fault tolerance
- Visualization via LangSmith
- Maintains existing investment in retrieval components

### Negative
- New dependency (LangGraph)
- Learning curve for team
- Potential version compatibility issues
- Adds complexity to the stack

### Risks and Mitigations
- API changes: Pin version, abstract interface
- Learning curve: Training, documentation
- Performance: Async processing, caching

## Alternatives Considered

1. **Pure Custom Implementation**
   - Rejected: Too much code to maintain for complex workflows

2. **LangChain Chains**
   - Rejected: Cannot express cyclic reflection loops

3. **LiteLLM + Custom Orchestration**
   - Rejected: Lacks state management for complex workflows
   - Fallback option if LangGraph proves problematic

## Implementation Timeline

- Phase 1: Foundation (Week 1-2)
- Phase 2: Reflection Loop (Week 3-4)
- Phase 3: Citation Enforcement (Week 5-6)
- Phase 4: Execution Tracing (Week 7-8)
- Phase 5: Production Hardening (Week 9-10)

Total: 10 weeks to production-ready system.
```

---

## 9. Summary

### Key Recommendations

1. **Adopt LangGraph** for workflow orchestration - it provides the right abstraction for cyclic agentic workflows

2. **Retain existing components** - HybridSearcher, LocalEmbedding, and MCP server are working well

3. **Build new nodes** for grading, reflection, and citation - these are domain-specific and should be custom

4. **Implement gradually** - Start with linear flow, add reflection, then citation enforcement

5. **Have fallback plan** - If LangGraph proves problematic, fall back to LiteLLM + custom orchestration

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Answer Quality | >0.7 | Reflection score |
| Citation Coverage | >90% | % claims cited |
| Retrieval Precision | >0.8 | Graded relevance |
| Latency P95 | <5s | Execution trace |
| Iteration Count | <3 | Average iterations |

### Next Steps

1. Review this document with the team
2. Set up development environment with LangGraph
3. Implement Phase 1 (foundation)
4. Test with real queries from your paper corpus
5. Iterate based on feedback

---

**Document Version**: 1.0
**Last Updated**: 2026-05-24
**Author**: Software Architect Agent