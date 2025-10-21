"""
简化版硬件检测模块 - VisionDeploy Studio
用于快速检测系统中可用的计算硬件，避免长时间等待
"""

import os
import sys
import platform
import subprocess
import logging
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HardwareDetectorSimple")

class HardwareDetector:
    """简化版硬件检测类，用于快速识别系统中的计算设备"""
    
    def __init__(self):
        """初始化硬件检测器"""
        self.system = platform.system()
    
    def _safe_run(self, cmd: List[str], timeout: int = 5) -> subprocess.CompletedProcess:
        """安全运行命令，带超时控制"""
        try:
            return subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"命令执行超时: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 1, "", "Timeout")
        except Exception as e:
            logger.warning(f"命令执行失败: {' '.join(cmd)}, 错误: {e}")
            return subprocess.CompletedProcess(cmd, 1, "", str(e))
    
    def detect_nvidia_gpu(self) -> bool:
        """快速检测NVIDIA GPU"""
        try:
            if self.system == "Windows":
                # 使用WMIC快速检测
                result = self._safe_run(['wmic', 'path', 'win32_VideoController', 'get', 'name'])
                if result.returncode == 0 and "NVIDIA" in result.stdout.upper():
                    return True
            else:
                # Linux/Mac检测
                result = self._safe_run(['lspci'])
                if result.returncode == 0 and "NVIDIA" in result.stdout:
                    return True
        except Exception as e:
            logger.warning(f"检测NVIDIA GPU时出错: {e}")
        return False
    
    def detect_amd_gpu(self) -> bool:
        """快速检测AMD GPU"""
        try:
            if self.system == "Windows":
                result = self._safe_run(['wmic', 'path', 'win32_VideoController', 'get', 'name'])
                if result.returncode == 0:
                    output = result.stdout.upper()
                    if "AMD" in output or "RADEON" in output:
                        return True
            else:
                result = self._safe_run(['lspci'])
                if result.returncode == 0:
                    output = result.stdout
                    if "AMD" in output or "Radeon" in output:
                        return True
        except Exception as e:
            logger.warning(f"检测AMD GPU时出错: {e}")
        return False
    
    def detect_intel_gpu(self) -> bool:
        """快速检测Intel GPU"""
        try:
            if self.system == "Windows":
                result = self._safe_run(['wmic', 'path', 'win32_VideoController', 'get', 'name'])
                if result.returncode == 0 and "INTEL" in result.stdout.upper():
                    return True
            else:
                result = self._safe_run(['lspci'])
                if result.returncode == 0 and "Intel" in result.stdout:
                    return True
        except Exception as e:
            logger.warning(f"检测Intel GPU时出错: {e}")
        return False
    
    def detect_all_hardware(self) -> Dict[str, Any]:
        """快速检测所有硬件信息"""
        logger.info("开始快速硬件检测...")
        
        # 检测GPU
        nvidia_gpu = self.detect_nvidia_gpu()
        amd_gpu = self.detect_amd_gpu()
        intel_gpu = self.detect_intel_gpu()
        
        # 检测CPU核心数
        try:
            cpu_cores = os.cpu_count() or 0
        except:
            cpu_cores = 0
        
        # 检测系统架构
        architecture = platform.architecture()[0]
        
        hardware_info = {
            'nvidia_gpu': nvidia_gpu,
            'amd_gpu': amd_gpu,
            'intel_gpu': intel_gpu,
            'cpu_cores': cpu_cores,
            'architecture': architecture,
            'system': self.system
        }
        
        logger.info(f"硬件检测完成: {hardware_info}")
        return hardware_info
    
    def get_recommended_backend(self) -> str:
        """获取推荐的推理后端"""
        hardware = self.detect_all_hardware()
        
        if hardware['nvidia_gpu']:
            return 'CUDA'
        elif hardware['amd_gpu']:
            return 'ROCm'
        elif hardware['intel_gpu']:
            return 'XPU'
        else:
            return 'CPU'
    
    def get_recommended_model_env(self) -> str:
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

# 测试代码
if __name__ == "__main__":
    detector = HardwareDetector()
    info = detector.detect_all_hardware()
    print("硬件信息:", info)
    print("推荐后端:", detector.get_recommended_backend())
    print("推荐模型环境:", detector.get_recommended_model_env())