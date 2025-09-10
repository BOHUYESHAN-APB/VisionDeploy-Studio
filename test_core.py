#!/usr/bin/env python3
"""
核心功能测试脚本
专注于测试环境管理、硬件检测和模型下载功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.environment_manager_simple import EnvironmentManager
from core.hardware_detector_fixed import HardwareDetector
from tools.create_test_model import create_yolov5s_test

def test_environment():
    """测试环境管理功能"""
    print("🧪 测试环境管理功能...")
    
    env_manager = EnvironmentManager()
    
    # 检查Python环境
    python_versions = env_manager.get_available_python_versions()
    print(f"📋 可用Python版本: {python_versions}")
    
    # 检查当前环境
    current_env = env_manager.get_current_environment()
    print(f"🔧 当前环境: {current_env}")
    
    return True

def test_hardware():
    """测试硬件检测功能"""
    print("\n🧪 测试硬件检测功能...")
    
    detector = HardwareDetector()
    hardware_info = detector.detect_all()
    
    print(f"💻 CPU: {hardware_info['cpu']['name']}")
    print(f"🎮 GPU: {hardware_info['gpu']['name']} ({hardware_info['gpu']['vendor']})")
    print(f"🧠 内存: {hardware_info['memory']['total_gb']} GB")
    
    if hardware_info['gpu']['ai_acceleration']:
        print("✅ 支持AI加速")
    else:
        print("⚠️  不支持AI加速")
    
    return True

def test_model_download():
    """测试模型下载功能"""
    print("\n🧪 测试模型下载功能...")
    
    try:
        model_path = download_yolov5s()
        if model_path and os.path.exists(model_path):
            print(f"✅ YOLOv5s模型下载成功: {model_path}")
            return True
        else:
            print("❌ 模型下载失败")
            return False
    except Exception as e:
        print(f"❌ 模型下载错误: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 YOLO Studio 核心功能测试")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # 运行测试
    if test_environment():
        success_count += 1
    
    if test_hardware():
        success_count += 1
    
    if test_model_download():
        success_count += 1
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("🎉 所有核心功能测试通过！")
        return True
    else:
        print("⚠️  部分功能测试失败，请检查日志")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)