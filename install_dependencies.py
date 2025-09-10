#!/usr/bin/env python3
"""
安装 VisionDeploy Studio 所需的依赖
"""

import subprocess
import sys
import platform
import os
from pathlib import Path

def install_package(package, index_url=None, extra_index_url=None):
    """安装单个包"""
    try:
        cmd = [sys.executable, "-m", "pip", "install", package]
        
        if index_url:
            cmd.extend(["--index-url", index_url])
        
        if extra_index_url:
            cmd.extend(["--extra-index-url", extra_index_url])
        
        subprocess.check_call(cmd)
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package} 安装失败: {e}")
        return False

def detect_china_network():
    """检测是否在中国大陆网络环境"""
    try:
        import urllib.request
        # 尝试访问Google
        urllib.request.urlopen("https://www.google.com", timeout=3)
        return False
    except:
        try:
            # 尝试访问百度
            import urllib.request
            urllib.request.urlopen("https://www.baidu.com", timeout=3)
            return True
        except:
            # 默认使用国际源
            return False

def main():
    """主函数"""
    print("🔍 检查并安装 VisionDeploy Studio 所需依赖...")
    print("=" * 50)
    
    # 检测网络环境
    is_china = detect_china_network()
    print(f"🌐 网络环境: {'中国大陆' if is_china else '国际'}")
    
    # 设置镜像源
    if is_china:
        index_url = "https://mirrors.aliyun.com/pypi/simple/"
        torch_extra_url = "https://download.pytorch.org/whl/cu118"  # 默认CUDA 11.8
    else:
        index_url = "https://pypi.org/simple/"
        torch_extra_url = "https://download.pytorch.org/whl/cu118"
    
    # 基础依赖
    required_packages = [
        "dearpygui",
        "psutil",
        "requests",
        "Pillow",
        "PyYAML",
        "GPUtil",
        "pynvml"
    ]
    
    # 根据硬件推荐安装额外依赖
    print("\n🖥️  检测系统硬件...")
    
    # 检查NVIDIA GPU
    cuda_available = False
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print("✅ 检测到 NVIDIA GPU")
            cuda_available = True
        else:
            print("⚠️  未检测到 NVIDIA GPU")
    except FileNotFoundError:
        print("⚠️  未安装 NVIDIA 驱动")
    
    # 询问用户需要安装的环境
    print("\n🔧 可选的深度学习环境:")
    print("  1. YOLOv5 CUDA环境 (需要NVIDIA GPU)")
    print("  2. YOLOv8 CUDA环境 (需要NVIDIA GPU)")
    print("  3. PP-YOLO XPU环境 (Intel处理器)")
    print("  4. 跳过环境安装 (稍后按需安装)")
    
    selected_envs = []
    while True:
        choice = input("\n请选择要安装的环境 (1-4, 多个选项用逗号分隔, 回车跳过): ").strip()
        if not choice:
            break
            
        try:
            choices = [int(x.strip()) for x in choice.split(",")]
            for c in choices:
                if c in [1, 2, 3, 4]:
                    selected_envs.append(c)
            break
        except ValueError:
            print("❌ 请输入有效的选项 (1-4)")
    
    # 根据选择添加依赖
    torch_installed = False
    for env in selected_envs:
        if env == 1:  # YOLOv5 CUDA
            if cuda_available:
                if not torch_installed:
                    print("正在安装 PyTorch CUDA 版本...")
                    if not install_package("torch", index_url, torch_extra_url):
                        print("⚠️  PyTorch 安装失败，将继续安装其他依赖")
                    torch_installed = True
                if not install_package("torchvision", index_url, torch_extra_url):
                    print("⚠️  TorchVision 安装失败")
                if not install_package("torchaudio", index_url, torch_extra_url):
                    print("⚠️  Torchaudio 安装失败")
                # YOLOv5 requirements
                if not install_package("matplotlib"):
                    print("⚠️  matplotlib 安装失败")
                if not install_package("opencv-python"):
                    print("⚠️  opencv-python 安装失败")
                print("✅ YOLOv5 CUDA 环境依赖添加完成")
            else:
                print("⚠️  检测不到NVIDIA GPU，跳过YOLOv5 CUDA环境安装")
                
        elif env == 2:  # YOLOv8 CUDA
            if cuda_available:
                if not torch_installed:
                    print("正在安装 PyTorch CUDA 版本...")
                    if not install_package("torch", index_url, torch_extra_url):
                        print("⚠️  PyTorch 安装失败，将继续安装其他依赖")
                    torch_installed = True
                if not install_package("torchvision", index_url, torch_extra_url):
                    print("⚠️  TorchVision 安装失败")
                if not install_package("torchaudio", index_url, torch_extra_url):
                    print("⚠️  Torchaudio 安装失败")
                if not install_package("ultralytics"):
                    print("⚠️  ultralytics 安装失败")
                print("✅ YOLOv8 CUDA 环境依赖添加完成")
            else:
                print("⚠️  检测不到NVIDIA GPU，跳过YOLOv8 CUDA环境安装")
                
        elif env == 3:  # PP-YOLO XPU
            if not install_package("paddlepaddle"):
                print("⚠️  PaddlePaddle 安装失败")
            print("✅ PP-YOLO XPU 环境依赖添加完成")
    
    # 安装基础依赖
    print(f"\n📦 安装基础依赖包...")
    print("-" * 30)
    
    failed_packages = []
    for package in required_packages:
        print(f"正在安装 {package}...")
        if not install_package(package, index_url):
            failed_packages.append(package)
    
    # 总结
    print("\n" + "=" * 50)
    if failed_packages:
        print(f"⚠️  以下包安装失败:")
        for package in failed_packages:
            print(f"  - {package}")
        print("\n请手动安装这些包:")
        print("pip install " + " ".join(failed_packages))
    else:
        print("🎉 所有依赖安装完成!")
    
    print("\n💡 提示:")
    print("  - 环境将在首次使用时按需创建")
    print("  - 可以在应用程序中准备不同的模型环境")
    print("  - 如果需要修改环境配置，请编辑 config.yaml 文件")

if __name__ == "__main__":
    main()