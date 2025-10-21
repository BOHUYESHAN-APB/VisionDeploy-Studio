#!/usr/bin/env python3
"""
HF浏览器集成测试
测试HF浏览器与模型管理器的集成功能
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

def test_hf_browser_integration():
    """测试HF浏览器与模型管理器的集成"""
    print("测试HF浏览器与模型管理器的集成...")
    print()
    
    try:
        from app.hf_browser import search_models, get_model_metadata, list_model_files, get_model_readme, download_from_hf
        from app.model_manager import list_models, get_model_entry, download_model
        
        # 1. 测试搜索模型
        print("1. 测试搜索模型:")
        results = search_models("yolo", limit=3, callback=progress_callback)
        print(f"搜索结果数量: {len(results)}")
        for i, model in enumerate(results[:2], 1):
            model_id = model.get('modelId', 'N/A')
            pipeline_tag = model.get('pipeline_tag', 'N/A')
            print(f"  {i}. {model_id} - {pipeline_tag}")
        print()
        
        # 2. 测试获取模型元数据
        print("2. 测试获取模型元数据:")
        if results:
            test_model_id = results[0].get('modelId')
            if test_model_id:
                metadata = get_model_metadata(test_model_id, callback=progress_callback)
                print(f"  Model ID: {metadata.get('modelId', 'N/A')}")
                print(f"  Pipeline Tag: {metadata.get('pipeline_tag', 'N/A')}")
                print(f"  Description: {metadata.get('description', 'N/A')[:100]}...")
        print()
        
        # 3. 测试列出模型文件
        print("3. 测试列出模型文件:")
        if results:
            test_model_id = results[0].get('modelId')
            if test_model_id:
                files = list_model_files(test_model_id, callback=progress_callback)
                print(f"  文件数量: {len(files)}")
                for i, file_info in enumerate(files[:3], 1):
                    name = file_info.get('name', 'N/A')
                    size = file_info.get('size', 'N/A')
                    print(f"    {i}. {name} ({size} bytes)")
        print()
        
        # 4. 测试获取模型README
        print("4. 测试获取模型README:")
        if results:
            test_model_id = results[0].get('modelId')
            if test_model_id:
                readme = get_model_readme(test_model_id, callback=progress_callback)
                if readme:
                    print(f"  README长度: {len(readme)} 字符")
                    print(f"  README预览: {readme[:100]}...")
                else:
                    print("  无法获取README")
        print()
        
        # 5. 测试列出内置模型
        print("5. 测试列出内置模型:")
        models = list_models()
        print(f"找到 {len(models)} 个内置模型")
        for i, model in enumerate(models[:2], 1):
            model_id = model.get('id', 'N/A')
            display_name = model.get('display_name', 'N/A')
            family = model.get('family', 'N/A')
            print(f"  {i}. {display_name} ({model_id}) - {family}")
        print()
        
        # 6. 测试获取模型条目
        print("6. 测试获取模型条目:")
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
        
        print("✅ HF浏览器与模型管理器集成测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hf_browser_integration()
    sys.exit(0 if success else 1)