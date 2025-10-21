#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VisionDeploy Studio - 最终集成测试脚本
验证所有核心功能是否正常工作
"""

import sys
import os
import time
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 确保当前目录也在路径中
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有模块导入"""
    print("1. 测试模块导入...")
    
    try:
        from app.hf_browser import search_models, get_model_metadata, list_model_files, get_model_readme
        print("  ✅ HF浏览器模块导入成功")
    except Exception as e:
        print(f"  ❌ HF浏览器模块导入失败: {e}")
        return False
    
    try:
        from app.model_manager import list_models, get_model_entry, download_model
        print("  ✅ 模型管理器模块导入成功")
    except Exception as e:
        print(f"  ❌ 模型管理器模块导入失败: {e}")
        return False
    
    try:
        from core.hardware_detector_simple import HardwareDetector
        print("  ✅ 硬件检测器模块导入成功")
    except Exception as e:
        print(f"  ❌ 硬件检测器模块导入失败: {e}")
        return False
    
    try:
        from app.gui_ctk import MainApp
        print("  ✅ GUI模块导入成功")
    except Exception as e:
        print(f"  ❌ GUI模块导入失败: {e}")
        return False
        
    return True

def test_hardware_detection():
    """测试硬件检测功能"""
    print("\n2. 测试硬件检测...")
    
    try:
        from core.hardware_detector_simple import HardwareDetector
        detector = HardwareDetector()
        hardware_info = detector.detect_all_hardware()
        print(f"  ✅ 硬件检测完成")
        print(f"     NVIDIA GPU: {'✅' if hardware_info.get('nvidia_gpu', False) else '❌'}")
        print(f"     AMD GPU: {'✅' if hardware_info.get('amd_gpu', False) else '❌'}")
        print(f"     Intel GPU: {'✅' if hardware_info.get('intel_gpu', False) else '❌'}")
        print(f"     CPU核心数: {hardware_info.get('cpu_cores', '未知')}")
        return True
    except Exception as e:
        print(f"  ❌ 硬件检测失败: {e}")
        return False

def test_hf_browser():
    """测试HF浏览器功能"""
    print("\n3. 测试HF浏览器功能...")
    
    try:
        from app.hf_browser import search_models, get_model_metadata
        
        # 测试搜索模型
        print("  测试搜索模型...")
        models = search_models("yolo", limit=3)
        print(f"  ✅ 搜索完成，找到 {len(models)} 个模型")
        
        if models:
            # 测试获取模型元数据
            print("  测试获取模型元数据...")
            model_id = models[0]['id']
            metadata = get_model_metadata(model_id)
            print(f"  ✅ 获取元数据完成: {metadata.get('id', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"  ❌ HF浏览器功能测试失败: {e}")
        return False

def test_model_manager():
    """测试模型管理器功能"""
    print("\n4. 测试模型管理器功能...")
    
    try:
        from app.model_manager import list_models, get_model_entry
        
        # 测试列出模型
        print("  测试列出内置模型...")
        models = list_models()
        print(f"  ✅ 列出模型完成，找到 {len(models)} 个模型")
        
        if models:
            # 测试获取模型条目
            print("  测试获取模型条目...")
            model_entry = get_model_entry(models[0]['id'])
            if model_entry:
                print(f"  ✅ 获取模型条目完成: {model_entry.get('display_name', 'N/A')}")
            else:
                print("  ⚠️  未找到模型条目")
        
        return True
    except Exception as e:
        print(f"  ❌ 模型管理器功能测试失败: {e}")
        return False

def test_gui_initialization():
    """测试GUI初始化"""
    print("\n5. 测试GUI初始化...")
    
    try:
        from app.gui_ctk import MainApp
        import customtkinter as ctk
        
        # 创建一个简单的GUI窗口测试
        root = ctk.CTk()
        root.title("测试窗口")
        root.geometry("300x200")
        
        label = ctk.CTkLabel(root, text="GUI初始化测试")
        label.pack(pady=20)
        
        # 不实际显示窗口，只是测试创建
        root.destroy()
        print("  ✅ GUI初始化成功")
        return True
    except Exception as e:
        print(f"  ❌ GUI初始化失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("VisionDeploy Studio - 最终集成测试")
    print("=" * 60)
    
    start_time = time.time()
    
    # 运行所有测试
    tests = [
        test_imports,
        test_hardware_detection,
        test_hf_browser,
        test_model_manager,
        test_gui_initialization
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ 测试过程中出现异常: {e}")
            results.append(False)
    
    # 计算测试结果
    passed = sum(results)
    total = len(results)
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"通过测试: {passed}/{total}")
    print(f"测试用时: {elapsed:.2f} 秒")
    
    if passed == total:
        print("🎉 所有测试通过！VisionDeploy Studio 功能正常。")
        return True
    else:
        print("❌ 部分测试失败，请检查上述错误信息。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)