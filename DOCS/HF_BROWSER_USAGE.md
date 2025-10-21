# HuggingFace浏览器使用指南

本文档介绍了如何在VisionDeploy Studio中使用HuggingFace浏览器功能来搜索、浏览和下载模型。

## 功能概述

HuggingFace浏览器功能包括：
1. 搜索HuggingFace上的模型
2. 获取模型元数据和文件列表
3. 从HuggingFace或国内镜像下载模型文件
4. 与内置模型管理器集成

## 核心组件

### 1. HF浏览器 (app/hf_browser.py)

提供了以下主要函数：

- `search_models(query, limit, api_base)`: 搜索模型
- `get_model_metadata(repo_id, api_base)`: 获取模型元数据
- `list_model_files(repo_id, api_base)`: 列出模型文件
- `download_from_hf(repo_id, filename, dest_dir, mirror_choice)`: 下载模型文件

### 2. 模型管理器 (app/model_manager.py)

提供了以下主要函数：

- `list_models()`: 列出内置模型
- `get_model_entry(model_id)`: 获取模型详细信息
- `download_model(model_id, mirror)`: 下载内置模型

## 使用示例

### 搜索模型

```python
from app import hf_browser

# 使用官方API搜索
results = hf_browser.search_models("yolo", limit=10)

# 使用国内镜像搜索
results = hf_browser.search_models("yolo", limit=10, api_base="https://hf-mirror.com/api")
```

### 获取模型元数据

```python
from app import hf_browser

# 获取模型元数据
metadata = hf_browser.get_model_metadata("Ultralytics/YOLOv8", api_base="https://hf-mirror.com/api")
print(metadata.get('modelId'))
print(metadata.get('pipeline_tag'))
```

### 列出模型文件

```python
from app import hf_browser

# 列出模型文件
files = hf_browser.list_model_files("Ultralytics/YOLOv8", api_base="https://hf-mirror.com/api")
for file in files:
    print(file.get('name'), file.get('size'))
```

### 下载模型文件

```python
from app import hf_browser
from pathlib import Path

# 下载模型文件
result = hf_browser.download_from_hf(
    repo_id="Ultralytics/YOLOv8",
    filename="README.md",
    dest_dir=Path("downloads"),
    mirror_choice="https://hf-mirror.com/"
)

if result:
    print(f"文件已下载到: {result}")
```

## 镜像配置

支持多种镜像源：

- 官方源: `https://huggingface.co/`
- 国内镜像: `https://hf-mirror.com/`

## 错误处理

所有函数都包含适当的错误处理，当出现网络问题或API错误时会返回空结果或None，而不会抛出异常。

## 测试

在`temp/`目录下有多个测试脚本可以验证功能：

- `test_hf_browser.py`: 测试基本的HF浏览器功能
- `test_model_download.py`: 测试模型下载功能
- `test_model_manager.py`: 测试模型管理器功能
- `test_hf_integration.py`: 测试HF浏览器与模型管理器的集成
- `final_integration_test.py`: 最终集成测试

运行测试:
```bash
python temp/final_integration_test.py
```