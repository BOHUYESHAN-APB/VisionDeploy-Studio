@echo off
chcp 65001 >nul
echo (scripts copy) Launcher helper - original at repository root

REM Invoke root launcher for actual behavior
python ..\launcher.bat
