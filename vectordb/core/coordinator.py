"""
Coordinator Pattern Implementation
借鉴Claude Usage Tracker的Coordinator模式，应用到论文知识库Agent系统

设计模式:
- UsageRefreshCoordinator → 状态协调
- WindowCoordinator → 多窗口管理
- StatusBarUIManager → UI管理

应用到论文知识库:
- RetrievalCoordinator: 检索协调
- GenerationCoordinator: 生成协调
- QualityCoordinator: 质量检查协调
- UsageTrackingCoordinator: 使用追踪协调
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class CoordinatorState(Enum):
    """协调器状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class PaceLevel(Enum):
    """使用节奏等级 (借鉴Claude Usage Tracker 6-tier pace system)"""
    VERY_SLOW = 1      # < 20%
    SLOW = 2           # 20-40%
    NORMAL = 3         # 40-60%
    FAST = 4           # 60-80%
    VERY_FAST = 5      # 80-90%
    EXTREME = 6        # > 90%


@dataclass
class CoordinatorContext:
    """协调器上下文"""
    session_id: str
    query: str
    start_time: datetime
    state: CoordinatorState = CoordinatorState.IDLE
    current_step: str = ""
    progress: float = 0.0
    metrics: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class BaseCoordinator:
    """基础协调器 (借鉴Claude Usage Tracker Coordinator模式)"""

    def __init__(self, name: str):
        self.name = name
        self.state = CoordinatorState.IDLE
        self.contexts: Dict[str, CoordinatorContext] = {}
        self.callbacks: List[Callable] = []
        self._lock = asyncio.Lock()

    async def start(self, session_id: str, **kwargs) -> CoordinatorContext:
        """启动协调"""
        context = CoordinatorContext(
            session_id=session_id,
            query=kwargs.get('query', ''),
            start_time=datetime.now(),
            state=CoordinatorState.RUNNING
        )
        self.contexts[session_id] = context
        await self._notify_callbacks('start', context)
        return context

    async def update_progress(self, session_id: str, step: str, progress: float):
        """更新进度"""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            context.current_step = step
            context.progress = progress
            await self._notify_callbacks('progress', context)

    async def complete(self, session_id: str, result: Dict):
        """完成协调"""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            context.state = CoordinatorState.COMPLETED
            context.metrics = result
            await self._notify_callbacks('complete', context)

    async def error(self, session_id: str, error_msg: str):
        """错误处理"""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            context.state = CoordinatorState.ERROR
            context.errors.append(error_msg)
            await self._notify_callbacks('error', context)

    def register_callback(self, callback: Callable):
        """注册回调"""
        self.callbacks.append(callback)

    async def _notify_callbacks(self, event: str, context: CoordinatorContext):
        """通知所有回调"""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, context)
                else:
                    callback(event, context)
            except Exception as e:
                print(f"Callback error: {e}")


class RetrievalCoordinator(BaseCoordinator):
    """检索协调器

    借鉴Claude Usage Tracker的UsageRefreshCoordinator设计:
    - 协调向量检索和BM25检索
    - RRF融合
    - 结果评分过滤
    """

    def __init__(self):
        super().__init__("RetrievalCoordinator")
        self.vector_results: List[Dict] = []
        self.bm25_results: List[Dict] = []
        self.fused_results: List[Dict] = []

    async def coordinate_retrieval(
        self,
        session_id: str,
        query: str,
        vector_search_func: Callable,
        bm25_search_func: Callable,
        top_k: int = 20
    ) -> List[Dict]:
        """协调混合检索"""

        context = await self.start(session_id, query=query)

        try:
            # Step 1: 向量检索 (借鉴UsageRefreshCoordinator的刷新协调)
            await self.update_progress(session_id, "vector_search", 0.2)
            self.vector_results = await vector_search_func(query, top_k)

            # Step 2: BM25检索
            await self.update_progress(session_id, "bm25_search", 0.4)
            self.bm25_results = await bm25_search_func(query, top_k)

            # Step 3: RRF融合 (Reciprocal Rank Fusion)
            await self.update_progress(session_id, "rrf_fusion", 0.6)
            self.fused_results = self._rrf_fusion(self.vector_results, self.bm25_results)

            # Step 4: 评分过滤
            await self.update_progress(session_id, "grade_filter", 0.8)
            filtered_results = [r for r in self.fused_results if r.get('rrf_score', 0) > 0.5]

            # Step 5: 完成
            await self.update_progress(session_id, "complete", 1.0)
            await self.complete(session_id, {
                'vector_count': len(self.vector_results),
                'bm25_count': len(self.bm25_results),
                'fused_count': len(self.fused_results),
                'filtered_count': len(filtered_results)
            })

            return filtered_results

        except Exception as e:
            await self.error(session_id, str(e))
            return []

    def _rrf_fusion(self, vector_results: List[Dict], bm25_results: List[Dict], k: int = 60) -> List[Dict]:
        """RRF融合算法"""
        fused_scores = {}

        # 向量检索贡献
        for rank, result in enumerate(vector_results):
            chunk_id = result.get('chunk_id')
            if chunk_id:
                fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (k + rank + 1)

        # BM25检索贡献
        for rank, result in enumerate(bm25_results):
            chunk_id = result.get('chunk_id')
            if chunk_id:
                fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (k + rank + 1)

        # 合并结果
        all_results = {}
        for result in vector_results + bm25_results:
            chunk_id = result.get('chunk_id')
            if chunk_id and chunk_id not in all_results:
                all_results[chunk_id] = result

        # 添加RRF分数
        fused_results = []
        for chunk_id, score in fused_scores.items():
            if chunk_id in all_results:
                result = all_results[chunk_id].copy()
                result['rrf_score'] = score
                fused_results.append(result)

        # 按RRF分数排序
        fused_results.sort(key=lambda x: x.get('rrf_score', 0), reverse=True)
        return fused_results


