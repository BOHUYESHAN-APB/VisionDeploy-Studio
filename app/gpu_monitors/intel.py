"""Intel GPU监控器 - 支持Intel核显和独显"""
import logging
import subprocess
from typing import Dict
from .base import BaseMonitor

class IntelMonitor(BaseMonitor):
    """Intel GPU监控器"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("VisionDeploy.IntelMonitor")
        self._detect_intel_gpu()
        
    def _detect_intel_gpu(self):
        """检测Intel GPU可用性"""
        try:
            # Windows系统检测
            import platform
            if platform.system() == 'Windows':
                try:
                    import wmi
                    w = wmi.WMI()
                    for gpu in w.Win32_VideoController():
                        if 'Intel' in gpu.Name:
                            self.logger.info(f"检测到Intel GPU: {gpu.Name}")
                            return
                except:
                    pass
            
            # Linux系统检测
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            if 'Intel' in result.stdout and 'VGA' in result.stdout:
                self.logger.info("检测到Intel集成显卡")
                return
                
            self.available = False
            self.logger.warning("未检测到Intel GPU")
            
        except Exception as e:
            self.logger.warning(f"Intel GPU检测失败: {e}")
            self.available = False
            
    def get_metrics(self) -> Dict[str, float]:
        """获取Intel GPU性能指标"""
        if not self.available:
            return super().get_metrics()
            
        try:
            # Windows系统使用WMI获取性能数据
            import platform
            if platform.system() == 'Windows':
                try:
                    import wmi
                    w = wmi.WMI()
                    
                    # 获取GPU使用率（需要Intel驱动支持性能计数器）
                    for gpu in w.Win32_VideoController():
                        if 'Intel' in gpu.Name:
                            # 估算使用率（实际实现需要Intel性能API）
                            usage = self._estimate_usage()
                            return {
                                'usage': float(usage),
                                'memory_usage': 0.0,
                                'memory_available': 0.0,
                                'temperature': 0.0
                            }
                except:
                    pass
            
            # 默认返回基础指标
            return {
                'usage': 0.0,
                'memory_usage': 0.0,
                'memory_available': 0.0,
                'temperature': 0.0
            }
            
        except Exception as e:
            self.logger.error(f"获取Intel GPU指标失败: {e}")
            return super().get_metrics()
            
    def _estimate_usage(self) -> float:
        """估算Intel GPU使用率（占位符实现）"""
        # 实际实现需要Intel GPU性能API
        # 这里返回一个估算值
        return 0.0