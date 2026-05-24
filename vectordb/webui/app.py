"""
WebUI Dashboard - 论文知识库RAG系统

使用Gradio实现的轻量级Web界面，包含：
- Tab 1: 论文查询 (检索结果展示)
- Tab 2: Pipeline监控 (四阶段流程可视化)
- Tab 3: Agent状态 (工具注册列表)
- Tab 4: 质量指标 (评分趋势图表)
"""

import gradio as gr
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目路径
sys.path.append('/home/nvidia/workspace/paper/vectordb')
sys.path.append('/home/nvidia/workspace/paper/vectordb/agents')
sys.path.append('/home/nvidia/workspace/paper/vectordb/core')

from specialized_agents import SpecializedAgentOrchestrator, create_orchestrator


class WebUIDashboard:
    """WebUI Dashboard 控制器"""

    def __init__(self):
        self.orchestrator = None
        self.current_result = None
        self.pipeline_state = {
            "retrieval": "pending",
            "analysis": "pending",
            "qa": "pending",
            "code": "pending"
        }
        self.quality_history = []

    def init_orchestrator(self):
        """延迟初始化协调器"""
        if self.orchestrator is None:
            self.orchestrator = create_orchestrator("webui-session")
        return self.orchestrator

    # ==================== Tab 1: 论文查询 ====================

    def query_papers(self, query: str, top_k: int, need_code: bool) -> tuple:
        """
        执行论文查询

        Returns:
            (检索结果, 分析摘要, 代码展示, 状态信息)
        """
        if not query.strip():
            return "请输入查询内容", "", "", ""

        try:
            orchestrator = self.init_orchestrator()

            # 重置Pipeline状态
            self.pipeline_state = {
                "retrieval": "running",
                "analysis": "pending",
                "qa": "pending",
                "code": "pending"
            }

            # 运行Pipeline
            result = orchestrator.run_pipeline(
                query=query,
                top_k=top_k,
                need_code=need_code
            )

            self.current_result = result

            # 格式化检索结果
            retrieval_text = self._format_retrieval_results(
                result.get("retrieval", {})
            )

            # 格式化分析摘要
            analysis_text = self._format_analysis_results(
                result.get("analysis", {})
            )

            # 格式化代码结果
            code_text = self._format_code_results(
                result.get("code_reproduction", {})
            )

            # 状态信息
            status_text = self._format_status(result)

            return retrieval_text, analysis_text, code_text, status_text

        except Exception as e:
            error_msg = f"查询出错: {str(e)}"
            return error_msg, "", "", error_msg

    def _format_retrieval_results(self, retrieval: Dict) -> str:
        """格式化检索结果"""
        if not retrieval:
            return "无检索结果"

        results = retrieval.get("results", [])
        metrics = retrieval.get("metrics", {})

        text = f"## 检索统计\n"
        text += f"- 总数: {metrics.get('total', 0)} 篇\n"
        text += f"- 平均评分: {metrics.get('avg_score', 0):.3f}\n"
        text += f"- 最高评分: {metrics.get('max_score', 0):.3f}\n"
        text += f"- 覆盖率: {metrics.get('coverage', 0):.1%}\n\n"

        text += "## 检索结果列表\n"
        for i, r in enumerate(results[:10], 1):
            score = r.get("rrf_score", r.get("score", 0))
            content = r.get("content", r.get("text", ""))[:200]
            source = r.get("source", r.get("paper_id", "未知"))

            text += f"### [{i}] 评分: {score:.3f}\n"
            text += f"来源: {source}\n"
            text += f"内容摘要: {content}...\n\n"

        return text

    def _format_analysis_results(self, analysis: Dict) -> str:
        """格式化分析结果"""
        if not analysis:
            return "无分析结果"

        summary = analysis.get("summary", "")
        concepts = analysis.get("concepts", [])
        formulas = analysis.get("formulas", [])

        text = f"## 餐巾纸摘要\n{summary}\n\n"

        if concepts:
            text += "## 核心概念\n"
            for c in concepts[:10]:
                text += f"- {c}\n"
            text += "\n"

        if formulas:
            text += "## 公式提取\n"
            for f in formulas[:5]:
                if f.get("type") == "latex":
                    text += f"- LaTeX: `{f.get('content', '')}`\n"
                elif f.get("type") == "numbered":
                    text += f"- 公式({f.get('number', '')}): {f.get('content', '')}\n"
                elif f.get("type") == "mapping":
                    text += f"- 映射: {f.get('from', '')} -> {f.get('to', '')}\n"
            text += "\n"

        return text

    def _format_code_results(self, code: Optional[Dict]) -> str:
        """格式化代码结果"""
        if not code:
            return "未生成代码"

        modules = code.get("code_modules", [])
        is_runnable = code.get("is_runnable", False)

        text = f"## 代码模块 ({len(modules)} 个)\n"
        text += f"可运行状态: {'是' if is_runnable else '否'}\n\n"

        for m in modules:
            name = m.get("name", "unknown.py")
            code_type = m.get("type", "unknown")
            code_content = m.get("code", "")

            text += f"### {name} ({code_type})\n"
            text += f"```python\n{code_content[:500]}...\n```\n\n"

        return text

    def _format_status(self, result: Dict) -> str:
        """格式化状态信息"""
        qa = result.get("quality_assurance", {})

        text = "## Pipeline 状态\n"
        text += "- Retrieval: completed\n"
        text += "- Analysis: completed\n"
        text += "- QA: completed\n"
        text += "- Code: completed (如请求)\n\n"

        text += "## 质量验证\n"
        text += f"- 质量评分: {qa.get('quality_score', 0)}\n"
        text += f"- 通过状态: {'是' if qa.get('is_passed', False) else '否'}\n"

        risks = qa.get("risks", [])
        if risks:
            text += "\n### 风险告警\n"
            for r in risks:
                text += f"- {r}\n"

        suggestions = qa.get("suggestions", [])
        if suggestions:
            text += "\n### 修正建议\n"
            for s in suggestions:
                text += f"- {s}\n"

        return text

    # ==================== Tab 2: Pipeline监控 ====================

    def get_pipeline_status(self) -> str:
        """获取Pipeline状态"""
        status_map = {
            "pending": "pending",
            "running": "running",
            "completed": "completed",
            "error": "error"
        }

        stages = [
            ("1. 检索", self.pipeline_state.get("retrieval", "pending")),
            ("2. 分析", self.pipeline_state.get("analysis", "pending")),
            ("3. 质量", self.pipeline_state.get("qa", "pending")),
            ("4. 代码", self.pipeline_state.get("code", "pending"))
        ]

        text = "## 四阶段流程状态\n\n"

        for stage_name, state in stages:
            icon = self._get_status_icon(state)
            text += f"{icon} **{stage_name}**: {state}\n\n"

        if self.current_result:
            text += "---\n\n"
            text += "### 完成时间\n"
            text += f"{datetime.now().strftime('%H:%M:%S')}\n"

        return text

    def _get_status_icon(self, state: str) -> str:
        """获取状态图标"""
        icons = {
            "pending": "gray",
            "running": "yellow",
            "completed": "green",
            "error": "red"
        }
        return f"({icons.get(state, 'gray')})"

    def refresh_pipeline(self) -> str:
        """刷新Pipeline状态"""
        return self.get_pipeline_status()

    # ==================== Tab 3: Agent状态 ====================

    def get_agent_status(self) -> str:
        """获取Agent状态"""
        try:
            orchestrator = self.init_orchestrator()
            status = orchestrator.get_status()

            text = "## Agent 协调器状态\n\n"
            text += f"- Session ID: {status.get('memory_session', 'unknown')}\n\n"

            text += "### 已注册工具\n"
            tools = status.get("registered_tools", [])
            for tool in tools:
                text += f"- {tool}\n"

            text += "\n### 工作流状态\n"
            wf = status.get("workflow_state", {})
            for stage, state in wf.items():
                text += f"- {stage}: {state}\n"

            text += "\n### 工作记忆\n"
            memory = orchestrator.memory.get_working_memory()
            for m in memory[-5:]:
                role = m.get("role", "unknown")
                content = m.get("content", "")[:50]
                text += f"- [{role}]: {content}...\n"

            return text

        except Exception as e:
            return f"获取状态出错: {str(e)}"

    def get_tools_list(self) -> str:
        """获取工具详细列表"""
        try:
            orchestrator = self.init_orchestrator()
            schemas = orchestrator.registry.get_all_schemas()

            text = "## 工具注册详情\n\n"

            for name, schema in schemas.items():
                text += f"### {name}\n"
                desc = schema.get("description", "")
                text += f"描述: {desc}\n\n"

                params = schema.get("parameters", {})
                props = params.get("properties", {})
                required = params.get("required", [])

                if props:
                    text += "参数:\n"
                    for param_name, param_info in props.items():
                        req = " (必需)" if param_name in required else ""
                        param_desc = param_info.get("description", "")
                        param_type = param_info.get("type", "")
                        text += f"- `{param_name}` ({param_type}){req}: {param_desc}\n"
                    text += "\n"

            return text

        except Exception as e:
            return f"获取工具列表出错: {str(e)}"

    # ==================== Tab 4: 质量指标 ====================

    def get_quality_metrics(self) -> tuple:
        """获取质量指标图表"""
        if not self.current_result:
            return "无数据", "无数据", "无数据"

        qa = self.current_result.get("quality_assurance", {})

        # 质量评分
        quality_score = qa.get("quality_score", 0)
        self.quality_history.append(quality_score)

        # 幻觉风险
        hallucination = qa.get("hallucination", {})
        hallucination_risk = hallucination.get("risk_level", "unknown")
        support_rate = hallucination.get("support_rate", 1.0)

        # 引用准确率
        citations = qa.get("citations", {})
        citation_accuracy = citations.get("accuracy", 1.0)

        # 格式化输出
        score_text = f"## 质量评分\n"
        score_text += f"当前评分: **{quality_score}**\n\n"
        score_text += "### 历史趋势\n"
        for i, s in enumerate(self.quality_history[-10:], 1):
            score_text += f"{i}. {s}\n"

        hallucination_text = f"## 幻觉风险\n"
        hallucination_text += f"- 风险等级: **{hallucination_risk}**\n"
        hallucination_text += f"- 支撑率: {support_rate:.2%}\n"
        hallucination_text += f"- 阈值: 0.80\n\n"

        entities = hallucination.get("hallucinated_entities", [])
        if entities:
            hallucination_text += "### 疑似幻觉实体\n"
            for e in entities[:5]:
                hallucination_text += f"- {e}\n"

        citation_text = f"## 引用准确率\n"
        citation_text += f"- 准确率: **{citation_accuracy:.2%}**\n"
        citation_text += f"- 总引用数: {citations.get('total', 0)}\n"
        citation_text += f"- 有效引用数: {citations.get('valid_count', 0)}\n"

        return score_text, hallucination_text, citation_text

    def refresh_metrics(self) -> tuple:
        """刷新质量指标"""
        return self.get_quality_metrics()