class GenerationCoordinator(BaseCoordinator):
    """生成协调器

    借鉴Claude Usage Tracker的WindowCoordinator设计:
    - 协调LLM调用
    - Prompt组装
    - 流式输出管理
    """

    def __init__(self):
        super().__init__("GenerationCoordinator")
        self.prompt_template = None
        self.raw_output = ""
        self.formatted_output = ""

    async def coordinate_generation(
        self,
        session_id: str,
        query: str,
        context_chunks: List[Dict],
        llm_call_func: Callable,
        prompt_template: str
    ) -> str:
        """协调生成"""

        ctx = await self.start(session_id, query=query)

        try:
            # Step 1: Prompt组装
            await self.update_progress(session_id, "prompt_assemble", 0.2)
            assembled_prompt = self._assemble_prompt(prompt_template, query, context_chunks)

            # Step 2: LLM调用
            await self.update_progress(session_id, "llm_call", 0.5)
            self.raw_output = await llm_call_func(assembled_prompt)

            # Step 3: 格式化输出
            await self.update_progress(session_id, "format_output", 0.8)
            self.formatted_output = self._format_output(self.raw_output, context_chunks)

            # Step 4: 完成
            await self.update_progress(session_id, "complete", 1.0)
            await self.complete(session_id, {
                'prompt_length': len(assembled_prompt),
                'output_length': len(self.formatted_output),
                'chunks_used': len(context_chunks)
            })

            return self.formatted_output

        except Exception as e:
            await self.error(session_id, str(e))
            return ""

    def _assemble_prompt(self, template: str, query: str, chunks: List[Dict]) -> str:
        """组装Prompt (Anti-Lost-in-Middle)"""
        # 重要内容放首位和末尾
        context = "\n\n---\n\n".join([
            f"[{i+1}] {c.get('content', '')}"
            for i, c in enumerate(chunks[:10])
        ])
        return template.replace('{query}', query).replace('{context}', context)

    def _format_output(self, raw_output: str, chunks: List[Dict]) -> str:
        """格式化输出 (添加Citation)"""
        # 简化格式化，实际应调用output_formatter
        return raw_output


