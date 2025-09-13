@echo off
chcp 65001 >nul
echo ========================================
echo    VisionDeploy Studio 启动器
echo ========================================
echo.

echo [1/3] 检测Python环境...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ 检测到系统Python环境
    goto :start_app
)

echo ⚠ 未检测到Python环境
echo.
echo [2/3] 准备下载Python...
echo 正在检查网络环境...

REM 检测网络环境（国内/国外）
python -c "import requests; print('cn' if requests.get('http://www.python.org', timeout=5).elapsed.total_seconds() > 1 else 'global')" 2>nul
if %errorlevel% neq 0 (
    set NETWORK=cn
) else (
    set NETWORK=global
)

echo 网络环境: %NETWORK%
echo.
echo 请手动安装Python 3.8+ 后重新运行
echo 下载地址: 
if "%NETWORK%"=="cn" (
    echo https://mirrors.aliyun.com/python/
) else (
    echo https://www.python.org/downloads/
)
pause
exit /b 1

:start_app
echo.
echo [3/3] 启动VisionDeploy Studio...
python launch_studio.py

if %errorlevel% neq 0 (
    echo.
    echo ✗ 启动失败，请检查错误信息
    echo 错误代码: %errorlevel%
    pause
) else (
    echo.
    echo ✓ 程序已正常退出
)
:start_app
echo.
echo [3/3] 启动VisionDeploy Studio...
rem Delegate to launch_studio.py which prefers CTk frontend when available
python launch_studio.py

if %errorlevel% neq 0 (
    echo.
    echo ✗ 启动失败，请检查错误信息
    echo 错误代码: %errorlevel%
    pause
) else (
    echo.
    echo ✓ 程序已正常退出
)