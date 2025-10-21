#!/usr/bin/env python3
"""
测试改进后的HF浏览器功能
"""

import sys
from pathlib import Path
import tempfile
import shutil

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def progress_callback(message, progress):
    """进度回调函数"""
    if progress >= 0:
        print(f"[{progress:3d}%] {message}")
    else:
        print(f"[ERR] {message}")

def test_model_type_detection():
    """测试模型类型检测功能"""
    print("测试模型类型检测功能...")
    
    from app.hf_browser import _detect_model_type
    
    test_cases = [
        ("model.pt", "pytorch"),
        ("pytorch_model.bin", "pytorch"),
        ("model.safetensors", "safetensors"),
        ("diffusion_pytorch_model.bin", "diffusion_pytorch"),
        ("pytorch_lora_weights.safetensors", "lora"),
        ("model.h5", "tensorflow"),
        ("tf_model.pb", "tensorflow"),
        ("model.tflite", "tflite"),
        ("model.onnx", "onnx"),
        ("flax_model.msgpack", "flax"),
        ("ggml-model.bin", "ggml"),
        ("unknown.txt", "unknown")
    ]
    
    success_count = 0
    for filename, expected_type in test_cases:
        detected_type = _detect_model_type(filename)
        if detected_type == expected_type:
            print(f"  ✓ {filename} -> {detected_type}")
            success_count += 1
        else:
            print(f"  ✗ {filename} -> {detected_type} (期望: {expected_type})")
    
    print(f"模型类型检测测试完成: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)

def test_file_categorization():
    """测试文件分类功能"""
    print("测试文件分类功能...")
    
    from app.hf_browser import _categorize_file
    
    test_cases = [
        ("pytorch_model.bin", "model"),
        ("config.json", "config"),
        ("README.md", "documentation"),
        ("setup.py", "code"),
        ("unknown.bin", "other"),
        ("model.safetensors", "model"),
        ("tokenizer_config.json", "config"),
        ("license", "documentation"),
        ("script.sh", "code")
    ]
    
    success_count = 0
    for filename, expected_category in test_cases:
        category = _categorize_file(filename)
        if category == expected_category:
            print(f"  ✓ {filename} -> {category}")
            success_count += 1
        else:
            print(f"  ✗ {filename} -> {category} (期望: {expected_category})")
    
    print(f"文件分类测试完成: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)

def test_model_file_detection():
    """测试模型文件检测功能"""
    print("测试模型文件检测功能...")
    
    from app.hf_browser import _is_model_file
    
    model_files = [
        "pytorch_model.bin",
        "model.safetensors",
        "tf_model.h5",
        "model.tflite",
        "model.onnx",
        "flax_model.msgpack",
        "ggml-model.bin"
    ]
    
    non_model_files = [
        "README.md",
        "config.json",
        "setup.py",
        "license.txt",
        "unknown.txt"
    ]
    
    success_count = 0
    total_tests = len(model_files) + len(non_model_files)
    
    # 测试模型文件
    for filename in model_files:
        if _is_model_file(filename):
            print(f"  ✓ {filename} 正确识别为模型文件")
            success_count += 1
        else:
            print(f"  ✗ {filename} 未识别为模型文件")
    
    # 测试非模型文件
    for filename in non_model_files:
        if not _is_model_file(filename):
            print(f"  ✓ {filename} 正确识别为非模型文件")
            success_count += 1
        else:
            print(f"  ✗ {filename} 错误识别为模型文件")
    
    print(f"模型文件检测测试完成: {success_count}/{total_tests} 通过")
    return success_count == total_tests

def test_config_file_detection():
    """测试配置文件检测功能"""
    print("测试配置文件检测功能...")
    
    from app.hf_browser import _is_config_file
    
    config_files = [
        "config.json",
        "configuration.json",
        "model_config.json",
        "tokenizer_config.json",
        "adapter_config.json"
    ]
    
    non_config_files = [
        "README.md",
        "pytorch_model.bin",
        "setup.py",
        "license.txt",
        "unknown.txt"
    ]
    
    success_count = 0
    total_tests = len(config_files) + len(non_config_files)
    
    # 测试配置文件
    for filename in config_files:
        if _is_config_file(filename):
            print(f"  ✓ {filename} 正确识别为配置文件")
            success_count += 1
        else:
            print(f"  ✗ {filename} 未识别为配置文件")
    
    # 测试非配置文件
    for filename in non_config_files:
        if not _is_config_file(filename):
            print(f"  ✓ {filename} 正确识别为非配置文件")
            success_count += 1
        else:
            print(f"  ✗ {filename} 错误识别为配置文件")
    
    print(f"配置文件检测测试完成: {success_count}/{total_tests} 通过")
    return success_count == total_tests

def test_documentation_file_detection():
    """测试文档文件检测功能"""
    print("测试文档文件检测功能...")
    
    from app.hf_browser import _is_documentation_file
    
    doc_files = [
        "README.md",
        "readme.txt",
        "LICENSE",
        "changelog.md",
        "contributing.rst"
    ]
    
    non_doc_files = [
        "config.json",
        "pytorch_model.bin",
        "setup.py",
        "unknown.bin",
        "script.sh"
    ]
    
    success_count = 0
    total_tests = len(doc_files) + len(non_doc_files)
    
    # 测试文档文件
    for filename in doc_files:
        if _is_documentation_file(filename):
            print(f"  ✓ {filename} 正确识别为文档文件")
            success_count += 1
        else:
            print(f"  ✗ {filename} 未识别为文档文件")
    
    # 测试非文档文件
    for filename in non_doc_files:
        if not _is_documentation_file(filename):
            print(f"  ✓ {filename} 正确识别为非文档文件")
            success_count += 1
        else:
            print(f"  ✗ {filename} 错误识别为文档文件")
    
    print(f"文档文件检测测试完成: {success_count}/{total_tests} 通过")
    return success_count == total_tests

def test_model_config_generation():
    """测试模型配置生成功能"""
    print("测试模型配置生成功能...")
    
    from app.hf_browser import _generate_model_config
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_model.pt"
        tmp_path.touch()
        
        # 测试YOLO模型
        config = _generate_model_config("ultralytics/yolov8", "yolov8s.pt", tmp_path)
        expected_id = "hf_ultralytics_yolov8_yolov8s"
        if config["id"] == expected_id and config["family"] == "yolo":
            print(f"  ✓ YOLO模型配置生成正确")
            success1 = True
        else:
            print(f"  ✗ YOLO模型配置生成错误: id={config['id']}, family={config['family']}")
            success1 = False
        
        # 测试BERT模型
        config = _generate_model_config("bert-base-uncased", "pytorch_model.bin", tmp_path)
        if config["family"] == "bert" and "nlp" in config["tags"]:
            print(f"  ✓ BERT模型配置生成正确")
            success2 = True
        else:
            print(f"  ✗ BERT模型配置生成错误: family={config['family']}, tags={config['tags']}")
            success2 = False
        
        # 测试通用模型
        config = _generate_model_config("unknown/model", "model.pt", tmp_path)
        if config["family"] == "custom" and config["source"] == "huggingface":
            print(f"  ✓ 通用模型配置生成正确")
            success3 = True
        else:
            print(f"  ✗ 通用模型配置生成错误: family={config['family']}, source={config['source']}")
            success3 = False
    
    print(f"模型配置生成测试完成: {sum([success1, success2, success3])}/3 通过")
    return success1 and success2 and success3

def test_auto_configure_model():
    """测试自动配置模型功能"""
    print("测试自动配置模型功能...")
    
    from app.hf_browser import auto_configure_model
    import tempfile
    import json
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_model.pt"
        tmp_path.touch()
        
        models_db_path = Path(tmpdir) / "models.json"
        
        # 测试模型自动配置
        success = auto_configure_model("test/repo", "test_model.pt", tmp_path, models_db_path)
        
        if success and models_db_path.exists():
            # 验证配置文件内容
            with open(models_db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            
            if len(db.get("models", [])) > 0:
                model = db["models"][0]
                if (model["id"] == "hf_test_repo_test_model" and 
                    model["source"] == "huggingface" and
                    model["source_repo"] == "test/repo"):
                    print(f"  ✓ 模型自动配置成功")
                    return True
                else:
                    print(f"  ✗ 模型配置内容不正确")
                    return False
            else:
                print(f"  ✗ 模型数据库为空")
                return False
        else:
            print(f"  ✗ 模型自动配置失败")
            return False

def test_improved_hf_browser_functionality():
    """测试所有改进后的HF浏览器功能"""
    print("测试改进后的HF浏览器功能...")
    print("=" * 50)
    
    tests = [
        test_model_type_detection,
        test_file_categorization,
        test_model_file_detection,
        test_config_file_detection,
        test_documentation_file_detection,
        test_model_config_generation,
        test_auto_configure_model
    ]
    
    passed_tests = 0
    for test_func in tests:
        try:
            if test_func():
                passed_tests += 1
            print()
        except Exception as e:
            print(f"  测试 {test_func.__name__} 出错: {e}")
            print()
    
    print("=" * 50)
    print(f"总计: {passed_tests}/{len(tests)} 个测试通过")
    
    if passed_tests == len(tests):
        print("✅ 所有改进后的HF浏览器功能测试通过")
        return True
    else:
        print("❌ 部分测试失败")
        return False

if __name__ == "__main__":
    success = test_improved_hf_browser_functionality()
    sys.exit(0 if success else 1)