class QualityCoordinator(BaseCoordinator):
    """质量协调器

    借鉴Claude Usage Tracker的StatusBarUIManager设计:
    - 幻觉检测
    - Citation验证
    - 支撑度评估
    """

    def __init__(self):
        super().__init__("QualityCoordinator")
        self.hallucination_risk = 0.0
        self.citation_accuracy = 0.0
        self.support_score = 0.0

    async def coordinate_quality_check(
        self,
        session_id: str,
        output: str,
        chunks: List[Dict]
    ) -> Dict:
        """协调质量检查"""

        await self.start(session_id)

        try:
            # Step 1: 幻觉检测
            await self.update_progress(session_id, "hallucination_check", 0.3)
            self.hallucination_risk = self._detect_hallucination(output, chunks)

            # Step 2: Citation验证
            await self.update_progress(session_id, "citation_check", 0.6)
            self.citation_accuracy = self._verify_citations(output, chunks)

            # Step 3: 支撑度评估
            await self.update_progress(session_id, "support_check", 0.9)
            self.support_score = self._evaluate_support(output, chunks)

            # Step 4: 完成
            await self.update_progress(session_id, "complete", 1.0)
            result = {
                'hallucination_risk': self.hallucination_risk,
                'citation_accuracy': self.citation_accuracy,
                'support_score': self.support_score,
                'quality_level': self._get_quality_level()
            }
            await self.complete(session_id, result)

            return result

        except Exception as e:
            await self.error(session_id, str(e))
            return {'hallucination_risk': 1.0, 'citation_accuracy': 0.0, 'support_score': 0.0}

    def _detect_hallucination(self, output: str, chunks: List[Dict]) -> float:
        """幻觉检测 (简化版)"""
        # 检查输出是否包含chunk内容
        chunk_contents = [c.get('content', '') for c in chunks]
        coverage = sum(1 for c in chunk_contents if any(word in output for word in c.split()[:5]))
        return 1.0 - (coverage / len(chunks) if chunks else 1.0)

    def _verify_citations(self, output: str, chunks: List[Dict]) -> float:
        """Citation验证"""
        # 检查是否包含chunk_id引用
        chunk_ids = [c.get('chunk_id') for c in chunks]
        citations_found = sum(1 for id in chunk_ids if id and id in output)
        return citations_found / len(chunks) if chunks else 0.0

    def _evaluate_support(self, output: str, chunks: List[Dict]) -> float:
        """支撑度评估"""
        # 基于citation和幻觉的综合评分
        return self.citation_accuracy * (1 - self.hallucination_risk)

    def _get_quality_level(self) -> str:
        """获取质量等级"""
        if self.hallucination_risk < 0.1:
            return "excellent"
        elif self.hallucination_risk < 0.3:
            return "good"
        elif self.hallucination_risk < 0.5:
            return "acceptable"
        else:
            return "poor"


