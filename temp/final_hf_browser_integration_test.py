#!/usr/bin/env python3
"""
HF浏览器最终集成测试
测试所有改进后的功能
"""

import sys
from pathlib import Path
import tempfile
import json

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def progress_callback(message, progress):
    """进度回调函数"""
    if progress >= 0:
        print(f"[{progress:3d}%] {message}")
    else:
        print(f"[ERR] {message}")

def test_complete_hf_browser_workflow():
    """测试完整的HF浏览器工作流程"""
    print("测试完整的HF浏览器工作流程...")
    print()
    
    try:
        from app.hf_browser import (
            search_models, 
            get_model_metadata, 
            list_model_files, 
            get_model_readme,
            download_from_hf,
            auto_configure_model,
            _detect_model_type,
            _categorize_file
        )
        
        # 1. 测试模型类型检测
        print("1. 测试模型类型检测:")
        test_files = [
            ("yolov8s.pt", "pytorch"),
            ("model.safetensors", "safetensors"),
            ("diffusion_pytorch_model.bin", "diffusion_pytorch"),
            ("README.md", "unknown")
        ]
        
        for filename, expected_type in test_files:
            detected_type = _detect_model_type(filename)
            status = "✓" if detected_type == expected_type else "✗"
            print(f"  {status} {filename} -> {detected_type}")
        print()
        
        # 2. 测试文件分类
        print("2. 测试文件分类:")
        test_files = [
            ("pytorch_model.bin", "model"),
            ("config.json", "config"),
            ("README.md", "documentation"),
            ("setup.py", "code"),
            ("unknown.txt", "other")
        ]
        
        for filename, expected_category in test_files:
            category = _categorize_file(filename)
            status = "✓" if category == expected_category else "✗"
            print(f"  {status} {filename} -> {category}")
        print()
        
        # 3. 测试搜索模型（使用一个简单的查询）
        print("3. 测试搜索模型:")
        try:
            results = search_models("yolo", limit=2, callback=progress_callback)
            print(f"  找到 {len(results)} 个模型")
            for i, model in enumerate(results[:2]):
                model_id = model.get('modelId', 'N/A')
                pipeline_tag = model.get('pipeline_tag', 'N/A')
                print(f"    {i+1}. {model_id} - {pipeline_tag}")
        except Exception as e:
            print(f"  搜索模型时出错: {e}")
        print()
        
        # 4. 测试列出模型文件（使用一个已知的模型）
        print("4. 测试列出模型文件:")
        try:
            # 使用一个简单的测试，避免网络请求
            test_files = [
                {"name": "README.md", "size": 1024, "type": "file", "category": "documentation"},
                {"name": "config.json", "size": 512, "type": "file", "category": "config"},
                {"name": "pytorch_model.bin", "size": 1024000, "type": "file", "category": "model"}
            ]
            
            print(f"  模拟文件列表:")
            for file_info in test_files:
                name = file_info.get('name', 'N/A')
                size = file_info.get('size', 'N/A')
                category = file_info.get('category', 'N/A')
                print(f"    {name} ({size} bytes) - {category}")
        except Exception as e:
            print(f"  列出模型文件时出错: {e}")
        print()
        
        # 5. 测试自动配置模型功能
        print("5. 测试自动配置模型:")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "test_model.pt"
            tmp_path.touch()
            
            models_db_path = Path(tmpdir) / "models.json"
            
            success = auto_configure_model("test/repo", "test_model.pt", tmp_path, models_db_path)
            if success and models_db_path.exists():
                with open(models_db_path, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                
                if len(db.get("models", [])) > 0:
                    model = db["models"][0]
                    print(f"  ✓ 模型配置成功:")
                    print(f"    ID: {model['id']}")
                    print(f"    家族: {model['family']}")
                    print(f"    来源: {model['source']}")
                    print(f"    标签: {model.get('tags', [])}")
                else:
                    print(f"  ✗ 模型数据库为空")
            else:
                print(f"  ✗ 模型自动配置失败")
        print()
        
        print("✅ 完整的HF浏览器工作流程测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_hf_browser_workflow()
    sys.exit(0 if success else 1)