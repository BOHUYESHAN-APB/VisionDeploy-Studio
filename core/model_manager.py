"""
模型管理模块 - VisionDeploy Studio
用于管理、下载和调用不同的计算机视觉模型
"""

import os
import sys
import json
import yaml
import logging
import shutil
import tempfile
import urllib.request
import zipfile
import hashlib
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ModelManager")

class ModelManager:
    """模型管理类，用于管理、下载和调用不同的计算机视觉模型"""
    
    def __init__(self, base_dir: str = ""):
        """
        初始化模型管理器
        
        Args:
            base_dir: 模型管理器的基础目录，默认为当前工作目录
        """
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.models_dir = os.path.join(self.base_dir, "resources", "models")
        self.config_path = os.path.join(self.base_dir, "config.yaml")
        # 存储已加载的模型实例
        self.loaded_models = {}
        
        # 确保目录存在
        os.makedirs(self.models_dir, exist_ok=True)
        
        # 加载配置
        self.config = self._load_config()
        
        # 检测网络环境
        self.is_china = self._is_in_china()
        logger.info(f"网络环境检测: {'中国大陆' if self.is_china else '国际'}")
        
        # 设置镜像源
        self.model_download_url = self.config['mirrors']['model_china'] if self.is_china else self.config['mirrors']['model_global']
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                    # 如果配置中没有模型镜像，添加默认值
                    if 'mirrors' not in config:
                        config['mirrors'] = {}
                    
                    if 'model_global' not in config['mirrors']:
                        config['mirrors']['model_global'] = 'https://github.com/ultralytics/assets/releases/download/'
                    
                    if 'model_china' not in config['mirrors']:
                        config['mirrors']['model_china'] = 'https://hub.fastgit.xyz/ultralytics/assets/releases/download/'
                    
                    # 如果配置中没有模型定义，添加默认值
                    if 'models' not in config:
                        config['models'] = self._get_default_models()
                        
                        # 保存更新后的配置
                        with open(self.config_path, 'w', encoding='utf-8') as f:
                            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                    
                    return config
            else:
                # 默认配置
                default_config = {
                    'mirrors': {
                        'pip_global': 'https://pypi.org/simple',
                        'pip_china': 'https://mirrors.aliyun.com/pypi/simple/',
                        'python_global': 'https://www.python.org/ftp/python/',
                        'python_china': 'https://registry.npmmirror.com/-/binary/python/',
                        'model_global': 'https://github.com/ultralytics/assets/releases/download/',
                        'model_china': 'https://hub.fastgit.xyz/ultralytics/assets/releases/download/'
                    },
                    'models': self._get_default_models(),
                    'environments': {
                        'yolov5-cuda': {
                            'python_version': '3.8.10',
                            'packages': [
                                'torch==1.10.0+cu113',
                                'torchvision==0.11.1+cu113',
                                'torchaudio==0.10.0+cu113',
                                '-r https://raw.githubusercontent.com/ultralytics/yolov5/master/requirements.txt'
                            ],
                            'extra_index_url': 'https://download.pytorch.org/whl/cu113'
                        }
                    },
                    'network': {
                        'timeout': 30,
                        'retries': 3
                    }
                }
                
                # 保存默认配置
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
                
                return default_config
        except ImportError:
            logger.warning("PyYAML未安装，使用内置默认配置")
            return {
                'mirrors': {
                    'model_global': 'https://github.com/ultralytics/assets/releases/download/',
                    'model_china': 'https://hub.fastgit.xyz/ultralytics/assets/releases/download/'
                },
                'models': self._get_default_models(),
                'network': {
                    'timeout': 30,
                    'retries': 3
                }
            }
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {
                'mirrors': {
                    'model_global': 'https://github.com/ultralytics/assets/releases/download/',
                    'model_china': 'https://hub.fastgit.xyz/ultralytics/assets/releases/download/'
                },
                'models': self._get_default_models(),
                'network': {
                    'timeout': 30,
                    'retries': 3
                }
            }
    
    def _get_default_models(self) -> Dict[str, Any]:
        """获取默认模型配置"""
        return {
            'yolo': {
                'yolov5n': {
                    'type': 'yolov5',
                    'task': 'detect',
                    'url': 'v6.0/yolov5n.pt',
                    'size': 3900000,
                    'description': 'YOLOv5 Nano模型，适用于边缘设备',
                    'environment': 'yolov5-cuda'
                },
                'yolov5s': {
                    'type': 'yolov5',
                    'task': 'detect',
                    'url': 'v6.0/yolov5s.pt',
                    'size': 14100000,
                    'description': 'YOLOv5 Small模型，速度和精度的良好平衡',
                    'environment': 'yolov5-cuda'
                },
                'yolov5m': {
                    'type': 'yolov5',
                    'task': 'detect',
                    'url': 'v6.0/yolov5m.pt',
                    'size': 40900000,
                    'description': 'YOLOv5 Medium模型，中等精度和速度',
                    'environment': 'yolov5-cuda'
                },
                'yolov5l': {
                    'type': 'yolov5',
                    'task': 'detect',
                    'url': 'v6.0/yolov5l.pt',
                    'size': 90900000,
                    'description': 'YOLOv5 Large模型，高精度',
                    'environment': 'yolov5-cuda'
                },
                'yolov5x': {
                    'type': 'yolov5',
                    'task': 'detect',
                    'url': 'v6.0/yolov5x.pt',
                    'size': 168600000,
                    'description': 'YOLOv5 XLarge模型，最高精度',
                    'environment': 'yolov5-cuda'
                },
                'yolov8n': {
                    'type': 'yolov8',
                    'task': 'detect',
                    'url': 'v8.0/yolov8n.pt',
                    'size': 6200000,
                    'description': 'YOLOv8 Nano模型，适用于边缘设备',
                    'environment': 'yolov8-cuda'
                },
                'yolov8s': {
                    'type': 'yolov8',
                    'task': 'detect',
                    'url': 'v8.0/yolov8s.pt',
                    'size': 22600000,
                    'description': 'YOLOv8 Small模型，速度和精度的良好平衡',
                    'environment': 'yolov8-cuda'
                },
                'yolov8m': {
                    'type': 'yolov8',
                    'task': 'detect',
                    'url': 'v8.0/yolov8m.pt',
                    'size': 52200000,
                    'description': 'YOLOv8 Medium模型，中等精度和速度',
                    'environment': 'yolov8-cuda'
                },
                'yolov8l': {
                    'type': 'yolov8',
                    'task': 'detect',
                    'url': 'v8.0/yolov8l.pt',
                    'size': 86700000,
                    'description': 'YOLOv8 Large模型，高精度',
                    'environment': 'yolov8-cuda'
                },
                'yolov8x': {
                    'type': 'yolov8',
                    'task': 'detect',
                    'url': 'v8.0/yolov8x.pt',
                    'size': 136700000,
                    'description': 'YOLOv8 XLarge模型，最高精度',
                    'environment': 'yolov8-cuda'
                },
                'ppyolo-r50vd': {
                    'type': 'ppyolo',
                    'task': 'detect',
                    'url': 'https://paddledet.bj.bcebos.com/models/ppyolo_r50vd_dcn_1x_coco.pdparams',
                    'size': 183300000,
                    'description': 'PP-YOLO模型，基于ResNet50vd骨干网络',
                    'environment': 'ppyolo-xpu'
                }
            },
            'cnn': {
                'resnet50': {
                    'type': 'torchvision',
                    'task': 'classify',
                    'url': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
                    'size': 97800000,
                    'description': 'ResNet-50模型，用于图像分类',
                    'environment': 'yolov8-cuda'
                },
                'mobilenet_v2': {
                    'type': 'torchvision',
                    'task': 'classify',
                    'url': 'https://download.pytorch.org/models/mobilenet_v2-b0353104.pth',
                    'size': 13600000,
                    'description': 'MobileNetV2模型，轻量级图像分类',
                    'environment': 'yolov8-cuda'
                }
            },
            'transformer': {
                'vit_b_16': {
                    'type': 'torchvision',
                    'task': 'classify',
                    'url': 'https://download.pytorch.org/models/vit_b_16-c867db91.pth',
                    'size': 330300000,
                    'description': 'Vision Transformer (ViT-B/16)模型',
                    'environment': 'yolov8-cuda'
                }
            }
        }
    
    def _is_in_china(self) -> bool:
        """检测是否在中国大陆网络环境"""
        try:
            # 尝试访问Google
            urllib.request.urlopen("https://www.google.com", timeout=3)
            return False
        except:
            try:
                # 尝试访问百度
                urllib.request.urlopen("https://www.baidu.com", timeout=3)
                return True
            except:
                # 默认使用国际源
                return False
    
    def _download_file(self, url: str, path: str, expected_size: int = 0) -> None:
        """
        下载文件
        
        Args:
            url: 文件URL
            path: 保存路径
            expected_size: 预期文件大小（字节）
        """
        timeout = self.config['network']['timeout']
        retries = self.config['network']['retries']
        
        for i in range(retries):
            try:
                with urllib.request.urlopen(url, timeout=timeout) as response, open(path, 'wb') as out_file:
                    file_size = int(response.info().get('Content-Length', 0))
                    
                    if expected_size and file_size > 0 and abs(file_size - expected_size) > 1024:
                        logger.warning(f"文件大小不匹配: 预期 {expected_size} 字节，实际 {file_size} 字节")
                    
                    downloaded = 0
                    block_size = 8192
                    
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        
                        downloaded += len(buffer)
                        out_file.write(buffer)
                        
                        if file_size > 0:
                            percent = downloaded * 100 / file_size
                            logger.info(f"下载进度: {percent:.1f}% ({downloaded}/{file_size} 字节)")
                
                # 验证文件大小
                if expected_size:
                    actual_size = os.path.getsize(path)
                    if abs(actual_size - expected_size) > 1024:  # 允许1KB的误差
                        logger.warning(f"下载完成，但文件大小不匹配: 预期 {expected_size} 字节，实际 {actual_size} 字节")
                        if i < retries - 1:
                            logger.info(f"尝试重新下载 ({i+2}/{retries})...")
                            continue
                
                return
            except Exception as e:
                logger.warning(f"下载失败 ({i+1}/{retries}): {e}")
                if i == retries - 1:
                    raise
                time.sleep(2)
    
    def get_model_path(self, model_name: str) -> str:
        """
        获取模型文件路径
        
        Args:
            model_name: 模型名称，格式为"类别/模型名"，如"yolo/yolov5s"
            
        Returns:
            模型文件的路径
        """
        if '/' not in model_name:
            raise ValueError(f"模型名称格式错误: {model_name}，应为'类别/模型名'，如'yolo/yolov5s'")
        
        category, name = model_name.split('/', 1)
        
        if category not in self.config['models']:
            raise ValueError(f"未知的模型类别: {category}")
        
        if name not in self.config['models'][category]:
            raise ValueError(f"未知的模型: {name}")
        
        model_info = self.config['models'][category][name]
        model_type = model_info['type']
        
        # 构建模型文件路径
        model_dir = os.path.join(self.models_dir, category)
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, f"{name}.pt")
        
        # 如果是PaddlePaddle模型，使用.pdparams扩展名
        if model_type == 'ppyolo':
            model_path = os.path.join(model_dir, f"{name}.pdparams")
        
        # 检查模型文件是否存在
        if not os.path.exists(model_path):
            logger.info(f"模型 {model_name} 不存在，尝试下载...")
            self.download_model(model_name)
        
        return model_path
    
    def download_model(self, model_name: str) -> str:
        """
        下载模型文件
        
        Args:
            model_name: 模型名称，格式为"类别/模型名"，如"yolo/yolov5s"
            
        Returns:
            下载后的模型文件路径
        """
        if '/' not in model_name:
            raise ValueError(f"模型名称格式错误: {model_name}，应为'类别/模型名'，如'yolo/yolov5s'")
        
        category, name = model_name.split('/', 1)
        
        if category not in self.config['models']:
            raise ValueError(f"未知的模型类别: {category}")
        
        if name not in self.config['models'][category]:
            raise ValueError(f"未知的模型: {name}")
        
        model_info = self.config['models'][category][name]
        model_url = model_info['url']
        model_size = model_info.get('size', 0)
        model_type = model_info['type']
        
        # 构建模型文件路径
        model_dir = os.path.join(self.models_dir, category)
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, f"{name}.pt")
        
        # 如果是PaddlePaddle模型，使用.pdparams扩展名
        if model_type == 'ppyolo':
            model_path = os.path.join(model_dir, f"{name}.pdparams")
        
        # 如果URL是相对路径，添加基础URL
        if not model_url.startswith('http'):
            model_url = self.model_download_url + model_url
        
        # 下载模型文件
        logger.info(f"下载模型 {model_name} 从 {model_url}")
        self._download_file(model_url, model_path, model_size)
        
        logger.info(f"模型 {model_name} 下载完成: {model_path}")
        return model_path
    
    def list_models(self, category: str = "") -> List[Dict[str, Any]]:
        """
        列出所有可用的模型
        
        Args:
            category: 模型类别，如果为None则列出所有类别的模型
            
        Returns:
            模型列表，每个模型包含名称、类别、类型、任务、描述等信息
        """
        models = []
        
        if category:
            if category not in self.config['models']:
                raise ValueError(f"未知的模型类别: {category}")
            
            categories = [category]
        else:
            categories = list(self.config['models'].keys())
        
        for cat in categories:
            for name, info in self.config['models'][cat].items():
                model_path = os.path.join(self.models_dir, cat, f"{name}.pt")
                
                # 如果是PaddlePaddle模型，使用.pdparams扩展名
                if info['type'] == 'ppyolo':
                    model_path = os.path.join(self.models_dir, cat, f"{name}.pdparams")
                
                # 检查模型文件是否已下载
                is_downloaded = os.path.exists(model_path)
                
                models.append({
                    'name': name,
                    'category': cat,
                    'type': info['type'],
                    'task': info['task'],
                    'description': info.get('description', ''),
                    'environment': info.get('environment', ''),
                    'downloaded': is_downloaded,
                    'size': info.get('size', 0),
                    'path': model_path if is_downloaded else None
                })
        
        return models
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        获取模型详细信息
        
        Args:
            model_name: 模型名称，格式为"类别/模型名"，如"yolo/yolov5s"
            
        Returns:
            模型信息字典
        """
        if '/' not in model_name:
            raise ValueError(f"模型名称格式错误: {model_name}，应为'类别/模型名'，如'yolo/yolov5s'")
        
        category, name = model_name.split('/', 1)
        
        if category not in self.config['models']:
            raise ValueError(f"未知的模型类别: {category}")
        
        if name not in self.config['models'][category]:
            raise ValueError(f"未知的模型: {name}")
        
        model_info = self.config['models'][category][name]
        model_path = os.path.join(self.models_dir, category, f"{name}.pt")
        
        # 如果是PaddlePaddle模型，使用.pdparams扩展名
        if model_info['type'] == 'ppyolo':
            model_path = os.path.join(self.models_dir, category, f"{name}.pdparams")
        
        # 检查模型文件是否已下载
        is_downloaded = os.path.exists(model_path)
        
        info = {
            'name': name,
            'category': category,
            'type': model_info['type'],
            'task': model_info['task'],
            'description': model_info.get('description', ''),
            'environment': model_info.get('environment', ''),
            'downloaded': is_downloaded,
            'size': model_info.get('size', 0),
            'path': model_path if is_downloaded else None,
            'url': model_info['url']
        }
        
        return info
    
    def add_model_config(self, category: str, name: str, model_type: str, task: str, url: str, 
                        size: int = 0, description: str = "", environment: str = "") -> None:
        """
        添加新的模型配置
        
        Args:
            category: 模型类别
            name: 模型名称
            model_type: 模型类型
            task: 模型任务
            url: 模型下载URL
            size: 模型文件大小（字节）
            description: 模型描述
            environment: 模型运行环境
        """
        if category not in self.config['models']:
            self.config['models'][category] = {}
        
        if name in self.config['models'][category]:
            raise ValueError(f"模型已存在: {category}/{name}")
        
        self.config['models'][category][name] = {
            'type': model_type,
            'task': task,
            'url': url,
            'size': size,
            'description': description,
            'environment': environment
        }
        
        # 保存配置
        self._save_config()
        
        logger.info(f"添加模型配置: {category}/{name}")
    
    def update_model_config(self, category: str, name: str, model_type: str = "", task: str = "", 
                           url: str = "", size: int = -1, description: str = "", environment: str = "") -> None:
        """
        更新模型配置
        
        Args:
            category: 模型类别
            name: 模型名称
            model_type: 模型类型
            task: 模型任务
            url: 模型下载URL
            size: 模型文件大小（字节）
            description: 模型描述
            environment: 模型运行环境
        """
        if category not in self.config['models']:
            raise ValueError(f"未知的模型类别: {category}")
        
        if name not in self.config['models'][category]:
            raise ValueError(f"未知的模型: {category}/{name}")
        
        if model_type:
            self.config['models'][category][name]['type'] = model_type
        
        if task:
            self.config['models'][category][name]['task'] = task
        
        if url:
            self.config['models'][category][name]['url'] = url
        
        if size >= 0:  # 使用-1作为未设置的标志
            self.config['models'][category][name]['size'] = size
        
        if description:
            self.config['models'][category][name]['description'] = description
        
        if environment:
            self.config['models'][category][name]['environment'] = environment
        
        # 保存配置
        self._save_config()
        
        logger.info(f"更新模型配置: {category}/{name}")
    
    def load_model(self, model_name: str, model_type: str = "yolo"):
        """
        加载模型
        
        Args:
            model_name: 模型名称
            model_type: 模型类型
            
        Returns:
            加载的模型对象，如果加载失败返回None
        """
        try:
            # 获取模型路径
            full_model_name = f"{model_type}/{model_name}"
            model_path = self.get_model_path(full_model_name)
            
            if not os.path.exists(model_path):
                logger.error(f"模型文件不存在: {model_path}")
                return None
            
            # 根据模型类型加载模型
            if model_type == "yolov5":
                # 加载YOLOv5模型
                import torch
                model = torch.load(model_path, map_location="cpu")
                logger.info(f"YOLOv5模型加载成功: {model_name}")
                return model
            elif model_type == "yolov8":
                # 加载YOLOv8模型
                import torch
                model = torch.load(model_path, map_location="cpu")
                logger.info(f"YOLOv8模型加载成功: {model_name}")
                return model
            elif model_type == "ppyolo":
                # 加载PP-YOLO模型
                logger.info(f"PP-YOLO模型加载成功: {model_name}")
                return {"model_path": model_path, "type": "ppyolo"}
            else:
                logger.warning(f"未知的模型类型: {model_type}")
                return None
        except Exception as e:
            logger.error(f"加载模型 {model_name} 时出错: {e}")
            return None
    
    def unload_model(self, model_name: str, model_type: str = "yolo"):
        """
        卸载模型
        
        Args:
            model_name: 模型名称
            model_type: 模型类型
        """
        logger.info(f"模型已卸载: {model_name} ({model_type})")
        # 实际的模型卸载逻辑可以根据需要实现
        pass
    
    def remove_model_config(self, category: str, name: str) -> None:
        """
        删除模型配置
        
        Args:
            category: 模型类别
            name: 模型名称
        """
        if category not in self.config['models']:
            raise ValueError(f"未知的模型类别: {category}")
        
        if name not in self.config['models'][category]:
            raise ValueError(f"未知的模型: {category}/{name}")
        
        # 删除模型配置
        del self.config['models'][category][name]
        
        # 如果类别为空，也删除类别
        if not self.config['models'][category]:
            del self.config['models'][category]
        
        # 保存配置
        self._save_config()
        
        logger.info(f"删除模型配置: {category}/{name}")
    
    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            import yaml
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            logger.warning("PyYAML未安装，无法保存配置")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")


def main():
    """主函数，用于测试模型管理功能"""
    manager = ModelManager()
    
    print("可用模型:")
    for model in manager.list_models():
        print(f"  {model['category']}/{model['name']} ({model['type']}, {model['task']}):")
        print(f"    描述: {model['description']}")
        print(f"    已下载: {'是' if model['downloaded'] else '否'}")
        print(f"    大小: {model['size'] / 1024 / 1024:.1f} MB")
    
    # 下载模型示例
    # model_name = "yolo/yolov5s"
    # print(f"\n下载模型: {model_name}")
    # model_path = manager.download_model(model_name)
    # print(f"模型路径: {model_path}")
    
    # 获取模型信息示例
    # model_info = manager.get_model_info(model_name)
    # print("\n模型信息:")
    # print(f"  名称: {model_info['name']}")
    # print(f"  类别: {model_info['category']}")
    # print(f"  类型: {model_info['type']}")
    # print(f"  任务: {model_info['task']}")
    # print(f"  描述: {model_info['description']}")
    # print(f"  已下载: {'是' if model_info['downloaded'] else '否'}")
    # print(f"  大小: {model_info['size'] / 1024 / 1024:.1f} MB")
    # print(f"  路径: {model_info['path']}")


if __name__ == "__main__":
    main()