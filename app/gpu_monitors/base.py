"""基础GPU监控器 - 所有GPU监控器的基类"""
from typing import Dict

class BaseMonitor:
    """基础GPU监控器，提供默认实现"""
    
    def __init__(self):
        self.available = True
        
    def get_metrics(self) -> Dict[str, float]:
        """获取GPU性能指标
        
        Returns:
            包含GPU使用率和内存使用情况的字典
        """
        return {
            'usage': 0.0,
            'memory_usage': 0.0,
            'memory_available': 0.0,
            'temperature': 0.0
        }
        
    def is_available(self) -> bool:
        """检查监控器是否可用"""
        return self.available