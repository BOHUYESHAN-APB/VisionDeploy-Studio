import subprocess
import json
import tempfile
import os
import platform
from pathlib import Path
import threading
import time
from .hardware_detector import hardware_detector

class ModelInvoker:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.environments_dir = self.base_dir / "environments"
        self.resources_dir = self.base_dir / "resources"
        
        # 模型环境配置
        self.env_configs = {
            'yolov5-cuda': {
                'python_path': lambda: self._get_python_executable_path('3.8'),
                'script': self.base_dir / "models" / "yolov5_detect.py",
                'timeout': 30,
                'env_vars': {
                    'PYTHONPATH': str(self.resources_dir / "python" / "3.8")
                }
            },
            'yolov8-rocm': {
                'python_path': lambda: self._get_python_executable_path('3.9'),
                'script': self.base_dir / "models" / "yolov8_detect.py", 
                'timeout': 30,
                'env_vars': {
                    'PYTHONPATH': str(self.resources_dir / "python" / "3.9")
                }
            },
            'ppyolo-xpu': {
                'python_path': lambda: self._get_python_executable_path('3.10'),
                'script': self.base_dir / "models" / "ppyolo_detect.py",
                'timeout': 30,
                'env_vars': {
                    'PYTHONPATH': str(self.resources_dir / "python" / "3.10")
                }
            }
        }
        
        self.active_processes = {}
    
    def _get_python_executable_path(self, version: str) -> Path:
        """获取指定版本的Python可执行文件路径"""
        if platform.system() == 'Windows':
            return self.resources_dir / "python" / f"python{version}" / "python.exe"
        else:
            return self.resources_dir / "python" / f"python{version}" / "bin" / "python"
    
    def get_python_path(self, env_name):
        """获取Python解释器路径"""
        if env_name not in self.env_configs:
            raise ValueError(f"未知的环境: {env_name}")
        
        python_path = self.env_configs[env_name]['python_path']()
        if not python_path.exists():
            raise FileNotFoundError(f"Python解释器不存在: {python_path}")
        
        return python_path
    
    def invoke_model(self, env_name, image_path, confidence=0.5, iou=0.45):
        """调用模型进行推理"""
        if env_name not in self.env_configs:
            raise ValueError(f"未知的环境: {env_name}")
        
        config = self.env_configs[env_name]
        python_path = self.get_python_path(env_name)
        script_path = config['script']
        
        if not script_path.exists():
            raise FileNotFoundError(f"模型脚本不存在: {script_path}")
        
        if not Path(image_path).exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 构建命令
        cmd = [
            str(python_path),
            str(script_path),
            '--image', str(image_path),
            '--confidence', str(confidence),
            '--iou', str(iou),
            '--output-format', 'json'
        ]
        
        # 设置环境变量，确保使用UTF-8编码
        env = os.environ.copy()
        env.update(config.get('env_vars', {}))
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 初始化process_id
        process_id = None
        
        # 执行推理
        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # 显式指定编码
                cwd=str(self.base_dir)
            )
            
            # 记录进程
            process_id = f"{env_name}_{int(time.time())}"
            self.active_processes[process_id] = process
            
            # 等待完成
            stdout, stderr = process.communicate(timeout=config['timeout'])
            
            # 移除进程记录
            if process_id in self.active_processes:
                del self.active_processes[process_id]
            
            # 检查返回码
            if process.returncode != 0:
                raise Exception(f"模型推理失败: {stderr}")
            
            # 解析JSON输出
            try:
                result = json.loads(stdout.strip())
                return result
            except json.JSONDecodeError:
                raise Exception(f"输出解析失败: {stdout}")
                
        except subprocess.TimeoutExpired:
            # 超时处理
            if process_id and process_id in self.active_processes:
                process = self.active_processes[process_id]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()
                del self.active_processes[process_id]
            raise TimeoutError(f"模型推理超时: {env_name}")
        
        except Exception as e:
            if process_id and process_id in self.active_processes:
                del self.active_processes[process_id]
            raise
    
    def invoke_model_async(self, env_name, image_path, callback, confidence=0.5, iou=0.45):
        """异步调用模型"""
        def async_task():
            try:
                result = self.invoke_model(env_name, image_path, confidence, iou)
                callback(result, None)
            except Exception as e:
                callback(None, str(e))
        
        thread = threading.Thread(target=async_task)
        thread.daemon = True
        thread.start()
        return thread
    
    def invoke_best_model(self, image_path, confidence=0.5, iou=0.45):
        """自动选择最佳模型进行推理"""
        # 获取硬件推荐
        try:
            # 使用正确的API获取推荐的模型环境
            recommended_env = hardware_detector.get_recommended_model_env()
        except:
            recommended_env = 'yolov5-cuda'
        
        # 按优先级尝试不同的环境
        env_priority = [recommended_env]
        
        # 添加备选环境
        if recommended_env != 'yolov5-cuda':
            env_priority.append('yolov5-cuda')
        if recommended_env != 'yolov8-rocm':
            env_priority.append('yolov8-rocm')
        if recommended_env != 'ppyolo-xpu':
            env_priority.append('ppyolo-xpu')
        
        last_error = None
        for env_name in env_priority:
            try:
                result = self.invoke_model(env_name, image_path, confidence, iou)
                return result, env_name
            except Exception as e:
                last_error = e
                print(f"{env_name} 推理失败: {e}")
                continue
        
        raise Exception(f"所有模型推理失败，最后错误: {last_error}")
    
    def stop_all_processes(self):
        """停止所有活跃进程"""
        for process_id, process in list(self.active_processes.items()):
            try:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except:
                    process.kill()
            except:
                pass
            finally:
                if process_id in self.active_processes:
                    del self.active_processes[process_id]
    
    def get_process_status(self):
        """获取当前进程状态"""
        status = {}
        for process_id, process in self.active_processes.items():
            status[process_id] = {
                'returncode': process.poll(),
                'alive': process.poll() is None
            }
        return status

# 单例模式
model_invoker = ModelInvoker()

if __name__ == "__main__":
    # 测试代码
    invoker = ModelInvoker()
    
    # 测试硬件检测
    # 注意：HardwareDetector类中没有get_hardware_info方法，我们使用device summary替代
    try:
        hardware_summary = hardware_detector.get_device_summary()
        print("硬件信息:", hardware_summary)
    except:
        print("无法获取硬件信息")
    
    # 创建一个测试图片
    test_image = Path("test_image.jpg")
    if not test_image.exists():
        # 创建一个简单的测试图片
        from PIL import Image, ImageDraw
        # 修复颜色参数类型错误，先创建图像再填充颜色
        img = Image.new('RGB', (640, 480))
        # 填充红色
        img.paste((255, 0, 0), (0, 0, 640, 480))
        draw = ImageDraw.Draw(img)
        draw.text((100, 100), "Test Image", fill='white')
        img.save(test_image)
        print("创建测试图片:", test_image)
    
    try:
        # 尝试调用最佳模型
        result, used_env = invoker.invoke_best_model(str(test_image))
        print(f"使用环境: {used_env}")
        print("推理结果:", result)
        
    except Exception as e:
        print("推理测试失败:", e)
    
    finally:
        # 清理测试文件
        if test_image.exists():
            test_image.unlink()
            print("清理测试文件")