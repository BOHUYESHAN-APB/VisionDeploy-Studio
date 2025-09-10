"""
硬件检测模块 - VisionDeploy Studio
用于检测系统中可用的计算硬件，包括CPU、GPU和其他加速器
"""

import os
import sys
import platform
import subprocess
import logging
import json as json_module
from typing import Dict, List, Optional, Tuple, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HardwareDetector")

class HardwareDetector:
    """硬件检测类，用于识别系统中的计算设备"""
    
    def __init__(self):
        """初始化硬件检测器"""
        self.system_info = self._get_system_info()
        self.cpu_info = self._get_cpu_info()
        self.memory_info = self._get_memory_info()
        self.gpu_info = {
            'nvidia': self._get_nvidia_gpu_info(),
            'amd': self._get_amd_gpu_info(),
            'intel': self._get_intel_gpu_info(),
            'huawei': self._get_huawei_npu_info(),
            'musa': self._get_musa_info()
        }
    
    def _get_system_info(self) -> Dict[str, str]:
        """获取系统基本信息"""
        return {
            'os': platform.system(),
            'os_version': platform.version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'python_version': sys.version
        }
    
    def _get_cpu_info(self) -> Dict[str, Any]:
        """获取CPU信息"""
        import psutil
        
        cpu_info = {
            'physical_cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'max_frequency': psutil.cpu_freq().max if psutil.cpu_freq() else None,
            'current_usage': psutil.cpu_percent(interval=0.1)
        }
        
        # 在Windows上尝试获取更详细的CPU信息
        if platform.system() == 'Windows':
            try:
                import wmi
                w = wmi.WMI()
                processor = w.Win32_Processor()[0]
                cpu_info.update({
                    'name': processor.Name,
                    'manufacturer': processor.Manufacturer,
                    'architecture': processor.Architecture
                })
            except ImportError:
                logger.warning("WMI模块未安装，无法获取详细CPU信息")
            except Exception as e:
                logger.warning(f"获取详细CPU信息失败: {e}")
        
        return cpu_info
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """获取内存信息"""
        import psutil
        
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percent': memory.percent
        }
    
    def _get_nvidia_gpu_info(self) -> List[Dict[str, Any]]:
        """获取NVIDIA GPU信息"""
        try:
            # 尝试导入pynvml
            import pynvml
            try:
                pynvml.nvmlInit()
            except Exception as init_error:
                logger.warning(f"NVML初始化失败: {init_error}")
                return []
            
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count == 0:
                pynvml.nvmlShutdown()
                return []
            
            gpu_info = []
            for i in range(device_count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    device_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    # 获取设备名称（处理可能的字节串）
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    
                    gpu_data = {
                        'index': i,
                        'name': name,
                        'total_memory': device_info.total,
                        'free_memory': device_info.free,
                        'used_memory': device_info.used,
                        'temperature': pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
                        'power_usage': pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0,  # 转换为瓦特
                        'power_limit': pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0,  # 转换为瓦特
                        'fan_speed': pynvml.nvmlDeviceGetFanSpeed(handle),
                        'utilization': pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    }
                    gpu_info.append(gpu_data)
                except Exception as device_error:
                    logger.warning(f"获取NVIDIA GPU设备 {i} 信息失败: {device_error}")
                    continue
            
            try:
                pynvml.nvmlShutdown()
            except:
                pass
            return gpu_info
        
        except ImportError:
            logger.warning("pynvml模块未安装，尝试使用nvidia-smi命令")
            return self._get_nvidia_gpu_info_cmd()
        except Exception as e:
            logger.warning(f"获取NVIDIA GPU信息失败: {e}")
            return []
    
    def _get_nvidia_gpu_info_cmd(self) -> List[Dict[str, Any]]:
        """使用nvidia-smi命令获取NVIDIA GPU信息"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=index,name,memory.total,memory.free,memory.used,temperature.gpu,power.draw,power.limit,fan.speed,utilization.gpu', '--format=csv,noheader,nounits'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            gpu_info = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                    
                values = [val.strip() for val in line.split(',')]
                if len(values) >= 10:
                    gpu_data = {
                        'index': int(values[0]),
                        'name': values[1],
                        'total_memory': float(values[2]) * 1024 * 1024,  # 转换为字节
                        'free_memory': float(values[3]) * 1024 * 1024,
                        'used_memory': float(values[4]) * 1024 * 1024,
                        'temperature': float(values[5]),
                        'power_usage': float(values[6]) if values[6] else None,
                        'power_limit': float(values[7]) if values[7] else None,
                        'fan_speed': float(values[8]) if values[8] else None,
                        'utilization': float(values[9])
                    }
                    gpu_info.append(gpu_data)
            
            return gpu_info
        except (subprocess.SubprocessError, FileNotFoundError, ValueError) as e:
            logger.warning(f"使用nvidia-smi获取GPU信息失败: {e}")
            return []
    
    def _get_amd_gpu_info(self) -> List[Dict[str, Any]]:
        """获取AMD GPU信息"""
        # 首先尝试使用rocm-smi工具
        amd_info = self._get_amd_gpu_info_rocm()
        if amd_info:
            return amd_info
            
        # 如果rocm-smi不可用，尝试其他方法
        if platform.system() == 'Windows':
            return self._get_amd_gpu_info_windows()
        elif platform.system() == 'Linux':
            return self._get_amd_gpu_info_linux()
        
        return []
    
    def _get_amd_gpu_info_rocm(self) -> List[Dict[str, Any]]:
        """使用rocm-smi获取AMD GPU信息"""
        try:
            # 首先检查rocm-smi是否可用
            result = subprocess.run(
                ['rocm-smi', '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            # 获取GPU信息
            result = subprocess.run(
                ['rocm-smi', '--showmeminfo', 'vram', '--showuse', '--json'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            import json
            data = json.loads(result.stdout)
            
            gpu_info = []
            for card_id, card_data in data.items():
                if not card_id.startswith('card'):
                    continue
                
                gpu_data = {
                    'index': int(card_id.replace('card', '')),
                    'name': card_data.get('GPU', {}).get('Card name', 'Unknown AMD GPU'),
                    'total_memory': int(card_data.get('VRAM Usage', {}).get('VRAM Total Memory (B)', '0')),
                    'used_memory': int(card_data.get('VRAM Usage', {}).get('VRAM Total Used Memory (B)', '0')),
                    'free_memory': int(card_data.get('VRAM Usage', {}).get('VRAM Total Free Memory (B)', '0')),
                    'temperature': float(card_data.get('Temperature', {}).get('Edge (Sensor)', '0').replace('c', '')),
                    'utilization': float(card_data.get('GPU use (%)').replace('%', '')) if 'GPU use (%)' in card_data else None
                }
                gpu_info.append(gpu_data)
            
            return gpu_info
            
        except FileNotFoundError:
            logger.debug("rocm-smi工具未安装")
            return []
        except subprocess.SubprocessError as e:
            logger.warning(f"执行rocm-smi命令失败: {e}")
            return []
        except json_module.JSONDecodeError as e:
            logger.warning(f"解析rocm-smi输出失败: {e}")
            return []
        except Exception as e:
            logger.warning(f"获取AMD GPU信息时发生意外错误: {e}")
            return []
    
    def _get_amd_gpu_info_windows(self) -> List[Dict[str, Any]]:
        """在Windows上获取AMD GPU信息"""
        try:
            import wmi
            w = wmi.WMI(namespace="root\\CIMV2")
            gpus = w.Win32_VideoController()
            
            gpu_info = []
            for i, gpu in enumerate(gpus):
                if "AMD" in gpu.Name or "Radeon" in gpu.Name:
                    gpu_data = {
                        'index': i,
                        'name': gpu.Name,
                        'adapter_ram': gpu.AdapterRAM if gpu.AdapterRAM else None,
                        'driver_version': gpu.DriverVersion,
                        'video_processor': gpu.VideoProcessor
                    }
                    gpu_info.append(gpu_data)
            
            return gpu_info
        except ImportError:
            logger.warning("WMI模块未安装，无法获取AMD GPU信息")
            return []
        except Exception as e:
            logger.warning(f"获取AMD GPU信息失败: {e}")
            return []
    
    def _get_amd_gpu_info_linux(self) -> List[Dict[str, Any]]:
        """在Linux上获取AMD GPU信息"""
        try:
            # 检查是否有AMD GPU设备
            result = subprocess.run(
                ['lspci', '|', 'grep', '-i', 'amd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
            
            if not result.stdout:
                return []
            
            gpu_info = []
            for i, line in enumerate(result.stdout.strip().split('\n')):
                if "VGA" in line or "Display" in line or "3D" in line:
                    gpu_data = {
                        'index': i,
                        'name': line.split(':')[-1].strip() if ':' in line else line.strip(),
                        'bus_id': line.split(' ')[0] if ' ' in line else None
                    }
                    gpu_info.append(gpu_data)
            
            return gpu_info
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"获取AMD GPU信息失败: {e}")
            return []
    
    def _get_intel_gpu_info(self) -> List[Dict[str, Any]]:
        """获取Intel GPU信息"""
        if platform.system() == 'Windows':
            return self._get_intel_gpu_info_windows()
        elif platform.system() == 'Linux':
            return self._get_intel_gpu_info_linux()
        
        return []
    
    def _get_intel_gpu_info_windows(self) -> List[Dict[str, Any]]:
        """在Windows上获取Intel GPU信息"""
        try:
            import wmi
            w = wmi.WMI(namespace="root\\CIMV2")
            gpus = w.Win32_VideoController()
            
            gpu_info = []
            for i, gpu in enumerate(gpus):
                if "Intel" in gpu.Name:
                    gpu_data = {
                        'index': i,
                        'name': gpu.Name,
                        'adapter_ram': gpu.AdapterRAM if gpu.AdapterRAM else None,
                        'driver_version': gpu.DriverVersion,
                        'video_processor': gpu.VideoProcessor
                    }
                    gpu_info.append(gpu_data)
            
            return gpu_info
        except ImportError:
            logger.warning("WMI模块未安装，无法获取Intel GPU信息")
            return []
        except Exception as e:
            logger.warning(f"获取Intel GPU信息失败: {e}")
            return []
    
    def _get_intel_gpu_info_linux(self) -> List[Dict[str, Any]]:
        """在Linux上获取Intel GPU信息"""
        try:
            # 检查是否有Intel GPU设备
            result = subprocess.run(
                ['lspci', '|', 'grep', '-i', 'intel'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
            
            if not result.stdout:
                return []
            
            gpu_info = []
            for i, line in enumerate(result.stdout.strip().split('\n')):
                if "VGA" in line or "Display" in line or "3D" in line:
                    gpu_data = {
                        'index': i,
                        'name': line.split(':')[-1].strip() if ':' in line else line.strip(),
                        'bus_id': line.split(' ')[0] if ' ' in line else None
                    }
                    gpu_info.append(gpu_data)
            
            return gpu_info
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"获取Intel GPU信息失败: {e}")
            return []
    
    def _get_huawei_npu_info(self) -> List[Dict[str, Any]]:
        """获取华为NPU信息"""
        try:
            # 检查npu-smi工具是否可用
            result = subprocess.run(
                ['npu-smi', 'info', '-l'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            npu_info = []
            current_npu = {
                'index': 0,
                'name': '',
                'health': '',
                'power_usage': 0.0,
                'temperature': 0.0,
                'used_memory': 0,
                'total_memory': 0,
                'free_memory': 0,
                'utilization': 0.0
            }
            
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                
                if line.startswith('NPU ID'):
                    if current_npu['name'] or current_npu['health']:  # 如果已有数据，则添加到列表中
                        npu_info.append(current_npu.copy())
                    current_npu = {
                        'index': int(line.split(':')[1].strip()),
                        'name': '',
                        'health': '',
                        'power_usage': 0.0,
                        'temperature': 0.0,
                        'used_memory': 0,
                        'total_memory': 0,
                        'free_memory': 0,
                        'utilization': 0.0
                    }
                
                elif ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if key == 'name' or key == 'chip_name':
                        current_npu['name'] = str(value)
                    elif key == 'health' or key == 'health_status':
                        current_npu['health'] = str(value)
                    elif key == 'power' and 'W' in value:
                        current_npu['power_usage'] = float(value.replace('W', '').strip())
                    elif key == 'temperature' and 'C' in value:
                        current_npu['temperature'] = float(value.replace('C', '').strip())
                    elif key == 'memory_usage' and 'MB' in value:
                        used, total = value.split('/')
                        used = float(used.replace('MB', '').strip())
                        total = float(total.replace('MB', '').strip())
                        current_npu['used_memory'] = int(used * 1024 * 1024)  # 转换为字节
                        current_npu['total_memory'] = int(total * 1024 * 1024)
                        current_npu['free_memory'] = int((total - used) * 1024 * 1024)
                    elif key == 'utilization' and '%' in value:
                        current_npu['utilization'] = float(value.replace('%', '').strip())
            
            if current_npu['name'] or current_npu['health']:  # 添加最后一个NPU
                npu_info.append(current_npu)
            
            return npu_info
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"获取华为NPU信息失败: {e}")
            return []
    
    def _get_musa_info(self) -> List[Dict[str, Any]]:
        """获取摩尔线程MUSA信息"""
        try:
            # 检查musa-smi工具是否可用
            result = subprocess.run(
                ['musa-smi'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            musa_info = []
            current_device = {
                'index': 0,
                'name': '',
                'temperature': 0.0,
                'used_memory': 0,
                'total_memory': 0,
                'free_memory': 0,
                'utilization': 0.0,
                'power_usage': 0.0
            }
            parsing_device = False
            
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                
                if line.startswith('Device'):
                    if current_device['name'] and parsing_device:  # 如果已有数据，则添加到列表中
                        musa_info.append(current_device.copy())
                    current_device = {
                        'index': len(musa_info),
                        'name': '',
                        'temperature': 0.0,
                        'used_memory': 0,
                        'total_memory': 0,
                        'free_memory': 0,
                        'utilization': 0.0,
                        'power_usage': 0.0
                    }
                    parsing_device = True
                
                elif parsing_device and ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if key == 'name' or key == 'product_name':
                        current_device['name'] = str(value)
                    elif key == 'temperature' and 'C' in value:
                        current_device['temperature'] = float(value.replace('C', '').strip())
                    elif key == 'memory_usage' and 'MiB' in value:
                        if '/' in value:
                            used, total = value.split('/')
                            used = float(used.replace('MiB', '').strip())
                            total = float(total.replace('MiB', '').strip())
                            current_device['used_memory'] = int(used * 1024 * 1024)  # 转换为字节
                            current_device['total_memory'] = int(total * 1024 * 1024)
                            current_device['free_memory'] = int((total - used) * 1024 * 1024)
                    elif key == 'gpu_utilization' and '%' in value:
                        current_device['utilization'] = float(value.replace('%', '').strip())
                    elif key == 'power' and 'W' in value:
                        current_device['power_usage'] = float(value.replace('W', '').strip())
            
            if current_device['name'] and parsing_device:  # 添加最后一个设备
                musa_info.append(current_device)
            
            return musa_info
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"获取摩尔线程MUSA信息失败: {e}")
            return []
    
    def get_best_device(self) -> Tuple[str, Dict[str, Any]]:
        """获取最佳计算设备"""
        # 优先级: NVIDIA GPU > AMD GPU > Intel GPU > 华为NPU > 摩尔线程MUSA > CPU
        
        if self.gpu_info['nvidia']:
            return 'nvidia', self.gpu_info['nvidia'][0]
        elif self.gpu_info['amd']:
            return 'amd', self.gpu_info['amd'][0]
        elif self.gpu_info['intel']:
            return 'intel', self.gpu_info['intel'][0]
        elif self.gpu_info['huawei']:
            return 'huawei', self.gpu_info['huawei'][0]
        elif self.gpu_info['musa']:
            return 'musa', self.gpu_info['musa'][0]
        else:
            return 'cpu', self.cpu_info
    
    def get_all_devices(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有计算设备"""
        devices = {}
        
        for device_type, info in self.gpu_info.items():
            if info:
                devices[device_type] = info
        
        if not devices:
            devices['cpu'] = [self.cpu_info]
        
        return devices
    
    def get_device_summary(self) -> Dict[str, Any]:
        """获取设备摘要信息"""
        device_type, device_info = self.get_best_device()
        
        summary = {
            'best_device': {
                'type': device_type,
                'name': device_info.get('name', 'Unknown'),
                'memory': device_info.get('total_memory', None) if device_type != 'cpu' else self.memory_info['total']
            },
            'system': self.system_info,
            'devices': {
                'cpu': {
                    'cores': self.cpu_info['physical_cores'],
                    'threads': self.cpu_info['logical_cores']
                },
                'memory': {
                    'total_gb': round(self.memory_info['total'] / (1024**3), 2),
                    'available_gb': round(self.memory_info['available'] / (1024**3), 2)
                }
            }
        }
        
        # 添加GPU信息
        for gpu_type in ['nvidia', 'amd', 'intel', 'huawei', 'musa']:
            if self.gpu_info[gpu_type]:
                summary['devices'][gpu_type] = {
                    'count': len(self.gpu_info[gpu_type]),
                    'models': [gpu.get('name', 'Unknown') for gpu in self.gpu_info[gpu_type]]
                }
        
        return summary
    
    # 添加缺失的方法以兼容main.py
    def detect_all_hardware(self) -> Dict[str, Any]:
        """检测所有硬件信息（为兼容main.py而添加）"""
        # 模拟硬件检测结果
        nvidia_gpu = len(self.gpu_info['nvidia']) > 0
        amd_gpu = len(self.gpu_info['amd']) > 0
        intel_gpu = len(self.gpu_info['intel']) > 0
        
        # 检查CUDA是否可用
        cuda_available = False
        try:
            import torch
            cuda_available = torch.cuda.is_available()
        except ImportError:
            cuda_available = False
        
        # 检查Intel AI能力
        intel_ai_capable = False
        if intel_gpu:
            # 简单检查，如果有Intel GPU就认为有AI能力
            intel_ai_capable = True
        
        return {
            'nvidia_gpu': nvidia_gpu,
            'amd_gpu': amd_gpu,
            'intel_gpu': intel_gpu,
            'cuda_available': cuda_available,
            'intel_ai_capable': intel_ai_capable
        }
    
    def get_recommended_backend(self) -> str:
        """获取推荐的后端（为兼容main.py而添加）"""
        device_type, _ = self.get_best_device()
        
        backend_map = {
            'nvidia': 'cuda',
            'amd': 'rocm',
            'intel': 'xpu',
            'huawei': 'cann',
            'musa': 'musa',
            'cpu': 'cpu'
        }
        
        return backend_map.get(device_type, 'cpu')
    
    def get_recommended_model_env(self) -> str:
        """获取推荐的模型环境（为兼容main.py而添加）"""
        device_type, _ = self.get_best_device()
        
        env_map = {
            'nvidia': 'yolov5-cuda',
            'amd': 'yolov8-rocm',
            'intel': 'ppyolo-xpu',
            'huawei': 'ppyolo-xpu',
            'musa': 'ppyolo-xpu',
            'cpu': 'yolov5-cuda'
        }
        
        return env_map.get(device_type, 'yolov5-cuda')


def main():
    """主函数，用于测试硬件检测功能"""
    detector = HardwareDetector()
    
    print("系统信息:")
    for key, value in detector.system_info.items():
        print(f"  {key}: {value}")
    
    print("\nCPU信息:")
    for key, value in detector.cpu_info.items():
        print(f"  {key}: {value}")
    
    print("\n内存信息:")
    print(f"  总内存: {detector.memory_info['total'] / (1024**3):.2f} GB")
    print(f"  可用内存: {detector.memory_info['available'] / (1024**3):.2f} GB")
    print(f"  使用率: {detector.memory_info['percent']}%")
    
    for gpu_type in ['nvidia', 'amd', 'intel', 'huawei', 'musa']:
        if detector.gpu_info[gpu_type]:
            print(f"\n{gpu_type.upper()} GPU信息:")
            for i, gpu in enumerate(detector.gpu_info[gpu_type]):
                print(f"  设备 {i}:")
                for key, value in gpu.items():
                    if key in ['total_memory', 'free_memory', 'used_memory'] and value is not None:
                        print(f"    {key}: {value / (1024**3):.2f} GB")
                    else:
                        print(f"    {key}: {value}")
    
    print("\n最佳设备:")
    device_type, device_info = detector.get_best_device()
    print(f"  类型: {device_type}")
    print(f"  名称: {device_info.get('name', 'Unknown')}")
    
    print("\n设备摘要:")
    summary = detector.get_device_summary()
    import json
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

# 创建全局实例
hardware_detector = HardwareDetector()