"""
文件验证模块 - VisionDeploy Studio
负责验证项目文件和语言包的完整性
"""

import os
import json
from typing import Dict, Tuple

class FileValidator:
    """验证项目文件和语言包的完整性"""
    
    def __init__(self, base_dir: str):
        """初始化文件验证器
        
        Args:
            base_dir: 项目根目录
        """
        self.base_dir = base_dir
        self.required_dirs = [
            "resources",
            "resources/languages",
            "resources/models",
            "resources/fonts",
            "environments"
        ]
        
        self.required_files = {
            "resources/languages/zh_CN.json": self._validate_language_file,
            "resources/languages/en_US.json": self._validate_language_file
        }
        
        # 可选文件
        self.optional_files = {
            "resources/fonts/NotoSansCJKsc-Regular.otf": self._validate_font_file
        }
    
    def validate_project_structure(self) -> Tuple[bool, str]:
        """验证项目目录结构
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            # 检查必需目录
            for rel_path in self.required_dirs:
                abs_path = os.path.join(self.base_dir, rel_path)
                if not os.path.isdir(abs_path):
                    os.makedirs(abs_path, exist_ok=True)
            
            # 检查必需文件
            for rel_path, validator in self.required_files.items():
                abs_path = os.path.join(self.base_dir, rel_path)
                if not os.path.isfile(abs_path):
                    return False, f"缺少必需文件: {rel_path}"
                
                is_valid, msg = validator(abs_path)
                if not is_valid:
                    return False, msg
            
            # 检查可选文件
            messages = []
            for rel_path, validator in self.optional_files.items():
                abs_path = os.path.join(self.base_dir, rel_path)
                if os.path.isfile(abs_path):
                    is_valid, msg = validator(abs_path)
                    if not is_valid:
                        messages.append(msg)
            
            if messages:
                return True, "项目结构验证通过 (有警告: " + "; ".join(messages) + ")"
            
            return True, "项目结构验证通过"
        
        except Exception as e:
            return False, f"验证项目结构时出错: {str(e)}"
    
    def _validate_language_file(self, file_path: str) -> Tuple[bool, str]:
        """验证语言文件
        
        Args:
            file_path: 语言文件路径
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False, f"无效的语言文件格式: {file_path}"
            
            # 检查必需键
            required_keys = {"app_title", "menu_file", "menu_edit", "menu_view", "menu_help"}
            missing_keys = required_keys - set(data.keys())
            if missing_keys:
                return False, f"语言文件缺少必需键: {missing_keys}"
            
            return True, ""
        
        except json.JSONDecodeError:
            return False, f"无效的JSON格式: {file_path}"
        except Exception as e:
            return False, f"验证语言文件时出错: {str(e)}"
    
    def _validate_font_file(self, file_path: str) -> Tuple[bool, str]:
        """验证字体文件
        
        Args:
            file_path: 字体文件路径
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not os.path.isfile(file_path):
            # 字体文件不是必需的，只是警告
            return True, f"警告: 字体文件不存在: {file_path} (将使用系统默认字体)"
        
        return True, ""
    
    def validate_language_package(self, file_path: str) -> Tuple[bool, str]:
        """验证自定义语言包
        
        Args:
            file_path: 语言包文件路径
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        return self._validate_language_file(file_path)