#!/bin/bash
# CLI功能验证脚本
#
# 使用方法: ./scripts/verify_cli.sh

set -e

cd /home/nvidia/workspace/paper/vectordb

echo "=========================================="
echo "CLI功能验证"
echo "=========================================="

echo ""
echo "1. 测试帮助命令..."
python -m vectordb.cli --help

echo ""
echo "2. 测试status命令..."
python -m vectordb.cli status --session verify-test

echo ""
echo "3. 测试agents命令..."
python -m vectordb.cli agents --session verify-test

echo ""
echo "4. 测试memory命令..."
python -m vectordb.cli memory --session verify-test

echo ""
echo "5. 测试query命令 (文本格式)..."
python -m vectordb.cli query "Transformer的核心创新" --top-k 3 --format text

echo ""
echo "6. 测试query命令 (JSON格式)..."
python -m vectordb.cli query "BERT模型架构" --top-k 2 --format json

echo ""
echo "7. 测试query命令 (带代码生成)..."
python -m vectordb.cli query "自注意力机制" --code --format text

echo ""
echo "=========================================="
echo "验证完成"
echo "=========================================="