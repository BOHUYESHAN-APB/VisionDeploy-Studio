"""
应用程序核心模块 - VisionDeploy Studio
包含主应用程序的核心功能
"""

import os
import sys
import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

class ApplicationCore:
    """应用程序核心类，包含主应用程序的核心功能"""
    
    def __init__(self, base_dir: str):
        """初始化应用程序核心
        
        Args:
            base_dir: 应用程序基础目录
        """
        self.base_dir = base_dir
        self.logger = logging.getLogger("VisionDeploy.ApplicationCore")
        
        # 应用程序状态
        self.app_state = {
            'dark_mode': True,
            'performance_monitoring': True,
            'network_timeout': 30,
            'network_retries': 3,
            'models_path': os.path.join(self.base_dir, "resources", "models"),
            'environments_path': os.path.join(self.base_dir, "environments")
        }
        
        # 初始化硬件检测器
        from core.hardware_detector import HardwareDetector
        self.hardware_detector = HardwareDetector()
        self.device_summary = self.hardware_detector.get_device_summary()
        
        # 初始化环境管理器
        from core.environment_manager import EnvironmentManager
        self.environment_manager = EnvironmentManager(
            base_dir=self.base_dir
        )
        
        # 初始化模型管理器
        from core.model_manager import ModelManager
        self.model_manager = ModelManager(
            base_dir=self.base_dir
        )
        
        # 初始化性能监控器
        from app.performance_monitor import PerformanceMonitor
        self.performance_monitor = PerformanceMonitor(self)
        
        # 初始化推理引擎
        from app.inference_engine import InferenceEngine
        self.inference_engine = InferenceEngine(self)
    
    def init_logging(self):
        """初始化日志系统"""
        log_dir = os.path.join(self.base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "visiondeploy.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def load_config(self):
        """加载配置"""
        config_file = os.path.join(self.base_dir, "config", "app_config.json")
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.app_state.update(config)
                    self.logger.info("配置已加载")
            else:
                self.save_config()
                self.logger.info("创建了默认配置")
        except Exception as e:
            self.logger.error(f"加载配置时出错: {e}")
    
    def save_config(self):
        """保存配置"""
        config_dir = os.path.join(self.base_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, "app_config.json")
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_state, f, indent=4)
            self.logger.info("配置已保存")
        except Exception as e:
            self.logger.error(f"保存配置时出错: {e}")
    
    def refresh_models(self):
        """刷新模型列表"""
        return self.model_manager.list_models()
    
    def refresh_environments(self):
        """刷新环境列表"""
        return self.environment_manager.list_environments()
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        
        # 停止性能监控
        if self.performance_monitor:
            self.performance_monitor.stop_monitoring()
        
        # 停止推理
        if self.inference_engine:
            self.inference_engine.stop_inference()
        
        # 保存配置
        self.save_config()