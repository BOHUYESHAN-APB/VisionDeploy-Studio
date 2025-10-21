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
echo 未检测到系统 Python 环境。您可以选择：
echo  1) 自动下载安装并配置嵌入式 Python（运行 setup.py，需网络连接）
echo  2) 打开官方下载页面手动安装
echo  3) 退出
set /p CHOICE="请输入选项(1/2/3, 默认2): "
if "%CHOICE%"=="1" (
    echo 正在调用 setup.py 以自动设置嵌入式 Python...
    python -V >nul 2>&1
    if %errorlevel% neq 0 (
        rem use system's python to run setup.py; if not present, attempt to run via bundled small bootstrap using powershell
        echo 正在尝试通过 PowerShell 启动 setup.py ...
        powershell -NoProfile -Command "& { Start-Process -FilePath 'python' -ArgumentList 'setup.py' -Wait -NoNewWindow }" 2>nul
        if %errorlevel% neq 0 (
            echo 无法直接运行 python，请手动运行 setup.py 或安装 Python。
            pause
            exit /b 1
        ) else (
            exit /b 0
        )
    ) else (
        python setup.py
        exit /b %errorlevel%
    )
) else if "%CHOICE%"=="2" (
    echo 打开下载页面...
    if "%NETWORK%"=="cn" (
        echo https://mirrors.aliyun.com/python/
    ) else (
        echo https://www.python.org/downloads/
    )
    pause
    exit /b 1
) else (
    echo 退出。
    exit /b 1
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