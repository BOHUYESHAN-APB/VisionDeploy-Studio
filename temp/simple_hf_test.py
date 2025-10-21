#!/usr/bin/env python3
"""
简单的HF浏览器功能测试
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def simple_callback(message, progress):
    """简单的进度回调函数"""
    if progress >= 0:
        print(f"[{progress:3d}%] {message}")
    else:
        print(f"[ERR] {message}")

def test_hf_functions():
    """测试HF浏览器功能"""
    print("测试HF浏览器功能...")
    
    try:
        from app.hf_browser import search_models, get_model_metadata, list_model_files, get_model_readme
        
        # 测试搜索模型
        print("\n1. 测试搜索模型:")
        results = search_models("yolo", limit=3)
        print(f"找到 {len(results)} 个模型")
        for i, model in enumerate(results, 1):
            model_id = model.get('modelId', 'N/A')
            pipeline_tag = model.get('pipeline_tag', 'N/A')
            print(f"  {i}. {model_id} - {pipeline_tag}")
        
        # 测试获取模型元数据
        print("\n2. 测试获取模型元数据:")
        if results:
            test_model_id = results[0].get('modelId')
            if test_model_id:
                metadata = get_model_metadata(test_model_id)
                print(f"  Model ID: {metadata.get('modelId', 'N/A')}")
                print(f"  Pipeline Tag: {metadata.get('pipeline_tag', 'N/A')}")
        
        # 测试列出模型文件
        print("\n3. 测试列出模型文件:")
        if results:
            test_model_id = results[0].get('modelId')
            if test_model_id:
                files = list_model_files(test_model_id)
                print(f"  找到 {len(files)} 个文件")
                for i, file_info in enumerate(files[:3], 1):
                    name = file_info.get('name', 'N/A')
                    size = file_info.get('size', 'N/A')
                    print(f"    {i}. {name} ({size} bytes)")
        
        # 测试获取模型README
        print("\n4. 测试获取模型README:")
        if results:
            test_model_id = results[0].get('modelId')
            if test_model_id:
                readme = get_model_readme(test_model_id)
                if readme:
                    print(f"  README长度: {len(readme)} 字符")
                else:
                    print("  无法获取README")
        
        print("\n✅ HF浏览器功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hf_functions()
    sys.exit(0 if success else 1)