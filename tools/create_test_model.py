#!/usr/bin/env python3
"""
创建测试模型文件
生成一个简单的测试模型文件，避免网络依赖
"""
import os
import struct
from pathlib import Path

def create_dummy_model(model_name):
    """创建虚拟模型文件"""
    models_dir = Path("resources/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = models_dir / f"{model_name}.pt"
    
    # 如果模型已存在，直接返回
    if model_path.exists():
        return str(model_path)
    
    print(f"🛠️  创建测试模型: {model_name}")
    
    # 创建一个简单的模型文件头信息
    try:
        with open(model_path, 'wb') as f:
            # 写入模型标识
            f.write(b"YOLO_TEST_MODEL_V1.0")
            # 写入模型名称
            f.write(model_name.encode('utf-8'))
            # 写入一些测试数据
            for i in range(100):
                f.write(struct.pack('f', i * 0.1))
        
        print(f"✅ 测试模型创建成功: {model_path}")
        return str(model_path)
        
    except Exception as e:
        print(f"❌ 创建测试模型失败: {e}")
        return None

def create_yolov5s_test():
    """创建YOLOv5s测试模型"""
    return create_dummy_model("yolov5s")

def create_yolov5m_test():
    """创建YOLOv5m测试模型"""
    return create_dummy_model("yolov5m")

def create_yolov5l_test():
    """创建YOLOv5l测试模型"""
    return create_dummy_model("yolov5l")

if __name__ == "__main__":
    # 创建测试模型
    model_path = create_yolov5s_test()
    if model_path:
        print(f"测试模型路径: {model_path}")
    else:
        print("测试模型创建失败")