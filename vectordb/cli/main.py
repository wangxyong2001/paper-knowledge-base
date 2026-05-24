"""
CLI交互界面 - 论文知识库系统

支持命令:
    python -m vectordb.cli query "Transformer的核心创新"
    python -m vectordb.cli query "BERT模型结构" --top-k 5 --code
    python -m vectordb.cli status
    python -m vectordb.cli memory

Pipeline状态显示:
    检索 -> 分析 -> 质量 -> 代码 四阶段进度

输出格式:
    JSON, Markdown, Plain text
"""

import argparse
import sys
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb')
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb/scripts')
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb/core')
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb/agents')

from specialized_agents import SpecializedAgentOrchestrator, create_orchestrator
from memory_manager import PaperMemoryManager
from output_formatter import OutputFormatter


class PipelineStage:
    """Pipeline阶段定义"""
    RETRIEVAL = "retrieval"
    ANALYSIS = "analysis"
    QUALITY = "quality"
    CODE = "code"


class CLIInterface:
    """CLI交互界面"""

    # 阶段图标和颜色映射
    STAGE_ICONS = {
        PipelineStage.RETRIEVAL: "[检索]",
        PipelineStage.ANALYSIS: "[分析]",
        PipelineStage.QUALITY: "[质量]",
        PipelineStage.CODE: "[代码]"
    }

    STAGE_COLORS = {
        PipelineStage.RETRIEVAL: "\033[94m",      # 蓝色
        PipelineStage.ANALYSIS: "\033[92m",       # 绿色
        PipelineStage.QUALITY: "\033[93m",        # 黄色
        PipelineStage.CODE: "\033[95m",           # 紫色
        "success": "\033[92m",                    # 绿色（成功）
        "warning": "\033[93m",                    # 黄色（警告）
        "error": "\033[91m",                      # 红色（错误）
        "reset": "\033[0m",                       # 重置颜色
        "bold": "\033[1m",                        # 加粗
    }

    def __init__(self, session_id: str = "cli-session"):
        """
        初始化CLI界面

        Args:
            session_id: 会话ID
        """
        self.session_id = session_id
        self.orchestrator = None
        self.formatter = OutputFormatter()
        self.current_stage = None
        self.pipeline_state = {}

    def _get_orchestrator(self) -> SpecializedAgentOrchestrator:
        """获取协调器（延迟加载）"""
        if self.orchestrator is None:
            self.orchestrator = create_orchestrator(self.session_id)
        return self.orchestrator

    def run_query(self, query: str, top_k: int = 10, need_code: bool = False,
                  output_format: str = "text") -> Dict:
        """
        运行查询

        Args:
            query: 查询文本
            top_k: 检索数量
            need_code: 是否需要生成代码
            output_format: 输出格式 (json/markdown/text)

        Returns:
            查询结果字典
        """
        print(self._colorize("bold", f"\n{'='*60}"))
        print(self._colorize("bold", f"查询: {query}"))
        print(self._colorize("bold", f"{'='*60}\n"))

        # 获取协调器
        orchestrator = self._get_orchestrator()

        # 显示Pipeline启动
        self._display_pipeline_header()

        try:
            # 阶段1: 检索
            self._display_stage(PipelineStage.RETRIEVAL, "running", "正在检索论文...")
            retrieval_result = orchestrator.retrieval_agent.retrieve(query, top_k=top_k)
            self.pipeline_state["retrieval"] = retrieval_result
            self._display_stage(PipelineStage.RETRIEVAL, "success",
                               f"检索完成: {len(retrieval_result['results'])} 篇论文")

            # 阶段2: 分析
            self._display_stage(PipelineStage.ANALYSIS, "running", "正在分析内容...")
            analysis_result = orchestrator.analysis_agent.analyze(
                query, retrieval_result["results"]
            )
            self.pipeline_state["analysis"] = analysis_result
            self._display_stage(PipelineStage.ANALYSIS, "success",
                               f"分析完成: {len(analysis_result['concepts'])} 个概念, "
                               f"{len(analysis_result['formulas'])} 个公式")

            # 生成输出用于质量验证
            generated_output = orchestrator._generate_output(query, analysis_result)

            # 阶段3: 质量验证
            self._display_stage(PipelineStage.QUALITY, "running", "正在验证质量...")
            qa_result = orchestrator.qa_agent.validate(
                generated_output, retrieval_result["results"]
            )
            self.pipeline_state["qa"] = qa_result
            status = "success" if qa_result["is_passed"] else "warning"
            self._display_stage(PipelineStage.QUALITY, status,
                               f"质量评分: {qa_result['quality_score']:.2f}")

            # 阶段4: 代码复现（如需要）
            code_result = None
            if need_code:
                self._display_stage(PipelineStage.CODE, "running", "正在生成代码...")
                code_result = orchestrator.code_agent.reproduce(query, analysis_result)
                self.pipeline_state["code"] = code_result
                status = "success" if code_result["is_runnable"] else "warning"
                self._display_stage(PipelineStage.CODE, status,
                                   f"生成 {len(code_result['code_modules'])} 个模块")

            # 显示风险告警
            if qa_result["risks"]:
                print(self._colorize("warning", "\n风险告警:"))
                for risk in qa_result["risks"]:
                    print(self._colorize("warning", f"  - {risk}"))

            # 显示修正建议
            if qa_result["suggestions"]:
                print(self._colorize("success", "\n修正建议:"))
                for suggestion in qa_result["suggestions"]:
                    print(self._colorize("success", f"  - {suggestion}"))

            # 组装完整结果
            result = {
                "query": query,
                "pipeline_status": "completed",
                "retrieval": retrieval_result,
                "analysis": analysis_result,
                "quality_assurance": qa_result,
                "code_reproduction": code_result,
                "final_output": generated_output if qa_result["is_passed"] else None
            }

            # 格式化输出
            formatted_output = self.format_output(result, output_format)
            print(formatted_output)

            return result

        except Exception as e:
            self._display_stage(self.current_stage or PipelineStage.RETRIEVAL,
                               "error", f"错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def _display_pipeline_header(self):
        """显示Pipeline启动头"""
        stages = [PipelineStage.RETRIEVAL, PipelineStage.ANALYSIS,
                  PipelineStage.QUALITY, PipelineStage.CODE]
        stage_names = [self.STAGE_ICONS[s] for s in stages]
        print(self._colorize("bold", "Pipeline: ") +
              " -> ".join(stage_names))
        print()

    def _display_stage(self, stage: str, status: str, message: str):
        """
        显示阶段状态

        Args:
            stage: 阶段名称
            status: 状态 (running/success/warning/error)
            message: 状态消息
        """
        self.current_stage = stage
        icon = self.STAGE_ICONS.get(stage, "")

        # 状态图标
        status_icons = {
            "running": "[...]",
            "success": "[OK]",
            "warning": "[!!]",
            "error": "[X]"
        }
        status_icon = status_icons.get(status, "")

        # 组合颜色
        color_key = status if status in self.STAGE_COLORS else "reset"
        print(self._colorize(color_key, f"  {icon} {status_icon} {message}"))

    def _colorize(self, color_key: str, text: str) -> str:
        """
        添加颜色

        Args:
            color_key: 颜色键
            text: 待着色文本

        Returns:
            着色后的文本
        """
        color = self.STAGE_COLORS.get(color_key, self.STAGE_COLORS["reset"])
        reset = self.STAGE_COLORS["reset"]
        return f"{color}{text}{reset}"

    def format_output(self, result: Dict, format_type: str = "text") -> str:
        """
        格式化输出

        Args:
            result: 查询结果
            format_type: 格式类型 (json/markdown/text)

        Returns:
            格式化后的字符串
        """
        if format_type == "json":
            return self._format_json(result)
        elif format_type == "markdown":
            return self._format_markdown(result)
        else:
            return self._format_text(result)

    def _format_json(self, result: Dict) -> str:
        """JSON格式输出"""
        # 简化输出，只保留关键信息
        simplified = {
            "query": result.get("query", ""),
            "pipeline_status": result.get("pipeline_status", ""),
            "retrieval": {
                "total": result.get("retrieval", {}).get("metrics", {}).get("total", 0),
                "avg_score": result.get("retrieval", {}).get("metrics", {}).get("avg_score", 0)
            },
            "analysis": {
                "summary": result.get("analysis", {}).get("summary", ""),
                "concepts": result.get("analysis", {}).get("concepts", []),
                "formulas": result.get("analysis", {}).get("formulas", [])
            },
            "quality": {
                "score": result.get("quality_assurance", {}).get("quality_score", 0),
                "passed": result.get("quality_assurance", {}).get("is_passed", False),
                "risks": result.get("quality_assurance", {}).get("risks", [])
            }
        }

        # 添加代码信息
        if result.get("code_reproduction"):
            simplified["code"] = {
                "modules": [
                    {"name": m["name"], "type": m["type"]}
                    for m in result["code_reproduction"].get("code_modules", [])
                ],
                "runnable": result["code_reproduction"].get("is_runnable", False)
            }

        return "\n" + self._colorize("bold", "JSON输出:") + "\n" + \
               json.dumps(simplified, ensure_ascii=False, indent=2)

    def _format_markdown(self, result: Dict) -> str:
        """Markdown格式输出"""
        md = f"""
## 查询结果

**查询**: {result.get('query', '')}

### 检索结果
- 召回数量: {result.get('retrieval', {}).get('metrics', {}).get('total', 0)}
- 平均评分: {result.get('retrieval', {}).get('metrics', {}).get('avg_score', 0):.2f}

### 分析结果

#### 餐巾纸摘要
{result.get('analysis', {}).get('summary', '无摘要')}

#### 核心概念
"""
        for concept in result.get('analysis', {}).get('concepts', [])[:10]:
            md += f"- {concept}\n"

        # 公式
        formulas = result.get('analysis', {}).get('formulas', [])
        if formulas:
            md += "\n#### 公式\n"
            for formula in formulas[:5]:
                if formula.get('latex'):
                    md += f"- `{formula['latex']}`\n"
                elif formula.get('content'):
                    md += f"- {formula['content']}\n"

        # 质量
        qa = result.get('quality_assurance', {})
        md += f"""
### 质量评估
- 评分: {qa.get('quality_score', 0):.2f}
- 通过: {'是' if qa.get('is_passed', False) else '否'}
"""
        if qa.get('risks'):
            md += "- 风险: " + ", ".join(qa['risks']) + "\n"

        # 代码
        code = result.get('code_reproduction')
        if code:
            md += f"""
### 代码复现
- 模块数量: {len(code.get('code_modules', []))}
- 可运行: {'是' if code.get('is_runnable', False) else '否'}
"""

            for module in code.get('code_modules', []):
                md += f"\n#### {module['name']}\n"
                md += f"```python\n{module['code'][:500]}...\n```\n"

        return "\n" + self._colorize("bold", "Markdown输出:") + "\n" + md

    def _format_text(self, result: Dict) -> str:
        """纯文本格式输出"""
        output = []
        output.append(self._colorize("bold", "\n结果摘要:"))
        output.append("-" * 40)

        # 检索信息
        retrieval = result.get('retrieval', {})
        metrics = retrieval.get('metrics', {})
        output.append(f"检索: {metrics.get('total', 0)} 论文, "
                     f"平均评分 {metrics.get('avg_score', 0):.2f}")

        # 分析信息
        analysis = result.get('analysis', {})
        output.append(f"分析: {len(analysis.get('concepts', []))} 概念, "
                     f"{len(analysis.get('formulas', []))} 公式")

        # 摘要
        if analysis.get('summary'):
            output.append(f"\n摘要: {analysis['summary'][:200]}...")

        # 概念
        concepts = analysis.get('concepts', [])
        if concepts:
            output.append(f"\n核心概念: {', '.join(concepts[:5])}")

        # 公式
        formulas = analysis.get('formulas', [])
        if formulas:
            output.append("\n关键公式:")
            for f in formulas[:3]:
                content = f.get('latex') or f.get('content') or f.get('raw', '')
                output.append(f"  - {content[:80]}")

        # 质量
        qa = result.get('quality_assurance', {})
        output.append(f"\n质量评分: {qa.get('quality_score', 0):.2f}")
        output.append(f"验证通过: {'是' if qa.get('is_passed', False) else '否'}")

        # 代码
        code = result.get('code_reproduction')
        if code and code.get('code_modules'):
            output.append(f"\n代码模块: {len(code['code_modules'])} 个")
            for module in code['code_modules'][:2]:
                output.append(f"  - {module['name']} ({module['type']})")

        return "\n".join(output)

    def display_status(self) -> Dict:
        """
        显示系统状态

        Returns:
            状态信息字典
        """
        print(self._colorize("bold", "\n系统状态"))
        print("=" * 40)

        orchestrator = self._get_orchestrator()
        status = orchestrator.get_status()

        # 显示工作流状态
        print(self._colorize("bold", "\nPipeline状态:"))
        for stage, state in status["workflow_state"].items():
            color = "success" if state == "completed" else "warning"
            icon = self.STAGE_ICONS.get(stage, "")
            print(self._colorize(color, f"  {icon} {state}"))

        # 显示工具列表
        print(self._colorize("bold", "\n已注册工具:"))
        tools = status["registered_tools"]
        for i, tool in enumerate(tools[:10], 1):
            print(f"  {i}. {tool}")

        # 显示会话信息
        print(self._colorize("bold", "\n会话信息:"))
        print(f"  Session ID: {status['memory_session']}")

        return status

    def display_memory(self) -> Dict:
        """
        显示记忆内容

        Returns:
            记忆信息字典
        """
        print(self._colorize("bold", "\n记忆系统"))
        print("=" * 40)

        orchestrator = self._get_orchestrator()
        memory = orchestrator.memory

        # 工作记忆
        working = memory.get_working_memory()
        print(self._colorize("bold", "\n工作记忆 (最近对话):"))
        for i, item in enumerate(working[-5:], 1):
            role = item.get('role', 'unknown')
            content = item.get('content', '')[:50]
            timestamp = item.get('timestamp', '')
            print(f"  [{i}] {role}: {content}... ({timestamp})")

        # 情景记忆
        episodic = memory.get_episodic_by_session(self.session_id)
        print(self._colorize("bold", "\n情景记忆 (分析历史):"))
        if episodic:
            for i, item in enumerate(episodic[:5], 1):
                paper_id = item.get('paper_id', '')
                summary = item.get('summary', '')[:30]
                print(f"  [{i}] {paper_id}: {summary}...")
        else:
            print("  (无历史记录)")

        return {
            "working_memory": working,
            "episodic_memory": episodic
        }

    def display_agent_status(self) -> Dict:
        """
        显示Agent状态

        Returns:
            Agent状态字典
        """
        print(self._colorize("bold", "\nAgent状态"))
        print("=" * 40)

        orchestrator = self._get_orchestrator()

        agents = [
            ("检索Agent", orchestrator.retrieval_agent),
            ("分析Agent", orchestrator.analysis_agent),
            ("质量Agent", orchestrator.qa_agent),
            ("代码Agent", orchestrator.code_agent)
        ]

        agent_status = {}
        for name, agent in agents:
            has_memory = agent.memory is not None
            status = "ready" if has_memory else "limited"
            color = "success" if has_memory else "warning"
            print(self._colorize(color, f"  {name}: {status}"))
            agent_status[name] = {
                "has_memory": has_memory,
                "status": status
            }

        return agent_status


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="vectordb.cli",
        description="论文知识库CLI交互界面",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m vectordb.cli query "Transformer的核心创新"
    python -m vectordb.cli query "BERT模型" --top-k 5 --code
    python -m vectordb.cli status
    python -m vectordb.cli memory
    python -m vectordb.cli agents
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # query 子命令
    query_parser = subparsers.add_parser(
        "query", help="执行查询"
    )
    query_parser.add_argument(
        "query_text", help="查询文本"
    )
    query_parser.add_argument(
        "--top-k", "-k", type=int, default=10,
        help="检索数量 (默认: 10)"
    )
    query_parser.add_argument(
        "--code", "-c", action="store_true",
        help="是否生成代码"
    )
    query_parser.add_argument(
        "--format", "-f", choices=["json", "markdown", "text"],
        default="text", help="输出格式 (默认: text)"
    )
    query_parser.add_argument(
        "--session", "-s", default="cli-session",
        help="会话ID (默认: cli-session)"
    )

    # status 子命令
    status_parser = subparsers.add_parser(
        "status", help="显示系统状态"
    )
    status_parser.add_argument(
        "--session", "-s", default="cli-session",
        help="会话ID"
    )

    # memory 子命令
    memory_parser = subparsers.add_parser(
        "memory", help="显示记忆内容"
    )
    memory_parser.add_argument(
        "--session", "-s", default="cli-session",
        help="会话ID"
    )

    # agents 子命令
    agents_parser = subparsers.add_parser(
        "agents", help="显示Agent状态"
    )
    agents_parser.add_argument(
        "--session", "-s", default="cli-session",
        help="会话ID"
    )

    return parser


def main():
    """CLI主入口"""
    parser = create_parser()
    args = parser.parse_args()

    # 如果没有指定命令，显示帮助
    if not args.command:
        parser.print_help()
        return

    # 创建CLI界面
    cli = CLIInterface(session_id=args.session if hasattr(args, 'session') else "cli-session")

    # 执行命令
    if args.command == "query":
        cli.run_query(
            query=args.query_text,
            top_k=args.top_k,
            need_code=args.code,
            output_format=args.format
        )
    elif args.command == "status":
        cli.display_status()
    elif args.command == "memory":
        cli.display_memory()
    elif args.command == "agents":
        cli.display_agent_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()