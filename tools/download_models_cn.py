#!/usr/bin/env python3
"""
国内镜像源模型下载工具
使用国内镜像加速模型下载
"""
import os
import requests
from pathlib import Path

class ChinaModelDownloader:
    def __init__(self):
        self.models_dir = Path("resources/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # 国内镜像源配置
        self.mirror_sources = {
            'yolov5s': [
                'https://mirror.sjtu.edu.cn/pytorch/models/yolov5s.pt',
                'https://mirrors.bfsu.edu.cn/pytorch/models/yolov5s.pt',
                'https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.pt'
            ],
            'yolov5m': [
                'https://mirror.sjtu.edu.cn/pytorch/models/yolov5m.pt',
                'https://mirrors.bfsu.edu.cn/pytorch/models/yolov5m.pt',
                'https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5m.pt'
            ],
            'yolov5l': [
                'https://mirror.sjtu.edu.cn/pytorch/models/yolov5l.pt',
                'https://mirrors.bfsu.edu.cn/pytorch/models/yolov5l.pt',
                'https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5l.pt'
            ]
        }
    
    def download_model(self, model_name):
        """下载模型文件"""
        if model_name not in self.mirror_sources:
            print(f"❌ 不支持的模型: {model_name}")
            return None
        
        model_path = self.models_dir / f"{model_name}.pt"
        
        # 如果模型已存在，直接返回路径
        if model_path.exists():
            print(f"✅ 模型已存在: {model_path}")
            return str(model_path)
        
        print(f"⬇️  下载 {model_name}...")
        
        # 尝试所有镜像源
        for i, url in enumerate(self.mirror_sources[model_name]):
            source_name = "官方源" if "github.com" in url else "国内镜像"
            print(f"   来源 [{i+1}/{len(self.mirror_sources[model_name])}]: {source_name}")
            
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                # 下载文件
                with open(model_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"✅ 下载成功: {model_path}")
                return str(model_path)
                
            except requests.exceptions.RequestException as e:
                print(f"   ❌ 下载失败: {e}")
                continue
        
        print(f"❌ 所有镜像源下载失败")
        return None

# 导出函数
def download_yolov5s():
    """下载YOLOv5s模型"""
    downloader = ChinaModelDownloader()
    return downloader.download_model("yolov5s")

def download_yolov5m():
    """下载YOLOv5m模型"""
    downloader = ChinaModelDownloader()
    return downloader.download_model("yolov5m")

def download_yolov5l():
    """下载YOLOv5l模型"""
    downloader = ChinaModelDownloader()
    return downloader.download_model("yolov5l")

if __name__ == "__main__":
    # 测试下载
    downloader = ChinaModelDownloader()
    model_path = downloader.download_model("yolov5s")
    if model_path:
        print(f"测试成功: {model_path}")
    else:
        print("测试失败")