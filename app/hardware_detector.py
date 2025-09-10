"""硬件检测模块 - 支持两阶段硬件检测"""
import os
import platform
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from .config_manager import ConfigManager

class HardwareDetector:
    """两阶段硬件检测器
    
    第一阶段: 快速基础检测 (启动时)
    第二阶段: 详细能力检测 (运行时)
    """
    
    def __init__(self, config_dir: str = "config"):
        """初始化硬件检测器
        
        Args:
            config_dir: 配置目录路径
        """
        self.system = platform.system()
        self.config_manager = ConfigManager(config_dir)
        self.device_summary = {
            'gpu': [],
            'cpu': {},
            'os': f"{self.system} {platform.release()}",
            'detection_stage': 'initial'
        }
        
        # 第一阶段检测 (快速)
        self._initial_detection()

    def _initial_detection(self):
        """第一阶段快速检测"""
        self.device_summary['cpu'] = self._quick_cpu_detect()
        self._quick_gpu_detect()
        self.config_manager.save_config(self.device_summary)

    def _quick_cpu_detect(self) -> Dict[str, str]:
        """快速CPU检测"""
        try:
            brand = 'Intel' if 'Intel' in platform.processor() else 'AMD'
            return {
                'brand': brand,
                'name': platform.processor(),
                'cores': self._get_cpu_cores(),
                'arch': platform.machine()
            }
        except:
            return {'brand': 'Unknown', 'name': 'Unknown', 'cores': 'Unknown', 'arch': 'Unknown'}

    def _get_cpu_cores(self) -> str:
        """获取CPU核心数"""
        try:
            return str(os.cpu_count()) if os.cpu_count() is not None else "Unknown"
        except:
            return "Unknown"

    def _quick_gpu_detect(self):
        """快速GPU检测"""
        if self._try_detect_nvidia(quick=True):
            return
        if self._try_detect_amd(quick=True):
            return
        self._try_detect_intel(quick=True)

    def _detailed_detection(self):
        """第二阶段详细检测"""
        self.device_summary['detection_stage'] = 'detailed'
        self.device_summary['cpu'].update(self._detailed_cpu_detect())
        self._detailed_gpu_detect()
        self.config_manager.save_config(self.device_summary)

    def _detailed_cpu_detect(self) -> Dict[str, str]:
        """详细CPU检测"""
        # 这里可以添加更详细的CPU检测逻辑
        return {}

    def _detailed_gpu_detect(self):
        """详细GPU检测"""
        # 这里可以添加更详细的GPU检测逻辑
        pass

    def _try_detect_nvidia(self, quick: bool = False) -> bool:
        """尝试检测NVIDIA GPU
        
        Args:
            quick: 是否快速检测模式
        """
        try:
            # 快速检测只检查是否存在NVIDIA设备
            if quick:
                if self.system == 'Windows':
                    try:
                        import wmi
                        w = wmi.WMI()
                        for gpu in w.Win32_VideoController():
                            if 'NVIDIA' in gpu.Name:
                                self.device_summary['gpu'].append({
                                    'brand': 'NVIDIA',
                                    'type': 'discrete',
                                    'detected': True
                                })
                                return True
                    except:
                        pass
                return False
            else:
                # 详细检测
                try:
                    smi_output = subprocess.check_output(
                        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"]
                    ).decode().strip()
                    for line in smi_output.split('\n'):
                        name, mem, driver = line.split(',')
                        self.device_summary['gpu'].append({
                            'brand': 'NVIDIA',
                            'name': name.strip(),
                            'memory': mem.strip(),
                            'driver': driver.strip(),
                            'type': 'discrete',
                            'cuda_cores': self._get_cuda_cores(),
                            'cuda_version': self._get_cuda_version()
                        })
                    return True
                except:
                    pass

                # 回退到通用检测
                if self.system == 'Windows':
                    try:
                        import wmi
                        w = wmi.WMI()
                        for gpu in w.Win32_VideoController():
                            if 'NVIDIA' in gpu.Name:
                                self.device_summary['gpu'].append({
                                    'brand': 'NVIDIA',
                                    'name': gpu.Name,
                                    'memory': f"{int(gpu.AdapterRAM)/1024**2:.0f} MB",
                                    'type': 'discrete'
                                })
                        return len(self.device_summary['gpu']) > 0
                    except:
                        pass
        except:
            pass
        return False

    def _get_cuda_cores(self) -> int:
        """获取CUDA核心数(需要详细检测阶段)"""
        # 实际实现需要根据具体GPU型号查询
        return 0

    def _get_cuda_version(self) -> str:
        """获取CUDA版本(需要详细检测阶段)"""
        # 实际实现需要检测CUDA安装情况
        return "unknown"

    def _try_detect_amd(self, quick: bool = False) -> bool:
        """尝试检测AMD GPU
        
        Args:
            quick: 是否快速检测模式
        """
        try:
            # 快速检测只检查是否存在AMD设备
            if quick:
                if self.system == 'Windows':
                    try:
                        import wmi
                        w = wmi.WMI()
                        for gpu in w.Win32_VideoController():
                            if 'AMD' in gpu.Name or 'Radeon' in gpu.Name:
                                self.device_summary['gpu'].append({
                                    'brand': 'AMD',
                                    'type': 'discrete',
                                    'detected': True
                                })
                                return True
                    except:
                        pass
                return False
            else:
                # 详细检测实现
                if self.system == 'Windows':
                    try:
                        import wmi
                        w = wmi.WMI()
                        for gpu in w.Win32_VideoController():
                            if 'AMD' in gpu.Name or 'Radeon' in gpu.Name:
                                self.device_summary['gpu'].append({
                                    'brand': 'AMD',
                                    'name': gpu.Name,
                                    'memory': f"{int(gpu.AdapterRAM)/1024**2:.0f} MB",
                                    'type': 'discrete'
                                })
                        return len(self.device_summary['gpu']) > 0
                    except:
                        pass
        except:
            pass
        return False

    def _try_detect_intel(self, quick: bool = False) -> bool:
        """尝试检测Intel核显
        
        Args:
            quick: 是否快速检测模式
        """
        try:
            # 快速检测只检查是否存在Intel设备
            if quick:
                if self.system == 'Windows':
                    try:
                        import wmi
                        w = wmi.WMI()
                        for gpu in w.Win32_VideoController():
                            if 'Intel' in gpu.Name:
                                self.device_summary['gpu'].append({
                                    'brand': 'Intel',
                                    'type': 'integrated',
                                    'detected': True
                                })
                                return True
                    except:
                        pass
                
                # 通用检测
                if 'Intel' in platform.processor():
                    self.device_summary['gpu'].append({
                        'brand': 'Intel',
                        'type': 'integrated',
                        'detected': True
                    })
                    return True
                return False
            else:
                # 详细检测实现
                if self.system == 'Windows':
                    try:
                        import wmi
                        w = wmi.WMI()
                        for gpu in w.Win32_VideoController():
                            if 'Intel' in gpu.Name:
                                self.device_summary['gpu'].append({
                                    'brand': 'Intel',
                                    'name': gpu.Name,
                                    'memory': f"{int(gpu.AdapterRAM)/1024**2:.0f} MB",
                                    'type': 'integrated'
                                })
                        return len(self.device_summary['gpu']) > 0
                    except:
                        pass
                
                # Linux/macOS检测
                if 'Intel' in platform.processor():
                    self.device_summary['gpu'].append({
                        'brand': 'Intel',
                        'name': 'Integrated Graphics',
                        'memory': 'Shared',
                        'type': 'integrated'
                    })
                    return True
        except:
            pass
        return False

    def get_device_summary(self) -> Dict[str, List[Dict]]:
        """获取设备摘要信息"""
        return self.device_summary

    def get_recommended_backend(self) -> str:
        """获取推荐的计算后端
        
        Returns:
            backend_type 例如 'CUDA'
        """
        config = self.config_manager.load_config()
        if not config:
            return 'CPU'
            
        # 获取推荐的环境
        recommended_env = self.get_recommended_model_env()
        
        # 根据环境映射到后端
        backend_map = {
            'yolov5-cuda': 'CUDA',
            'yolov8-rocm': 'ROCM',
            'ppyolo-xpu': 'XPU'
        }
        
        return backend_map.get(recommended_env, 'CPU')
        
    def get_recommended_model_env(self) -> str:
        """获取推荐的模型环境
        
        Returns:
            recommended_env 例如 'yolov5-cuda'
        """
        # 检查是否有GPU设备
        gpus = self.device_summary.get('gpu', [])
        if not gpus:
            return 'yolov5-cuda'  # 默认使用CPU环境
            
        # 根据检测到的GPU类型推荐环境
        for gpu in gpus:
            brand = gpu.get('brand', '').lower()
            if 'nvidia' in brand:
                return 'yolov5-cuda'
            elif 'amd' in brand:
                return 'yolov8-rocm'
            elif 'intel' in brand:
                return 'ppyolo-xpu'
                
        # 默认返回
        return 'yolov5-cuda'
        
    def run_detailed_detection(self):
        """执行第二阶段详细检测"""
        self._detailed_detection()