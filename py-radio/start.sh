#!/bin/bash

echo "========================================"
echo "B站音频播放器启动脚本"
echo "========================================"
echo ""

echo "[1/3] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python，请先安装Python 3.7+"
    exit 1
fi

echo "[2/3] 检查依赖..."
if ! pip3 show flask &> /dev/null; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

echo "[3/3] 启动服务..."
echo ""
echo "正在启动Flask API服务器..."
python3 worker.py &

sleep 2

echo "正在启动播放器GUI..."
python3 player.py &

echo ""
echo "========================================"
echo "启动完成！"
echo "API服务器: http://localhost:5000"
echo "播放器窗口已打开"
echo "========================================"
