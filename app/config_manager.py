"""配置管理模块 - 负责硬件配置的持久化存储"""
import os
import time
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """管理应用程序的硬件配置"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_path = Path(config_dir) / "hardware_config.yaml"
        self.config_dir = Path(config_dir)
        self._ensure_config_dir()
        
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def save_config(self, hardware_info: Dict[str, Any]):
        """保存硬件配置到YAML文件
        
        Args:
            hardware_info: 硬件信息字典，包含gpu/cpu等详细信息
        """
        config = {
            'version': '1.0',
            'detection_time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'hardware': hardware_info
        }
        
        with open(self.config_path, 'w') as f:
            yaml.safe_dump(config, f, sort_keys=False)
            
    def load_config(self) -> Optional[Dict[str, Any]]:
        """从YAML文件加载硬件配置
        
        Returns:
            配置字典，如果文件不存在则返回None
        """
        if not self.config_path.exists():
            return None
            
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return None
            
    def get_recommended_environments(self) -> Dict[str, str]:
        """获取推荐的Python环境配置
        
        Returns:
            字典格式: {python_version: backend_type}
        """
        config = self.load_config()
        if not config:
            return {}
            
        hardware = config.get('hardware', {})
        # GPU信息是列表，获取第一个GPU的类型
        gpu_list = hardware.get('gpu', [])
        gpu_type = gpu_list[0].get('type', 'unknown') if gpu_list else 'unknown'
        
        # 根据硬件类型推荐环境
        envs = {
            '3.8': 'xpu' if gpu_type == 'integrated' else 'cuda',
            '3.9': 'xpu' if gpu_type == 'integrated' else 'cuda', 
            '3.10': 'cpu'  # 保底选项
        }
        
        return envs