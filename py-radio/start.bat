@echo off
echo ============================================
echo B站音频播放器 - 启动脚本
echo ============================================
echo.

echo [1/2] 检查Python依赖...
pip show Flask-SocketIO >nul 2>&1
if errorlevel 1 (
    echo 正在安装Python依赖...
    pip install Flask Flask-CORS Flask-SocketIO python-socketio python-engineio requests Werkzeug -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo [2/2] 启动后端服务...
echo 后端服务地址: http://localhost:5000
echo.

cd /d "%~dp0"
python app.py

pause
