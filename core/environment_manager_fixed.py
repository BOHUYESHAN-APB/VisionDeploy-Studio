"""
环境管理模块 - VisionDeploy Studio
用于创建、管理和切换不同的Python虚拟环境，支持多种深度学习框架
"""

import os
import sys
import platform
import subprocess
import logging
import json
import shutil
import tempfile
import urllib.request
import zipfile
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EnvironmentManager")

class EnvironmentManager:
    """环境管理类，用于创建和管理Python虚拟环境"""
    
    def __init__(self, base_dir: str = None):
        """
        初始化环境管理器
        
        Args:
            base_dir: 环境管理器的基础目录，默认为当前工作目录
        """
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.env_dir = os.path.join(self.base_dir, "environments")
        self.python_dir = os.path.join(self.base_dir, "resources", "python")
        self.config_path = os.path.join(self.base_dir, "config.yaml")
        
        # 确保目录存在
        os.makedirs(self.env_dir, exist_ok=True)
        os.makedirs(self.python_dir, exist_ok=True)
        
        # 加载配置
        self.config = self._load_config()
        
        # 检测网络环境
        self.is_china = self._is_in_china()
        logger.info(f"网络环境检测: {'中国大陆' if self.is_china else '国际'}")
        
        # 设置镜像源
        self.pip_index_url = self.config['mirrors']['pip_china'] if self.is_china else self.config['mirrors']['pip_global']
        self.python_download_url = self.config['mirrors']['python_china'] if self.is_china else self.config['mirrors']['python_global']
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            import yaml
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # 默认配置
                default_config = {
                    'mirrors': {
                        'pip_global': 'https://pypi.org/simple',
                        'pip_china': 'https://mirrors.aliyun.com/pypi/simple/',
                        'python_global': 'https://www.python.org/ftp/python/',
                        'python_china': 'https://registry.npmmirror.com/-/binary/python/'
                    },
                    'environments': {
                        'yolov5-cuda': {
                            'python_version': '3.8.10',
                            'packages': [
                                'torch==1.10.0+cu113',
                                'torchvision==0.11.1+cu113',
                                'torchaudio==0.10.0+cu113',
                                '-r https://raw.githubusercontent.com/ultralytics/yolov5/master/requirements.txt'
                            ],
                            'extra_index_url': 'https://download.pytorch.org/whl/cu113'
                        },
                        'yolov8-cuda': {
                            'python_version': '3.9.7',
                            'packages': [
                                'torch==2.0.0+cu118',
                                'torchvision==0.15.1+cu118',
                                'torchaudio==2.0.1+cu118',
                                'ultralytics==8.0.120'
                            ],
                            'extra_index_url': 'https://download.pytorch.org/whl/cu118'
                        },
                        'ppyolo-xpu': {
                            'python_version': '3.10.0',
                            'packages': [
                                'paddlepaddle==2.4.2',
                                'paddledet'
                            ]
                        }
                    },
                    'network': {
                        'timeout': 30,
                        'retries': 3
                    }
                }
                
                # 保存默认配置
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
                
                return default_config
        except ImportError:
            logger.warning("PyYAML未安装，使用内置默认配置")
            return {
                'mirrors': {
                    'pip_global': 'https://pypi.org/simple',
                    'pip_china': 'https://mirrors.aliyun.com/pypi/simple/',
                    'python_global': 'https://www.python.org/ftp/python/',
                    'python_china': 'https://registry.npmmirror.com/-/binary/python/'
                },
                'environments': {
                    'yolov5-cuda': {
                        'python_version': '3.8.10',
                        'packages': [
                            'torch==1.10.0+cu113',
                            'torchvision==0.11.1+cu113',
                            'torchaudio==0.10.0+cu113',
                            '-r https://raw.githubusercontent.com/ultralytics/yolov5/master/requirements.txt'
                        ],
                        'extra_index_url': 'https://download.pytorch.org/whl/cu113'
                    }
                },
                'network': {
                    'timeout': 30,
                    'retries': 3
                }
            }
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {
                'mirrors': {
                    'pip_global': 'https://pypi.org/simple',
                    'pip_china': 'https://mirrors.aliyun.com/pypi/simple/',
                    'python_global': 'https://www.python.org/ftp/python/',
                    'python_china': 'https://registry.npmmirror.com/-/binary/python/'
                },
                'environments': {},
                'network': {
                    'timeout': 30,
                    'retries': 3
                }
            }
    
    def _is_in_china(self) -> bool:
        """检测是否在中国大陆网络环境"""
        try:
            # 尝试访问Google
            urllib.request.urlopen("https://www.google.com", timeout=3)
            return False
        except:
            try:
                # 尝试访问百度
                urllib.request.urlopen("https://www.baidu.com", timeout=3)
                return True
            except:
                # 默认使用国际源
                return False
    
    def _get_python_executable(self, version: str) -> str:
        """
        获取指定版本的Python可执行文件路径
        
        Args:
            version: Python版本，如"3.8.10"
            
        Returns:
            Python可执行文件的路径
        """
        major_minor = '.'.join(version.split('.')[:2])  # 例如"3.8.10" -> "3.8"
        
        if platform.system() == 'Windows':
            python_path = os.path.join(self.python_dir, f"python{major_minor}", "python.exe")
        else:
            python_path = os.path.join(self.python_dir, f"python{major_minor}", "bin", "python")
        
        if os.path.exists(python_path):
            return python_path
        else:
            logger.warning(f"Python {version} 未安装，尝试下载...")
            self._download_python(version)
            if os.path.exists(python_path):
                return python_path
            else:
                raise FileNotFoundError(f"无法找到或下载Python {version}")
    
    def _download_python(self, version: str) -> None:
        """
        下载并安装指定版本的Python
        
        Args:
            version: Python版本，如"3.8.10"
        """
        major_minor = '.'.join(version.split('.')[:2])  # 例如"3.8.10" -> "3.8"
        
        # 创建目标目录
        target_dir = os.path.join(self.python_dir, f"python{major_minor}")
        os.makedirs(target_dir, exist_ok=True)
        
        # 下载Python
        if platform.system() == 'Windows':
            # Windows使用嵌入式Python
            url = f"{self.python_download_url}{version}/python-{version}-embed-amd64.zip"
            download_path = os.path.join(tempfile.gettempdir(), f"python-{version}-embed-amd64.zip")
            
            logger.info(f"下载Python {version} 从 {url}")
            self._download_file(url, download_path)
            
            # 解压Python
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            # 修改pth文件以支持pip
            pth_file = os.path.join(target_dir, f"python{major_minor.replace('.', '')}._pth")
            if os.path.exists(pth_file):
                with open(pth_file, 'r') as f:
                    content = f.read()
                
                if "#import site" in content:
                    content = content.replace("#import site", "import site")
                    
                    with open(pth_file, 'w') as f:
                        f.write(content)
            
            # 下载并安装pip
            get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
            get_pip_path = os.path.join(tempfile.gettempdir(), "get-pip.py")
            
            logger.info("下载pip安装脚本")
            self._download_file(get_pip_url, get_pip_path)
            
            # 安装pip
            logger.info("安装pip")
            subprocess.run([os.path.join(target_dir, "python.exe"), get_pip_path], check=True)
        else:
            # Linux/macOS使用编译版本
            if platform.system() == 'Darwin':
                # macOS
                url = f"{self.python_download_url}{version}/python-{version}-macos11.pkg"
                download_path = os.path.join(tempfile.gettempdir(), f"python-{version}-macos11.pkg")
                
                logger.info(f"下载Python {version} 从 {url}")
                self._download_file(url, download_path)
                
                # 安装Python
                logger.info(f"安装Python {version}")
                subprocess.run(["installer", "-pkg", download_path, "-target", target_dir], check=True)
            else:
                # Linux
                url = f"{self.python_download_url}{version}/Python-{version}.tgz"
                download_path = os.path.join(tempfile.gettempdir(), f"Python-{version}.tgz")
                
                logger.info(f"下载Python {version} 从 {url}")
                self._download_file(url, download_path)
                
                # 解压Python
                extract_dir = os.path.join(tempfile.gettempdir(), f"Python-{version}")
                os.makedirs(extract_dir, exist_ok=True)
                
                subprocess.run(["tar", "-xzf", download_path, "-C", tempfile.gettempdir()], check=True)
                
                # 编译安装Python
                logger.info(f"编译安装Python {version}")
                subprocess.run([
                    "cd", extract_dir, "&&",
                    "./configure", f"--prefix={target_dir}", "--enable-optimizations", "&&",
                    "make", "-j", str(os.cpu_count()), "&&",
                    "make", "install"
                ], shell=True, check=True)
    
    def _download_file(self, url: str, path: str) -> None:
        """
        下载文件
        
        Args:
            url: 文件URL
            path: 保存路径
        """
        timeout = self.config['network']['timeout']
        retries = self.config['network']['retries']
        
        for i in range(retries):
            try:
                with urllib.request.urlopen(url, timeout=timeout) as response, open(path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                return
            except Exception as e:
                logger.warning(f"下载失败 ({i+1}/{retries}): {e}")
                if i == retries - 1:
                    raise
                time.sleep(2)
    
    def create_environment(self, env_name: str) -> str:
        """
        创建虚拟环境
        
        Args:
            env_name: 环境名称，必须在配置文件中定义
            
        Returns:
            虚拟环境的路径
        """
        if env_name not in self.config['environments']:
            raise ValueError(f"未知的环境: {env_name}")
        
        env_config = self.config['environments'][env_name]
        python_version = env_config['python_version']
        packages = env_config.get('packages', [])
        extra_index_url = env_config.get('extra_index_url', '')
        
        # 获取Python可执行文件
        python_exe = self._get_python_executable(python_version)
        
        # 创建虚拟环境目录
        env_path = os.path.join(self.env_dir, env_name)
        os.makedirs(env_path, exist_ok=True)
        
        # 创建虚拟环境
        logger.info(f"创建虚拟环境: {env_name}")
        
        try:
            # 尝试使用venv模块
            subprocess.run([
                python_exe, "-m", "venv", env_path
            ], check=True)
        except subprocess.CalledProcessError:
            # 如果venv失败，尝试使用virtualenv
            logger.info("venv失败，尝试使用virtualenv")
            subprocess.run([
                python_exe, "-m", "pip", "install", "virtualenv",
                "--index-url", self.pip_index_url
            ], check=True)
            
            subprocess.run([
                python_exe, "-m", "virtualenv", env_path
            ], check=True)
        
        # 获取虚拟环境中的pip
        if platform.system() == 'Windows':
            pip_exe = os.path.join(env_path, "Scripts", "pip.exe")
        else:
            pip_exe = os.path.join(env_path, "bin", "pip")
        
        # 升级pip
        logger.info("升级pip")
        subprocess.run([
            pip_exe, "install", "--upgrade", "pip",
            "--index-url", self.pip_index_url
        ], check=True)
        
        # 安装包
        if packages:
            logger.info(f"安装依赖包: {', '.join(packages)}")
            
            pip_cmd = [pip_exe, "install"]
            pip_cmd.extend(packages)
            pip_cmd.extend(["--index-url", self.pip_index_url])
            
            if extra_index_url:
                pip_cmd.extend(["--extra-index-url", extra_index_url])
            
            subprocess.run(pip_cmd, check=True)
        
        logger.info(f"环境 {env_name} 创建成功")
        return env_path
    
    def get_environment_path(self, env_name: str) -> str:
        """
        获取虚拟环境路径
        
        Args:
            env_name: 环境名称
            
        Returns:
            虚拟环境的路径
        """
        env_path = os.path.join(self.env_dir, env_name)
        if os.path.exists(env_path):
            return env_path
        else:
            return self.create_environment(env_name)
    
    def get_python_path(self, env_name: str) -> str:
        """
        获取虚拟环境中的Python可执行文件路径
        
        Args:
            env_name: 环境名称
            
        Returns:
            Python可执行文件的路径
        """
        env_path = self.get_environment_path(env_name)
        
        if platform.system() == 'Windows':
            return os.path.join(env_path, "Scripts", "python.exe")
        else:
            return os.path.join(env_path, "bin", "python")
    
    def run_in_environment(self, env_name: str, script_path: str, args: List[str] = None) -> subprocess.CompletedProcess:
        """
        在指定环境中运行脚本
        
        Args:
            env_name: 环境名称
            script_path: 脚本路径
            args: 脚本参数
            
        Returns:
            子进程的完成对象
        """
        python_path = self.get_python_path(env_name)
        cmd = [python_path, script_path]
        
        if args:
            cmd.extend(args)
        
        logger.info(f"在环境 {env_name} 中运行: {' '.join(cmd)}")
        return subprocess.run(cmd, check=True)
    
    def list_environments(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的环境
        
        Returns:
            环境列表，每个环境包含名称、状态和配置信息
        """
        environments = []
        
        for env_name, env_config in self.config['environments'].items():
            env_path = os.path.join(self.env_dir, env_name)
            
            # 检查环境是否已创建
            is_created = os.path.exists(env_path)
            
            # 获取Python版本
            python_version = env_config['python_version']
            
            # 获取包列表
            packages = env_config.get('packages', [])
            
            environments.append({
                'name': env_name,
                'created': is_created,
                'python_version': python_version,
                'packages': packages,
                'path': env_path if is_created else None
            })
        
        return environments
    
    def get_environment_info(self, env_name: str) -> Dict[str, Any]:
        """
        获取环境详细信息
        
        Args:
            env_name: 环境名称
            
        Returns:
            环境信息字典
        """
        if env_name not in self.config['environments']:
            raise ValueError(f"未知的环境: {env_name}")
        
        env_config = self.config['environments'][env_name]
        env_path = os.path.join(self.env_dir, env_name)
        is_created = os.path.exists(env_path)
        
        info = {
            'name': env_name,
            'created': is_created,
            'python_version': env_config['python_version'],
            'packages': env_config.get('packages', []),
            'path': env_path if is_created else None
        }
        
        # 如果环境已创建，获取已安装的包
        if is_created:
            python_path = self.get_python_path(env_name)
            try:
                result = subprocess.run(
                    [python_path, "-m", "pip", "list", "--format=json"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                
                installed_packages = json.loads(result.stdout)
                info['installed_packages'] = installed_packages
            except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                logger.warning(f"获取已安装包列表失败: {e}")
                info['installed_packages'] = []
        
        return info
    
    def remove_environment(self, env_name: str) -> bool:
        """
        删除虚拟环境
        
        Args:
            env_name: 环境名称
            
        Returns:
            是否成功删除
        """
        env_path = os.path.join(self.env_dir, env_name)
        
        if os.path.exists(env_path):
            logger.info(f"删除环境: {env_name}")
            try:
                shutil.rmtree(env_path)
                return True
            except Exception as e:
                logger.error(f"删除环境失败: {e}")
                return False
        else:
            logger.warning(f"环境不存在: {env_name}")
            return False
    
    def add_environment_config(self, env_name: str, python_version: str, packages: List[str], extra_index_url: str = None) -> None:
        """
        添加新的环境配置
        
        Args:
            env_name: 环境名称
            python_version: Python版本
            packages: 依赖包列表
            extra_index_url: 额外的包索引URL
        """
        if env_name in self.config['environments']:
            raise ValueError(f"环境已存在: {env_name}")
        
        self.config['environments'][env_name] = {
            'python_version': python_version,
            'packages': packages
        }
        
        if extra_index_url:
            self.config['environments'][env_name]['extra_index_url'] = extra_index_url
        
        # 保存配置
        self._save_config()
        
        logger.info(f"添加环境配置: {env_name}")
    
    def update_environment_config(self, env_name: str, python_version: str = None, packages: List[str] = None, extra_index_url: str = None) -> None:
        """
        更新环境配置
        
        Args:
            env_name: 环境名称
            python_version: Python版本
            packages: 依赖包列表
            extra_index_url: 额外的包索引URL
        """
        if env_name not in self.config['environments']:
            raise ValueError(f"未知的环境: {env_name}")
        
        if python_version:
            self.config['environments'][env_name]['python_version'] = python_version
        
        if packages:
            self.config['environments'][env_name]['packages'] = packages
        
        if extra_index_url:
            self.config['environments'][env_name]['extra_index_url'] = extra_index_url
        elif extra_index_url == '':
            # 删除extra_index_url
            self.config['environments'][env_name].pop('extra_index_url', None)
        
        # 保存配置
        self._save_config()
        
        logger.info(f"更新环境配置: {env_name}")
    
    def remove_environment_config(self, env_name: str) -> None:
        """
        删除环境配置
        
        Args:
            env_name: 环境名称
        """
        if env_name not in self.config['environments']:
            raise ValueError(f"未知的环境: {env_name}")
        
        # 删除环境配置
        del self.config['environments'][env_name]
        
        # 保存配置
        self._save_config()
        
        logger.info(f"删除环境配置: {env_name}")
    
    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            import yaml
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            logger.warning("PyYAML未安装，无法保存配置")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")


def main():
    """主函数，用于测试环境管理功能"""
    manager = EnvironmentManager()
    
    print("可用环境:")
    for env in manager.list_environments():
        print(f"  {env['name']} (Python {env['python_version']}):")
        print(f"    已创建: {'是' if env['created'] else '否'}")
        print(f"    包: {', '.join(env['packages'])}")
    
    # 创建环境示例
    # env_name = "yolov5-cuda"
    # print(f"\n创建环境: {env_name}")
    # env_path = manager.create_environment(env_name)
    # print(f"环境路径: {env_path}")
    
    # 获取环境信息示例
    # env_info = manager.get_environment_info(env_name)
    # print("\n环境信息:")
    # print(f"  名称: {env_info['name']}")
    # print(f"  Python版本: {env_info['python_version']}")
    # print(f"  已创建: {'是' if env_info['created'] else '否'}")
    # if env_info['created'] and 'installed_packages' in env_info:
    #     print(f"  已安装包:")
    #     for pkg in env_info['installed_packages'][:5]:  # 只显示前5个
    #         print(f"    {pkg['name']} {pkg['version']}")
    #     if len(env_info['installed_packages']) > 5:
    #         print(f"    ... 共 {len(env_info['installed_packages'])} 个包")


if __name__ == "__main__":
    main()