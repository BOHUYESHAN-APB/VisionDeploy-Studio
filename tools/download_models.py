#!/usr/bin/env python3
"""
YOLO模型下载工具
用于下载常用的YOLO模型文件进行测试
"""

import os
import requests
from pathlib import Path

class ModelDownloader:
    def __init__(self):
        self.models_dir = Path("resources/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # 常用YOLO模型下载链接
        self.model_urls = {
            "yolov5s": "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.pt",
            "yolov5m": "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5m.pt", 
            "yolov5l": "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5l.pt",
            "yolov8n": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
            "yolov8s": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt"
        }
        
        # 国内镜像（备用）
        self.mirror_urls = {
            "yolov5s": "https://huggingface.co/ultralytics/yolov5/resolve/main/yolov5s.pt",
            "yolov8n": "https://huggingface.co/ultralytics/yolov8/resolve/main/yolov8n.pt"
        }
    
    def download_model(self, model_name, use_mirror=False):
        """下载指定的YOLO模型"""
        if model_name not in self.model_urls:
            print(f"❌ 不支持的模型: {model_name}")
            print(f"✅ 支持的模型: {list(self.model_urls.keys())}")
            return False
        
        # 选择下载源
        if use_mirror and model_name in self.mirror_urls:
            url = self.mirror_urls[model_name]
        else:
            url = self.model_urls[model_name]
        
        model_path = self.models_dir / f"{model_name}.pt"
        
        if model_path.exists():
            print(f"✅ {model_name} 已存在: {model_path}")
            return True
        
        print(f"⬇️  下载 {model_name}...")
        print(f"   来源: {url}")
        
        try:
            # 下载模型
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 显示下载进度
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"  进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='\r')
            
            print(f"\n✅ {model_name} 下载完成: {model_path}")
            print(f"   大小: {model_path.stat().st_size / (1024*1024):.1f} MB")
            return True
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            # 清理失败的文件
            if model_path.exists():
                model_path.unlink()
            return False
    
    def list_models(self):
        """列出可用的模型"""
        print("📦 可用YOLO模型:")
        for model_name in self.model_urls.keys():
            model_path = self.models_dir / f"{model_name}.pt"
            status = "✅ 已下载" if model_path.exists() else "❌ 未下载"
            print(f"   {model_name}: {status}")
    
    def download_all(self, use_mirror=False):
        """下载所有模型"""
        print("🚀 开始下载所有YOLO模型...")
        success_count = 0
        
        for model_name in self.model_urls.keys():
            if self.download_model(model_name, use_mirror):
                success_count += 1
            print()  # 空行分隔
        
        print(f"📊 下载完成: {success_count}/{len(self.model_urls)} 成功")
        return success_count > 0

def main():
    """主函数"""
    print("=" * 50)
    print("YOLO模型下载工具")
    print("=" * 50)
    
    downloader = ModelDownloader()
    
    # 列出当前模型状态
    downloader.list_models()
    print()
    
    # 询问用户要下载的模型
    print("选择下载选项:")
    print("1. 下载 yolov5s (小型模型，推荐测试)")
    print("2. 下载 yolov8n (最新版本，小型)")
    print("3. 下载所有模型")
    print("4. 列出模型状态")
    print("5. 退出")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    if choice == "1":
        downloader.download_model("yolov5s", use_mirror=True)
    elif choice == "2":
        downloader.download_model("yolov8n", use_mirror=True)
    elif choice == "3":
        downloader.download_all(use_mirror=True)
    elif choice == "4":
        downloader.list_models()
    elif choice == "5":
        print("👋 再见！")
        return
    else:
        print("❌ 无效选项")
    
    input("\n按回车键继续...")

if __name__ == "__main__":
    main()