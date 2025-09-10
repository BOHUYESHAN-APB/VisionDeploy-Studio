# YOLO本地部署助手 - 项目架构文档

## 项目概述
一个跨平台的YOLO模型本地部署工具，支持多种硬件后端和模型格式，提供一键式环境部署和推理功能。

## 技术架构

### 整体架构
```
主应用 (DearPyGui + Python 3.10)
    │
    ├── 通过subprocess调用
    │
    ├── 模型推理环境1 (Python 3.8 + PyTorch 1.10 + CUDA)
    ├── 模型推理环境2 (Python 3.9 + PyTorch 2.0 + ROCm) 
    ├── 模型推理环境3 (Python 3.10 + PaddlePaddle + XPU)
    └── 模型推理环境4 (Python 3.8 + ONNX Runtime + NPU)
```

### 核心模块设计

#### 1. 环境管理模块 (Environment Manager)
- 负责检测网络环境（国内/国外）
- 下载和管理多个Python版本
- 创建和维护不同的虚拟环境
- 自动安装硬件对应的深度学习框架

#### 2. 硬件检测模块 (Hardware Detector)
- 识别NVIDIA GPU (CUDA)
- 识别AMD GPU (ROCm) 
- 识别Intel GPU (XPU)
- 识别华为NPU (Ascend)
- 识别摩尔线程卡 (MUSA)

#### 3. 模型推理控制器 (Model Invoker)
- 使用subprocess调用不同Python环境的模型
- 处理进程间通信和数据传输
- 管理推理服务的生命周期

#### 4. 用户界面 (DearPyGui)
- 资源监控仪表盘
- 模型选择和参数配置
- 实时视频流显示
- 结果可视化界面

## 环境配置策略

### Python版本管理
```
resources/
└── python/
    ├── python-3.8.10-embed-amd64/ (国内镜像下载)
    ├── python-3.9.13-embed-amd64/
    ├── python-3.10.8-embed-amd64/
    └── downloads/
        ├── python-3.8.10-embed-amd64.zip
        ├── python-3.9.13-embed-amd64.zip
        └── python-3.10.8-embed-amd64.zip
```

### 虚拟环境配置
```
environments/
├── yolov5-cuda/ (Python 3.8 + PyTorch 1.10 + CUDA 11.3)
├── yolov8-rocm/ (Python 3.9 + PyTorch 2.0 + ROCm 5.6)
├── ppyolo-xpu/ (Python 3.10 + PaddlePaddle 2.4 + XPU)
└── onnx-npu/ (Python 3.8 + ONNX Runtime + CANN)
```

## 实现方案

### 1. 环境自动部署
```python
# 首次运行时的环境部署流程
def setup_environments():
    # 1. 检测网络环境
    if is_china_network():
        mirror = "https://mirrors.aliyun.com/pypi/simple/"
    else:
        mirror = "https://pypi.org/simple/"
    
    # 2. 下载所需Python版本
    for version in ["3.8", "3.9", "3.10"]:
        if not check_python_exists(version):
            download_python(version, mirror)
    
    # 3. 创建模型专用环境
    create_environment("yolov5-cuda", 
                      python_version="3.8",
                      requirements=["torch==1.10.0", "torchvision==0.11.0"])
    
    create_environment("yolov8-rocm",
                      python_version="3.9", 
                      requirements=["torch==2.0.0", "ultralytics"])
```

### 2. 模型调用接口
```python
class ModelInvoker:
    def __init__(self):
        self.env_configs = {
            "yolov5": {
                "python_path": "environments/yolov5-cuda/python.exe",
                "script": "models/yolov5_detect.py",
                "args": ["--conf", "0.5", "--iou", "0.45"]
            },
            "yolov8": {
                "python_path": "environments/yolov8-rocm/python.exe", 
                "script": "models/yolov8_detect.py",
                "args": ["--conf", "0.5", "--iou", "0.45"]
            }
        }
    
    def invoke_model(self, model_name, image_path):
        config = self.env_configs[model_name]
        cmd = [
            config["python_path"],
            config["script"], 
            image_path
        ] + config["args"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return parse_result(result.stdout)
```

### 3. 备用方案（如果subprocess出现问题）
```python
# 方案B: HTTP微服务调用
def setup_model_services():
    # 为每个模型环境启动一个HTTP服务
    for model_env in ["yolov5-cuda", "yolov8-rocm"]:
        start_service(model_env, port=5000 + env_index)

# 方案C: 动态库调用  
def load_model_library(model_name):
    # 将模型推理封装为动态链接库
    lib_path = f"environments/{model_name}/model_inference.dll"
    return ctypes.CDLL(lib_path)
```

## 开发路线图

### 阶段一：核心框架 (1-2周)
- [ ] 环境管理模块实现
- [ ] 硬件检测功能
- [ ] 基本的subprocess调用框架
- [ ] DearPyGui主界面框架

### 阶段二：模型集成 (2-3周)
- [ ] YOLOv5环境配置和测试
- [ ] YOLOv8环境配置和测试  
- [ ] 摄像头和图片输入处理
- [ ] 结果可视化实现

### 阶段三：功能完善 (1-2周)
- [ ] 性能监控仪表盘
- [ ] 参数调节界面
- [ ] 结果保存功能
- [ ] 错误处理和日志系统

### 阶段四：测试优化 (1周)
- [ ] 多硬件兼容性测试
- [ ] 性能优化和内存管理
- [ ] 用户文档编写
- [ ] 发布准备

## 注意事项

1. **环境隔离**: 确保不同Python环境完全隔离，避免依赖冲突
2. **网络优化**: 国内用户使用阿里云镜像加速下载
3. **错误处理**: 完善的subprocess错误捕获和重试机制
4. **资源管理**: 及时清理不再使用的模型进程
5. **安全考虑**: 验证下载文件的完整性和安全性

## 备用方案
如果subprocess方案遇到问题，按顺序尝试：
1. 优化subprocess参数和通信协议
2. 切换到HTTP微服务架构
3. 使用动态库调用方式
4. 采用共享内存或管道通信

---
*文档版本: 1.0*
*最后更新: 2025-09-09*