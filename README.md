# VisionDeploy Studio - YOLO本地部署助手

> 文档已集中到 `DOCS/` 目录，首选阅读 `DOCS/INDEX.md` 以获取项目概览与规范。


一个专为计算机视觉模型设计的本地部署工具，支持多种硬件加速和模型格式。

## 功能特性

### 🚀 核心功能
- **多硬件支持**: Intel XPU, NVIDIA CUDA, AMD ROCM
- **模型管理**: YOLO系列模型下载、管理和部署
- **实时推理**: 摄像头实时检测和图片批量处理
- **性能监控**: CPU/GPU/内存使用率实时显示
- **按需环境**: 仅在需要时安装模型环境，节省存储空间

### 🌍 多语言支持
- 简体中文 (zh_CN)
- 英文 (en_US)
- 自动检测系统语言环境

### 🛠️ 技术特性
- 自动硬件检测和配置优化
- 按需Python虚拟环境管理
- 网络环境自适应（国内/国外镜像）
- 跨平台支持 (Windows/Linux/macOS)

## 快速开始

### Windows用户
1. 双击 `run.bat` 启动程序
2. 或右键选择 `run.ps1` 使用PowerShell运行

### Linux/macOS用户
```bash
chmod +x run.sh
./run.sh
```

### 命令行启动
```bash
# 使用中文界面
python app/main.py --language zh_CN

# 使用英文界面  
python app/main.py --language en_US

# 自动检测语言
python app/main.py
```

## 硬件要求

### 最低配置
- CPU: 支持AVX指令集的x86_64处理器
- 内存: 4GB RAM
- 存储: 2GB可用空间
- 系统: Windows 10/11, Ubuntu 18.04+, macOS 10.15+

### 推荐配置
- CPU: 8核以上处理器
- 内存: 16GB RAM
- GPU: NVIDIA GTX 1060 6GB+ / AMD RX 580 8GB+
- 存储: 10GB SSD空间

## 支持模型

### YOLO系列
- YOLOv5, YOLOv6, YOLOv7, YOLOv8
- PP-YOLO, YOLOX
- 自定义训练的YOLO模型

### 模型格式
- PyTorch (.pt)
- ONNX (.onnx) 
- TensorRT (.engine)
- OpenVINO (.xml)

## 按需环境管理

### 工作原理
VisionDeploy Studio采用按需环境管理策略：
1. **初始安装**: 仅安装基础依赖，不预装大型深度学习框架
2. **环境准备**: 当用户选择特定模型环境时，动态创建虚拟环境并安装所需依赖
3. **资源优化**: 避免预装多个大型框架，节省磁盘空间和安装时间

### 可用环境
- **yolov5-cuda**: YOLOv5 + CUDA支持 (NVIDIA GPU)
- **yolov8-cuda**: YOLOv8 + CUDA支持 (NVIDIA GPU)
- **ppyolo-xpu**: PP-YOLO + Intel XPU支持 (Intel处理器)

### 环境准备流程
1. 在GUI中选择目标模型环境
2. 点击"准备选中环境"按钮
3. 系统自动下载Python、创建虚拟环境、安装依赖
4. 环境准备完成后即可进行模型推理

## 目录结构

```
VisionDeploy-Studio/
├── app/                 # 应用程序核心
│   ├── main.py         # 主入口文件
│   └── gui_application.py # GUI界面
├── core/               # 核心模块
│   ├── hardware_detector.py         # 硬件检测
│   ├── on_demand_environment_manager.py  # 按需环境管理
│   ├── model_manager.py             # 模型管理
│   └── language_manager.py          # 语言管理
├── resources/          # 资源文件
│   ├── languages/     # 语言包
│   └── fonts/         # 字体文件
├── config/            # 配置文件
├── run.bat           # Windows启动脚本
├── run.ps1           # PowerShell启动脚本
└── run.sh            # Linux/macOS启动脚本
```

## 常见问题

### Q: 检测不到NVIDIA显卡？
A: 请安装NVIDIA驱动和CUDA工具包

### Q: 程序启动失败？
A: 检查Python版本（需要3.8+）和依赖安装

### Q: 如何添加新的语言支持？
A: 在 `resources/languages/` 目录下创建新的语言文件

### Q: 环境准备失败怎么办？
A: 检查网络连接，或手动运行 `python install_dependencies.py` 安装依赖

## 开发计划

- [ ] 华为NPU支持
- [ ] 摩尔线程MUSA SDK支持  
- [ ] 更多CNN模型支持
- [ ] 模型训练功能
- [ ] 云端同步功能

## 许可证

MIT License - 详见 LICENSE 文件

## 技术支持

如有问题请提交Issue或联系开发团队。