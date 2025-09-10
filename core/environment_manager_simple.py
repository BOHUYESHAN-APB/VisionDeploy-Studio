import os
import sys
import subprocess
import requests
import zipfile
from pathlib import Path

class EnvironmentManager:
    def __init__(self):
        self.resources_dir = Path("resources")
        self.python_versions = {
            '3.8': 'python-3.8.10-embed-amd64.zip',
            '3.9': 'python-3.9.13-embed-amd64.zip',
            '3.10': 'python-3.10.8-embed-amd64.zip'
        }
        
    def detect_network(self):
        """检测网络环境（简化版本）"""
        return 'cn'  # 默认国内网络
        
    def get_available_python_versions(self):
        """获取可用的Python版本"""
        available_versions = []
        for version, zip_file in self.python_versions.items():
            python_dir = self.resources_dir / "python" / version
            if python_dir.exists() and (python_dir / "python.exe").exists():
                available_versions.append(version)
        return available_versions
        
    def get_current_environment(self):
        """获取当前Python环境信息"""
        return {
            'version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'executable': sys.executable,
            'path': sys.path
        }
        
    def setup_environments(self):
        """设置所有需要的Python环境"""
        print("🛠️  设置模型环境...")
        
        # 只设置当前可用的环境
        success = self.setup_python('3.10')
        if success:
            print("✅ 基础环境设置完成")
        else:
            print("❌ 环境设置失败")
        
        return success
    
    def setup_python(self, version):
        """设置单个Python版本"""
        python_dir = self.resources_dir / "python" / version
        zip_filename = self.python_versions[version]
        zip_path = python_dir / zip_filename
        
        if python_dir.exists():
            print(f"✅ Python {version} 已存在")
            return True
            
        print(f"Python {version} 未安装，开始下载...")
        
        # 下载Python
        download_url = f"https://mirrors.aliyun.com/python-release/windows/{zip_filename}"
        print(f"正在下载 Python {version} from {download_url}")
        
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            python_dir.mkdir(parents=True, exist_ok=True)
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Python {version} 下载完成")
            
            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(python_dir)
            
            print(f"Python {version} 解压完成")
            
            # 删除zip文件
            zip_path.unlink()
            
            print(f"Python {version} 安装完成")
            return True
            
        except Exception as e:
            print(f"❌ Python {version} 安装失败: {e}")
            return False

# 简单测试
if __name__ == "__main__":
    manager = EnvironmentManager()
    manager.setup_environments()