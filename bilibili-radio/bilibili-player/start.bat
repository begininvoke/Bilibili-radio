@echo off
echo ============================================
echo B站音频播放器 - 前端启动脚本
echo ============================================
echo.

cd /d "%~dp0"

echo [1/2] 检查Node.js依赖...
if not exist "node_modules" (
    echo 正在安装Node.js依赖...
    npm install
)

echo.
echo [2/2] 启动前端开发服务器...
echo 前端服务地址: http://localhost:3000
echo.

npm run dev

pause
