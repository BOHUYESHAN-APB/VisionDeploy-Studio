#!/usr/bin/env python3
"""
模型下载进度测试
测试模型下载功能的进度显示和错误处理
"""

import sys
from pathlib import Path
import time

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def progress_callback(message, progress):
    """进度回调函数"""
    if progress >= 0:
        print(f"[{progress:3d}%] {message}")
    else:
        print(f"[ERR] {message}")

def test_model_download_with_progress():
    """测试模型下载功能的进度显示和错误处理"""
    print("测试模型下载功能的进度显示和错误处理...")
    print()
    
    try:
        from app.model_manager import list_models, download_model
        from app.hf_browser import download_from_hf
        
        # 1. 测试列出模型
        print("1. 测试列出模型:")
        models = list_models()
        print(f"找到 {len(models)} 个模型")
        for i, model in enumerate(models[:2], 1):
            model_id = model.get('id', 'N/A')
            display_name = model.get('display_name', 'N/A')
            print(f"  {i}. {display_name} ({model_id})")
        print()
        
        # 2. 测试下载内置模型（如果有的话）
        print("2. 测试下载内置模型:")
        if models:
            test_model_id = models[0].get('id')
            if test_model_id:
                print(f"  开始下载模型: {test_model_id}")
                # 使用不同的镜像进行测试
                for mirror in ['auto', 'cn']:
                    print(f"  使用镜像: {mirror}")
                    try:
                        result = download_model(
                            test_model_id, 
                            mirror=mirror, 
                            callback=progress_callback
                        )
                        if result:
                            print(f"  ✅ 下载成功: {result}")
                            break
                        else:
                            print(f"  ❌ 下载失败，尝试下一个镜像")
                    except Exception as e:
                        print(f"  ❌ 下载异常: {e}")
        else:
            print("  没有内置模型可测试")
        print()
        
        # 3. 测试HF模型下载（如果HF浏览器可用）
        print("3. 测试HF模型下载:")
        try:
            from app.hf_browser import search_models
            results = search_models("yolo", limit=1)
            if results:
                test_model_id = results[0].get('modelId')
                if test_model_id:
                    print(f"  找到HF模型: {test_model_id}")
                    # 获取文件列表
                    from app.hf_browser import list_model_files
                    files = list_model_files(test_model_id)
                    if files:
                        # 下载第一个文件
                        filename = files[0].get('name')
                        if filename:
                            print(f"  开始下载文件: {filename}")
                            models_dir = Path('models')
                            models_dir.mkdir(exist_ok=True)
                            result = download_from_hf(
                                test_model_id, 
                                filename, 
                                models_dir,
                                callback=progress_callback
                            )
                            if result:
                                print(f"  ✅ 下载成功: {result}")
                            else:
                                print(f"  ❌ 下载失败")
                        else:
                            print("  无法获取文件名")
                    else:
                        print("  无法获取文件列表")
                else:
                    print("  无法获取模型ID")
            else:
                print("  未找到HF模型")
        except Exception as e:
            print(f"  ❌ HF模型下载测试异常: {e}")
        print()
        
        print("✅ 模型下载进度测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_model_download_with_progress()
    sys.exit(0 if success else 1)