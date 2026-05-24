"""
Vectordb 模块入口

支持: python -m vectordb [command]
"""

import sys

if len(sys.argv) > 1 and sys.argv[1] == "cli":
    from cli.main import main
    # 移除 "cli" 参数，让 CLI 的 argparse 正常工作
    sys.argv = sys.argv[1:]
    main()
else:
    print("Usage: python -m vectordb.cli [command]")
    print("Commands: query, status, memory, agents")