"""性能监控模块 - 支持多品牌GPU"""
import time
import threading
import psutil
import logging
from typing import Dict
from .hardware_detector import HardwareDetector

class PerformanceMonitor:
    """智能性能监控器，自动适配NVIDIA/AMD/Intel/CPU"""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("VisionDeploy.PerformanceMonitor")
        self.detector = HardwareDetector(config_dir="config")
        
        # 初始化监控数据
        self.performance_data = {
            'cpu': {'usage': 0, 'history': []},
            'memory': {'usage': 0, 'total': 0, 'available': 0},
            'gpu': self._init_gpu_data()
        }
        
        # 监控控制
        self.monitoring = False
        self.monitor_thread = None
        self.update_interval = 1.0
        
        # 根据硬件选择监控实现
        self.gpu_monitor = self._create_gpu_monitor()
        
    def _init_gpu_data(self) -> Dict:
        """初始化GPU数据结构"""
        gpu_info = self.detector.get_device_summary().get('gpu', [{}])[0]
        return {
            'brand': gpu_info.get('brand', 'Unknown'),
            'name': gpu_info.get('name', 'None'),
            'usage': 0,
            'memory_usage': 0,
            'memory_total': float(gpu_info.get('memory', '0').split()[0]) if 'memory' in gpu_info else 0,
            'type': gpu_info.get('type', 'unknown')
        }

    def _create_gpu_monitor(self):
        """根据硬件检测结果创建合适的GPU监控器"""
        backend = self.detector.get_recommended_backend()
        
        if backend == 'CUDA':
            try:
                from .gpu_monitors.nvidia import NvidiaMonitor
                return NvidiaMonitor()
            except ImportError:
                self.logger.warning("NVIDIA监控器初始化失败")
                
        elif backend == 'ROCm':
            try: 
                from .gpu_monitors.amd import AMDMontior
                return AMDMontior()
            except ImportError:
                self.logger.warning("AMD监控器初始化失败")
                
        elif backend == 'XPU':
            try:
                from .gpu_monitors.intel import IntelMonitor
                return IntelMonitor()
            except ImportError:
                self.logger.warning("Intel监控器初始化失败")
                
        # 默认回退到基本监控
        from .gpu_monitors.base import BaseMonitor
        return BaseMonitor()

    def start_monitoring(self):
        """启动性能监控线程"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, 
                daemon=True
            )
            self.monitor_thread.start()
            self.logger.info("性能监控已启动")

    def stop_monitoring(self):
        """停止性能监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self.logger.info("性能监控已停止")

    def _monitor_loop(self):
        """监控主循环"""
        while self.monitoring:
            self._update_performance_data()
            time.sleep(self.update_interval)

    def _update_performance_data(self):
        """更新所有性能数据"""
        # CPU监控
        self.performance_data['cpu']['usage'] = psutil.cpu_percent()
        self._update_history('cpu')
        
        # 内存监控
        mem = psutil.virtual_memory()
        self.performance_data['memory'].update({
            'usage': mem.percent,
            'total': mem.total / (1024 ** 3),  # GB
            'available': mem.available / (1024 ** 3)
        })
        
        # GPU监控
        if self.gpu_monitor:
            gpu_data = self.gpu_monitor.get_metrics()
            self.performance_data['gpu'].update({
                'usage': gpu_data.get('usage', 0),
                'memory_usage': gpu_data.get('memory_usage', 0),
                'memory_available': gpu_data.get('memory_available', 0)
            })

    def _update_history(self, component: str):
        """更新历史数据"""
        if len(self.performance_data[component]['history']) >= 100:
            self.performance_data[component]['history'].pop(0)
        self.performance_data[component]['history'].append(
            self.performance_data[component]['usage']
        )

    def get_performance_data(self) -> Dict:
        """获取当前性能数据"""
        return self.performance_data

    def update_ui(self):
        """更新UI性能显示"""
        if hasattr(self.app, 'dpg'):
            # 实际UI更新逻辑
            pass