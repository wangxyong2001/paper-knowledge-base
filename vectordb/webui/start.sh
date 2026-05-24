#!/bin/bash
# WebUI启动脚本

cd /home/nvidia/workspace/paper/vectordb

# 激活虚拟环境
source .venv/bin/activate

# 检查Gradio是否安装
python -c "import gradio; print(f'Gradio {gradio.__version__} 已安装')" || {
    echo "安装Gradio..."
    pip install gradio>=4.0.0
}

# 启动WebUI
echo "启动 WebUI Dashboard..."
echo "访问地址: http://localhost:7860"
echo ""

python -m webui.app