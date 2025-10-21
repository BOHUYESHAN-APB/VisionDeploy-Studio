#!/usr/bin/env python3
"""
测试改进后的模型管理器功能
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def progress_callback(message, progress):
    """进度回调函数"""
    if progress >= 0:
        print(f"[{progress:3d}%] {message}")
    else:
        print(f"[ERR] {message}")

def test_improved_model_manager():
    """测试改进后的模型管理器功能"""
    print("测试改进后的模型管理器功能...")
    print()
    
    try:
        from app.model_manager import list_models, get_model_entry, find_local_models
        
        # 1. 测试列出模型
        print("1. 测试列出模型:")
        models = list_models()
        print(f"找到 {len(models)} 个模型")
        for i, model in enumerate(models[:3], 1):
            model_id = model.get('id', 'N/A')
            display_name = model.get('display_name', 'N/A')
            family = model.get('family', 'N/A')
            print(f"  {i}. {display_name} ({model_id}) - {family}")
        print()
        
        # 2. 测试获取模型条目
        print("2. 测试获取模型条目:")
        if models:
            test_model_id = models[0].get('id')
            if test_model_id:
                entry = get_model_entry(test_model_id)
                if entry:
                    print(f"  Model ID: {entry.get('id', 'N/A')}")
                    print(f"  Display Name: {entry.get('display_name', 'N/A')}")
                    print(f"  Family: {entry.get('family', 'N/A')}")
                    versions = entry.get('versions', [])
                    print(f"  Versions: {len(versions)}")
                    if versions:
                        version = versions[0]
                        print(f"    First Version: {version.get('version', 'N/A')}")
                        print(f"    Filename: {version.get('filename', 'N/A')}")
                else:
                    print("  无法获取模型条目")
        print()
        
        # 3. 测试查找本地模型
        print("3. 测试查找本地模型:")
        local_models = find_local_models()
        print(f"找到 {len(local_models)} 个本地模型")
        for i, model_path in enumerate(local_models[:3], 1):
            print(f"  {i}. {model_path.name}")
        print()
        
        print("✅ 改进后的模型管理器功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_improved_model_manager()
    sys.exit(0 if success else 1)