# VisionDeploy Studio — 架构设计


## 高层架构概览

VisionDeploy Studio 采用前端 UI + 后端服务（按需环境）分离的架构：

- UI 进程：负责用户交互、快速响应、模型浏览与简单管理操作。使用 PySide6 / CTk 等桌面 UI 框架。
- 管理服务（本地）：管理模型索引、环境创建、插件调度与社区缓存（SQLite 存储）。
- 推理执行器（按需）：每个模型/后端在独立进程或虚拟环境中运行，UI 通过 IPC（HTTP REST 或 Unix domain socket）调用，确保主进程稳定。


## 组件

1. UI 层
   - 负责所有用户界面、输入采集、可视化结果渲染。
   - 与管理服务通信（控制接口）与推理执行器通信（结果/监控）。

2. 管理服务
   - 模型索引（SQLite），模型文件管理（resources/models/）
   - 环境管理器（按需创建 venv/conda 环境）、下载管理、镜像选择逻辑。

3. 推理执行器（ModelInvoker）
   - 插件化后端接口，支持 PyTorch / ONNXRuntime / OpenVINO / TensorRT。
   - 提供统一的 REST 接口：/invoke, /status, /metrics, /cancel。

4. 社区服务（可选）
   - 本地缓存社区内容，支持从在线 API 拉取与用户上传。


## 通信协议

- UI <-> 管理服务：本地 HTTP REST（短连接）或本地 socket。
- UI <-> 推理执行器：HTTP REST 或 gRPC（如果需要更高性能）。
- 管理服务 <-> 远端模型源：HTTPS 调用 Hugging Face / ModelScope API，并缓存结果。


## 插件与扩展点

- 后端适配器接口：ModelInvoker 插件注册点。
- 模型源适配器：支持不同在线源（Hugging Face/ModelScope/自定义仓库）。
- UI 插件点：可扩展面板、数据导出格式、性能分析工具。