class UsageTrackingCoordinator(BaseCoordinator):
    """使用追踪协调器

    直接借鉴Claude Usage Tracker的核心设计:
    - Session追踪 (5小时窗口)
    - Weekly限制追踪
    - Token消耗追踪
    - Pace System (6-tier)
    """

    def __init__(self):
        super().__init__("UsageTrackingCoordinator")
        self.session_start = datetime.now()
        self.session_duration = 5 * 60 * 60  # 5小时 (秒)
        self.total_tokens_used = 0
        self.api_calls = 0
        self.estimated_cost = 0.0

    def get_session_remaining(self) -> float:
        """获取Session剩余时间"""
        elapsed = (datetime.now() - self.session_start).total_seconds()
        remaining = max(0, self.session_duration - elapsed)
        return remaining / 60  # 返回分钟

    def get_pace_level(self, context_percentage: float) -> PaceLevel:
        """获取使用节奏等级 (借鉴Claude Usage Tracker 6-tier pace)"""
        if context_percentage < 20:
            return PaceLevel.VERY_SLOW
        elif context_percentage < 40:
            return PaceLevel.SLOW
        elif context_percentage < 60:
            return PaceLevel.NORMAL
        elif context_percentage < 80:
            return PaceLevel.FAST
        elif context_percentage < 90:
            return PaceLevel.VERY_FAST
        else:
            return PaceLevel.EXTREME

    def get_pace_indicator(self, pace: PaceLevel) -> str:
        """获取Pace指示符号 (借鉴Claude Usage Tracker图标系统)"""
        indicators = {
            PaceLevel.VERY_SLOW: "○",   # 灰色
            PaceLevel.SLOW: "◐",        # 浅色
            PaceLevel.NORMAL: "●",      # 蓝色
            PaceLevel.FAST: "◈",        # 绿色
            PaceLevel.VERY_FAST: "◆",   # 黄色
            PaceLevel.EXTREME: "✦",     # 红色
        }
        return indicators.get(pace, "●")

    async def track_usage(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> Dict:
        """追踪使用"""

        self.total_tokens_used += input_tokens + output_tokens
        self.api_calls += 1
        self.estimated_cost += cost

        await self.complete(session_id, {
            'session_remaining_minutes': self.get_session_remaining(),
            'total_tokens': self.total_tokens_used,
            'api_calls': self.api_calls,
            'estimated_cost': self.estimated_cost
        })

        return {
            'session_remaining': self.get_session_remaining(),
            'tokens_used': input_tokens + output_tokens,
            'pace': self.get_pace_indicator(
                self.get_pace_level(self.api_calls / 100 * 100)  # 简化计算
            )
        }

    def is_peak_hours(self) -> bool:
        """判断是否Peak Hours (借鉴Claude Usage Tracker v3.1.0)"""
        # Peak Hours: 上午9-12点，下午2-6点
        now = datetime.now()
        hour = now.hour
        return (9 <= hour <= 12) or (14 <= hour <= 18)

    def get_peak_hours_remaining(self) -> int:
        """获取Peak Hours剩余时间"""
        if not self.is_peak_hours():
            return 0

        now = datetime.now()
        hour = now.hour

        if hour <= 12:
            return (12 - hour) * 60 - now.minute
        else:
            return (18 - hour) * 60 - now.minute


# ═══════════════════════════════════════════════════════════════════════════════
# Master Coordinator (借鉴WindowCoordinator)
# ═══════════════════════════════════════════════════════════════════════════════

class MasterCoordinator:
    """主协调器 - 协调所有子协调器"""

    def __init__(self):
        self.retrieval = RetrievalCoordinator()
        self.generation = GenerationCoordinator()
        self.quality = QualityCoordinator()
        self.usage = UsageTrackingCoordinator()

        # 注册全局回调
        self._register_global_callbacks()

    def _register_global_callbacks(self):
        """注册全局回调 (借鉴StatusBarUIManager)"""
        for coordinator in [self.retrieval, self.generation, self.quality, self.usage]:
            coordinator.register_callback(self._global_event_handler)

    async def _global_event_handler(self, event: str, context: CoordinatorContext):
        """全局事件处理"""
        # 可用于更新Statusline、记录审计日志等
        print(f"[{context.session_id}] {event}: {context.current_step} ({context.progress*100:.0f}%)")

    async def run_full_pipeline(
        self,
        session_id: str,
        query: str,
        vector_search_func: Callable,
        bm25_search_func: Callable,
        llm_call_func: Callable,
        prompt_template: str
    ) -> Dict:
        """运行完整Pipeline"""

        # 1. 检索
        chunks = await self.retrieval.coordinate_retrieval(
            session_id, query, vector_search_func, bm25_search_func
        )

        # 2. 生成
        output = await self.generation.coordinate_generation(
            session_id, query, chunks, llm_call_func, prompt_template
        )

        # 3. 质量检查
        quality_result = await self.quality.coordinate_quality_check(
            session_id, output, chunks
        )

        return {
            'chunks': chunks,
            'output': output,
            'quality': quality_result,
            'usage': {
                'session_remaining': self.usage.get_session_remaining(),
                'peak_hours': self.usage.is_peak_hours()
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 测试示例
# ═══════════════════════════════════════════════════════════════════════════════

async def mock_vector_search(query: str, top_k: int) -> List[Dict]:
    """模拟向量检索"""
    await asyncio.sleep(0.1)
    return [{'chunk_id': f'vec_{i}', 'content': f'Vector content {i}', 'score': 0.9-i*0.1} for i in range(top_k)]

async def mock_bm25_search(query: str, top_k: int) -> List[Dict]:
    """模拟BM25检索"""
    await asyncio.sleep(0.1)
    return [{'chunk_id': f'bm25_{i}', 'content': f'BM25 content {i}', 'score': 0.8-i*0.05} for i in range(top_k)]

async def mock_llm_call(prompt: str) -> str:
    """模拟LLM调用"""
    await asyncio.sleep(0.2)
    return "This is a generated response based on the context."

async def test_coordinator():
    """测试协调器"""
    master = MasterCoordinator()

    result = await master.run_full_pipeline(
        session_id="test-001",
        query="What is Transformer?",
        vector_search_func=mock_vector_search,
        bm25_search_func=mock_bm25_search,
        llm_call_func=mock_llm_call,
        prompt_template="Query: {query}\nContext: {context}\nAnswer:"
    )

    print("\n" + "="*60)
    print("Pipeline Result:")
    print("="*60)
    print(f"Chunks retrieved: {len(result['chunks'])}")
    print(f"Output length: {len(result['output'])}")
    print(f"Quality: {result['quality']}")
    print(f"Usage: {result['usage']}")

    # 测试Usage Tracker
    usage = UsageTrackingCoordinator()
    print(f"\nSession remaining: {usage.get_session_remaining():.1f} minutes")
    print(f"Peak hours: {usage.is_peak_hours()}")
    print(f"Pace indicator: {usage.get_pace_indicator(PaceLevel.NORMAL)}")


if __name__ == "__main__":
    asyncio.run(test_coordinator())