def create_interface():
    """创建Gradio界面"""
    dashboard = WebUIDashboard()

    with gr.Blocks(title="论文知识库 Dashboard", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 论文知识库 RAG 系统 Dashboard")
        gr.Markdown("四角色专用Agent协作系统")

        # ==================== Tab 1: 论文查询 ====================
        with gr.Tab("论文查询"):
            gr.Markdown("## 论文检索与分析")

            with gr.Row():
                with gr.Column(scale=2):
                    query_input = gr.Textbox(
                        label="查询内容",
                        placeholder="输入论文相关问题...",
                        lines=3
                    )

                    with gr.Row():
                        top_k_input = gr.Slider(
                            minimum=1,
                            maximum=20,
                            value=10,
                            step=1,
                            label="检索数量 (top_k)"
                        )
                        need_code_checkbox = gr.Checkbox(
                            label="生成代码复现",
                            value=False
                        )

                    submit_btn = gr.Button("开始查询", variant="primary")

                with gr.Column(scale=3):
                    retrieval_output = gr.Textbox(
                        label="检索结果",
                        lines=10,
                        max_lines=20
                    )

            with gr.Row():
                analysis_output = gr.Textbox(
                    label="分析摘要",
                    lines=8
                )
                code_output = gr.Textbox(
                    label="代码模块",
                    lines=8
                )

            with gr.Row():
                status_output = gr.Textbox(
                    label="状态信息",
                    lines=5
                )

            submit_btn.click(
                fn=dashboard.query_papers,
                inputs=[query_input, top_k_input, need_code_checkbox],
                outputs=[retrieval_output, analysis_output, code_output, status_output]
            )

        # ==================== Tab 2: Pipeline监控 ====================
        with gr.Tab("Pipeline监控"):
            gr.Markdown("## 四阶段流程可视化")

            pipeline_status = gr.Textbox(
                label="Pipeline状态",
                value=dashboard.get_pipeline_status(),
                lines=12,
                interactive=False
            )

            refresh_pipeline_btn = gr.Button("刷新状态", variant="secondary")
            refresh_pipeline_btn.click(
                fn=dashboard.refresh_pipeline,
                outputs=pipeline_status
            )

            gr.Markdown("""
            ### 流程说明
            1. **检索阶段**: 向量检索 + BM25 + RRF融合
            2. **分析阶段**: 公式提取 + 概念抽取 + 餐巾纸摘要
            3. **质量阶段**: 幻觉检测 + 引用验证 + 支撑度评估
            4. **代码阶段**: 模块生成 + 测试验证 + 运行检查
            """)

        # ==================== Tab 3: Agent状态 ====================
        with gr.Tab("Agent状态"):
            gr.Markdown("## Agent系统状态")

            with gr.Row():
                agent_status = gr.Textbox(
                    label="协调器状态",
                    value=dashboard.get_agent_status(),
                    lines=15,
                    interactive=False
                )

                tools_list = gr.Textbox(
                    label="工具注册详情",
                    value=dashboard.get_tools_list(),
                    lines=15,
                    interactive=False
                )

            refresh_agent_btn = gr.Button("刷新状态", variant="secondary")
            refresh_agent_btn.click(
                fn=dashboard.get_agent_status,
                outputs=agent_status
            )

            refresh_tools_btn = gr.Button("刷新工具列表", variant="secondary")
            refresh_tools_btn.click(
                fn=dashboard.get_tools_list,
                outputs=tools_list
            )

            gr.Markdown("""
            ### Agent角色分工
            | Agent | 功能 | 工具 |
            |-------|------|------|
            | PaperRetrievalAgent | 论文检索 | hybrid_search, vector_search, bm25_search |
            | PaperAnalysisAgent | 内容分析 | 公式提取, 概念抽取 |
            | QualityAssuranceAgent | 质量验证 | hallucination_detect, citation_check |
            | CodeReproductionAgent | 代码复现 | python_exec |
            """)

        # ==================== Tab 4: 质量指标 ====================
        with gr.Tab("质量指标"):
            gr.Markdown("## 质量评估指标")

            with gr.Row():
                quality_score_output = gr.Textbox(
                    label="质量评分趋势",
                    value="无数据",
                    lines=10,
                    interactive=False
                )

                hallucination_output = gr.Textbox(
                    label="幻觉风险分布",
                    value="无数据",
                    lines=10,
                    interactive=False
                )

                citation_output = gr.Textbox(
                    label="引用准确率",
                    value="无数据",
                    lines=10,
                    interactive=False
                )

            refresh_metrics_btn = gr.Button("刷新指标", variant="secondary")
            refresh_metrics_btn.click(
                fn=dashboard.refresh_metrics,
                outputs=[quality_score_output, hallucination_output, citation_output]
            )

            gr.Markdown("""
            ### 质量指标说明
            - **质量评分**: 综合幻觉率和引用准确率加权计算
            - **幻觉风险**: 基于实体支撑度检测
            - **引用准确率**: 验证 [1], [2] 等引用标记有效性
            """)

        # 页脚
        gr.Markdown("---")
        gr.Markdown("""
        **论文知识库RAG系统**
        - 基于四角色专用Agent架构
        - 支持混合检索 (Vector + BM25 + RRF)
        - 集成质量验证和代码复现
        """)

    return demo


def launch():
    """启动WebUI"""
    print("=" * 60)
    print("论文知识库 WebUI Dashboard")
    print("=" * 60)
    print("启动地址: http://0.0.0.0:7860")
    print("=" * 60)

    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    launch()