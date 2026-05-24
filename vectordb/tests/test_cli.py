"""
CLI功能测试脚本

运行: python tests/test_cli.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb')
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb/scripts')
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb/core')
sys.path.insert(0, '/home/nvidia/workspace/paper/vectordb/agents')

def test_cli_import():
    """测试CLI模块导入"""
    print("=" * 60)
    print("测试 1: CLI模块导入")
    print("=" * 60)

    try:
        from vectordb.cli import CLIInterface, main
        print("[OK] CLIInterface 导入成功")
        print("[OK] main 导入成功")
        return True
    except ImportError as e:
        print(f"[FAIL] 导入失败: {e}")
        return False


def test_cli_interface_creation():
    """测试CLIInterface创建"""
    print("\n" + "=" * 60)
    print("测试 2: CLIInterface实例创建")
    print("=" * 60)

    try:
        from vectordb.cli import CLIInterface
        cli = CLIInterface(session_id="test-session-001")
        print("[OK] CLIInterface实例创建成功")
        print(f"     Session ID: {cli.session_id}")
        return True
    except Exception as e:
        print(f"[FAIL] 创建失败: {e}")
        return False


def test_cli_orchestrator():
    """测试Orchestrator集成"""
    print("\n" + "=" * 60)
    print("测试 3: Orchestrator集成")
    print("=" * 60)

    try:
        from vectordb.cli import CLIInterface
        cli = CLIInterface(session_id="test-session-002")
        orchestrator = cli._get_orchestrator()

        print("[OK] Orchestrator获取成功")
        print(f"     已注册工具: {len(orchestrator.registry.list_tools())}")
        print(f"     工具列表: {orchestrator.registry.list_tools()}")
        return True
    except Exception as e:
        print(f"[FAIL] Orchestrator失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_format_output():
    """测试输出格式化"""
    print("\n" + "=" * 60)
    print("测试 4: 输出格式化")
    print("=" * 60)

    try:
        from vectordb.cli import CLIInterface

        cli = CLIInterface(session_id="test-session-003")

        # 测试数据
        test_result = {
            "query": "Transformer自注意力",
            "pipeline_status": "completed",
            "retrieval": {
                "metrics": {"total": 5, "avg_score": 0.85}
            },
            "analysis": {
                "summary": "Transformer使用自注意力机制处理序列数据",
                "concepts": ["Self-Attention", "Multi-Head Attention"],
                "formulas": [{"latex": "Attention(Q,K,V) = softmax(QK^T)V"}]
            },
            "quality_assurance": {
                "quality_score": 0.92,
                "is_passed": True,
                "risks": ["无明显风险"]
            },
            "code_reproduction": None
        }

        # 测试三种格式
        json_output = cli.format_output(test_result, "json")
        print("[OK] JSON格式化成功")

        md_output = cli.format_output(test_result, "markdown")
        print("[OK] Markdown格式化成功")

        text_output = cli.format_output(test_result, "text")
        print("[OK] Text格式化成功")

        # 显示部分输出
        print("\n--- Text格式示例 ---")
        print(text_output[:200])

        return True
    except Exception as e:
        print(f"[FAIL] 格式化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_status_display():
    """测试状态显示"""
    print("\n" + "=" * 60)
    print("测试 5: 状态显示")
    print("=" * 60)

    try:
        from vectordb.cli import CLIInterface

        cli = CLIInterface(session_id="test-session-004")
        status = cli.display_status()

        print("[OK] 状态显示成功")
        return True
    except Exception as e:
        print(f"[FAIL] 状态显示失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_agent_status():
    """测试Agent状态显示"""
    print("\n" + "=" * 60)
    print("测试 6: Agent状态显示")
    print("=" * 60)

    try:
        from vectordb.cli import CLIInterface

        cli = CLIInterface(session_id="test-session-005")
        agent_status = cli.display_agent_status()

        print("[OK] Agent状态显示成功")
        return True
    except Exception as e:
        print(f"[FAIL] Agent状态显示失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_argparse():
    """测试argparse命令解析"""
    print("\n" + "=" * 60)
    print("测试 7: 命令行参数解析")
    print("=" * 60)

    try:
        from vectordb.cli.main import create_parser

        parser = create_parser()

        # 测试query命令解析
        args = parser.parse_args(["query", "Transformer", "--top-k", "5", "--code"])
        print(f"[OK] query命令解析: query='{args.query_text}', top_k={args.top_k}, code={args.code}")

        # 测试status命令解析
        args = parser.parse_args(["status"])
        print(f"[OK] status命令解析: command='{args.command}'")

        # 测试memory命令解析
        args = parser.parse_args(["memory"])
        print(f"[OK] memory命令解析: command='{args.command}'")

        # 测试agents命令解析
        args = parser.parse_args(["agents"])
        print(f"[OK] agents命令解析: command='{args.command}'")

        return True
    except Exception as e:
        print(f"[FAIL] 参数解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("CLI模块测试报告")
    print("=" * 60 + "\n")

    tests = [
        ("CLI导入", test_cli_import),
        ("CLIInterface创建", test_cli_interface_creation),
        ("Orchestrator集成", test_cli_orchestrator),
        ("输出格式化", test_cli_format_output),
        ("状态显示", test_cli_status_display),
        ("Agent状态", test_cli_agent_status),
        ("参数解析", test_argparse),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"[ERROR] 测试异常: {e}")
            results.append((name, False))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\n总计: {passed_count}/{total_count} 测试通过")

    return passed_count == total_count


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)