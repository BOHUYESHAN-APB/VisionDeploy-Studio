#!/usr/bin/env python3
"""
YOLO本地部署助手 - 环境设置脚本
用于在没有Python环境的情况下设置基础运行环境
"""

import os
import sys
import subprocess
from pathlib import Path

def download_file(url, destination):
    """下载文件"""
    try:
        import requests
        print(f"正在下载: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"下载完成: {destination}")
        return True
    except Exception as e:
        print(f"下载失败: {e}")
        return False

def setup_basic_environment():
    """设置基础Python环境"""
    print("=" * 60)
    print("YOLO本地部署助手 - 基础环境设置")
    print("=" * 60)
    
    # 创建目录结构
    resources_dir = Path("resources")
    python_dir = resources_dir / "python" / "3.10"
    downloads_dir = resources_dir / "downloads"
    
    python_dir.mkdir(parents=True, exist_ok=True)
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查是否已安装Python
    python_exe = python_dir / "python.exe"
    if python_exe.exists():
        print("✅ 已存在Python环境")
        return True
    
    # 下载嵌入式Python
    python_url = "https://mirrors.aliyun.com/python-release/windows/python-3.10.8-embed-amd64.zip"
    zip_path = downloads_dir / "python-3.10.8-embed-amd64.zip"
    
    if not zip_path.exists():
        print("📥 下载嵌入式Python 3.10.8...")
        if not download_file(python_url, zip_path):
            print("❌ Python下载失败")
            return False
    
    # 解压Python
    print("📦 解压Python...")
    try:
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(python_dir)
        print("✅ Python解压完成")
    except Exception as e:
        print(f"❌ 解压失败: {e}")
        return False
    
    # 安装pip
    print("🔧 安装pip...")
    try:
        # 下载get-pip.py
        get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
        get_pip_path = python_dir / "get-pip.py"
        
        if not get_pip_path.exists():
            if not download_file(get_pip_url, get_pip_path):
                print("❌ get-pip.py下载失败")
                return False
        
        # 运行get-pip.py
        subprocess.run([str(python_exe), str(get_pip_path)], check=True)
        print("✅ pip安装完成")
        
        # 配置python._pth文件以包含Scripts目录
        pth_file = python_dir / "python310._pth"
        if pth_file.exists():
            with open(pth_file, 'a') as f:
                f.write("\nimport site\n")
            print("✅ Python路径配置完成")
        
    except Exception as e:
        print(f"❌ pip安装失败: {e}")
        return False
    
    return True

def install_requirements():
    """安装主应用程序依赖"""
    print("📦 安装应用程序依赖...")
    try:
        python_exe = Path("resources") / "python" / "3.10" / "python.exe"
        if not python_exe.exists():
            print("❌ Python环境未找到")
            return False
        
        # 安装requirements.txt中的依赖
        result = subprocess.run([
            str(python_exe), "-m", "pip", "install", 
            "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 依赖安装完成")
            return True
        else:
            print(f"❌ 依赖安装失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 安装过程出错: {e}")
        return False

def main():
    """主函数"""
    print("YOLO本地部署助手环境设置工具")
    print("此工具将帮助您设置基础运行环境")
    print()
    
    # 设置基础环境
    if not setup_basic_environment():
        print("❌ 环境设置失败")
        input("按回车键退出...")
        return
    
    # 安装依赖
    if not install_requirements():
        print("⚠️  依赖安装失败，部分功能可能受限")
    
    print()
    print("🎉 环境设置完成！")
    print("您现在可以运行: python main.py")
    print("或直接运行: run.bat")
    print()
    input("按回车键退出...")

if __name__ == "__main__":
    main()