import os
import subprocess
import platform
import re
from pathlib import Path

class HardwareDetector:
    def __init__(self):
        self.system = platform.system()
        self.detected_hardware = {}
    
    def detect_nvidia_gpu(self):
        """检测NVIDIA GPU"""
        try:
            if self.system == "Windows":
                # 使用WMIC检测NVIDIA GPU
                cmd = ['wmic', 'path', 'win32_VideoController', 'get', 'name']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if "NVIDIA" in result.stdout.upper():
                    return True
            else:
                # Linux/Mac检测
                cmd = ['lspci']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if "NVIDIA" in result.stdout:
                    return True
        except:
            pass
        return False
    
    def detect_amd_gpu(self):
        """检测AMD GPU"""
        try:
            if self.system == "Windows":
                cmd = ['wmic', 'path', 'win32_VideoController', 'get', 'name']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if "AMD" in result.stdout.upper() or "RADEON" in result.stdout.upper():
                    return True
            else:
                cmd = ['lspci']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if "AMD" in result.stdout or "Radeon" in result.stdout:
                    return True
        except:
            pass
        return False
    
    def detect_intel_gpu(self):
        """检测Intel GPU"""
        try:
            if self.system == "Windows":
                cmd = ['wmic', 'path', 'win32_VideoController', 'get', 'name']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if "INTEL" in result.stdout.upper():
                    return True
            else:
                cmd = ['lspci']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if "Intel" in result.stdout:
                    return True
        except:
            pass
        return False
    
    def detect_gpu(self):
        """检测GPU信息"""
        gpu_info = {
            'name': 'Unknown',
            'vendor': 'Unknown',
            'memory_gb': 0,
            'ai_acceleration': False
        }
        
        # 检测GPU厂商
        if self.detect_nvidia_gpu():
            gpu_info['vendor'] = 'NVIDIA'
            gpu_info['name'] = 'NVIDIA GPU'
            gpu_info['ai_acceleration'] = True
        elif self.detect_amd_gpu():
            gpu_info['vendor'] = 'AMD'
            gpu_info['name'] = 'AMD GPU'
            gpu_info['ai_acceleration'] = True
        elif self.detect_intel_gpu():
            gpu_info['vendor'] = 'Intel'
            gpu_info['name'] = 'Intel GPU'
            gpu_info['ai_acceleration'] = True
        
        return gpu_info
    
    def detect_cpu(self):
        """检测CPU信息"""
        cpu_info = {
            'name': platform.processor(),
            'cores': os.cpu_count(),
            'architecture': platform.architecture()[0]
        }
        return cpu_info
    
    def detect_memory(self):
        """检测内存信息"""
        try:
            if self.system == "Windows":
                cmd = ['wmic', 'computersystem', 'get', 'totalphysicalmemory']
                result = subprocess.run(cmd, capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    memory_bytes = int(lines[1].strip())
                    memory_gb = memory_bytes / (1024**3)
                    return {'total_gb': round(memory_gb, 1)}
            else:
                # Linux/Mac内存检测
                pass
        except:
            pass
        return {'total_gb': 0}
    
    def has_ai_acceleration(self):
        """检查是否支持AI加速"""
        gpu_info = self.detect_gpu()
        return gpu_info['ai_acceleration']
    
    def get_recommended_backend(self):
        """获取推荐的推理后端"""
        gpu_info = self.detect_gpu()
        if gpu_info['vendor'] == 'NVIDIA':
            return 'CUDA'
        elif gpu_info['vendor'] == 'AMD':
            return 'ROCm'
        elif gpu_info['vendor'] == 'Intel':
            return 'XPU'
        else:
            return 'CPU'
    
    def get_recommended_model_env(self):
        """获取推荐的模型环境"""
        backend = self.get_recommended_backend()
        if backend == 'CUDA':
            return 'pytorch-gpu'
        elif backend == 'ROCm':
            return 'pytorch-rocm'
        elif backend == 'XPU':
            return 'pytorch-xpu'
        else:
            return 'pytorch-cpu'
    
    def get_hardware_info(self):
        """获取完整的硬件信息"""
        return {
            'cpu': self.detect_cpu(),
            'gpu': self.detect_gpu(),
            'memory': self.detect_memory(),
            'ai_acceleration': self.has_ai_acceleration(),
            'recommended_backend': self.get_recommended_backend(),
            'recommended_model_env': self.get_recommended_model_env()
        }
    
    def detect_all(self):
        """检测所有硬件信息"""
        return self.get_hardware_info()

# 测试代码
if __name__ == "__main__":
    detector = HardwareDetector()
    
    cpu = detector.detect_cpu()
    print("CPU信息:", cpu)
    
    gpu = detector.detect_gpu()
    print("GPU信息:", gpu)
    
    memory = detector.detect_memory()
    print("内存信息:", memory)
    
    backend = detector.get_recommended_backend()
    print("推荐的后端:", backend)
    
    model_env = detector.get_recommended_model_env()
    print("推荐的模型环境:", model_env)
    
    info = detector.get_hardware_info()
    print("硬件详细信息:", info)