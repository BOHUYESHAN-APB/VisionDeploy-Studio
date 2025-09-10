"""NVIDIA GPU监控器 - 使用NVML库"""
import logging
from typing import Dict, Optional
from .base import BaseMonitor

class NvidiaMonitor(BaseMonitor):
    """NVIDIA GPU监控器"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("VisionDeploy.NvidiaMonitor")
        self.nvml = None
        self.device_count = 0
        self._initialize_nvml()
        
    def _initialize_nvml(self):
        """初始化NVML库"""
        try:
            import pynvml
            self.nvml = pynvml
            self.nvml.nvmlInit()
            self.device_count = self.nvml.nvmlDeviceGetCount()
            self.logger.info(f"检测到 {self.device_count} 个NVIDIA GPU")
        except Exception as e:
            self.logger.warning(f"NVML初始化失败: {e}")
            self.available = False
            
    def get_metrics(self) -> Dict[str, float]:
        """获取NVIDIA GPU性能指标"""
        if not self.available or self.device_count == 0 or self.nvml is None:
            return super().get_metrics()
            
        try:
            # 确保nvml不为None
            if self.nvml is None:
                return super().get_metrics()
                
            # 获取第一个GPU的指标
            handle = self.nvml.nvmlDeviceGetHandleByIndex(0) if self.nvml else None
            if handle is None:
                return super().get_metrics()
            
            # GPU使用率
            utilization = self.nvml.nvmlDeviceGetUtilizationRates(handle) if self.nvml else None
            gpu_usage = utilization.gpu if utilization else 0
            
            # 内存使用情况
            memory_info = self.nvml.nvmlDeviceGetMemoryInfo(handle) if self.nvml else None
            memory_usage = (memory_info.used / memory_info.total) * 100 if memory_info and memory_info.total > 0 else 0
            memory_available = memory_info.free / (1024 ** 3) if memory_info else 0  # GB
            
            # 温度
            temperature = 0
            if self.nvml:
                try:
                    temperature = self.nvml.nvmlDeviceGetTemperature(
                        handle, self.nvml.NVML_TEMPERATURE_GPU
                    ) if self.nvml and hasattr(self.nvml, 'NVML_TEMPERATURE_GPU') else 0
                except:
                    temperature = 0
            
            return {
                'usage': float(gpu_usage),
                'memory_usage': float(memory_usage),
                'memory_available': float(memory_available),
                'temperature': float(temperature)
            }
            
        except Exception as e:
            self.logger.error(f"获取GPU指标失败: {e}")
            return super().get_metrics()
            
    def __del__(self):
        """清理NVML资源"""
        if self.nvml and self.available:
            try:
                self.nvml.nvmlShutdown()
            except:
                pass