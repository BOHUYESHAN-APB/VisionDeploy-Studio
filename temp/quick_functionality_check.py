#!/usr/bin/env python3
"""
VisionDeploy Studio - 快速功能验证脚本
验证所有核心功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 确保当前目录也在路径中
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_all_components():
    """测试所有核心组件"""
    print("VisionDeploy Studio - 快速功能验证")
    print("=" * 50)
    
    # 1. 测试HF浏览器
    print("1. 测试HF浏览器...")
    try:
        from app.hf_browser import search_models, get_model_metadata
        models = search_models("yolo", limit=2)
        if models:
            print(f"   ✅ HF浏览器正常工作，找到 {len(models)} 个模型")
            metadata = get_model_metadata(models[0]['id'])
            print(f"   ✅ 模型元数据获取成功: {metadata.get('id', 'N/A')}")
        else:
            print("   ⚠️  HF浏览器未返回结果")
    except Exception as e:
        print(f"   ❌ HF浏览器测试失败: {e}")
        return False
    
    # 2. 测试模型管理器
    print("2. 测试模型管理器...")
    try:
        from app.model_manager import list_models, get_model_entry
        models = list_models()
        print(f"   ✅ 模型管理器正常工作，找到 {len(models)} 个内置模型")
        if models:
            entry = get_model_entry(models[0]['id'])
            if entry:
                print(f"   ✅ 模型条目获取成功: {entry.get('display_name', 'N/A')}")
            else:
                print("   ⚠️  未找到模型条目")
    except Exception as e:
        print(f"   ❌ 模型管理器测试失败: {e}")
        return False
    
    # 3. 测试硬件检测器
    print("3. 测试硬件检测器...")
    try:
        from core.hardware_detector_simple import HardwareDetector
        detector = HardwareDetector()
        hardware_info = detector.detect_all_hardware()
        print(f"   ✅ 硬件检测器正常工作")
        print(f"      NVIDIA GPU: {'✅' if hardware_info.get('nvidia_gpu', False) else '❌'}")
        print(f"      AMD GPU: {'✅' if hardware_info.get('amd_gpu', False) else '❌'}")
        print(f"      Intel GPU: {'✅' if hardware_info.get('intel_gpu', False) else '❌'}")
    except Exception as e:
        print(f"   ❌ 硬件检测器测试失败: {e}")
        return False
    
    # 4. 测试GUI组件导入
    print("4. 测试GUI组件导入...")
    try:
        from app.gui_ctk import MainApp
        import customtkinter as ctk
        print("   ✅ GUI组件导入成功")
    except Exception as e:
        print(f"   ❌ GUI组件导入失败: {e}")
        return False
    
    print("\n🎉 所有核心组件测试通过！")
    print("VisionDeploy Studio 功能正常，可以正常启动。")
    return True

if __name__ == "__main__":
    success = test_all_components()
    sys.exit(0 if success else 1)