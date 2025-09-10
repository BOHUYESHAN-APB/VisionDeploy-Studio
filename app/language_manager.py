"""
语言管理模块 - VisionDeploy Studio
负责管理应用程序的多语言支持
"""

import os
import json
from typing import Dict, Optional

class LanguageManager:
    """管理应用程序的多语言支持"""
    
    def __init__(self, base_dir: str):
        """初始化语言管理器
        
        Args:
            base_dir: 项目根目录
        """
        self.base_dir = base_dir
        self.languages_dir = os.path.join(base_dir, "resources", "languages")
        self.current_language = "zh_CN"  # 默认中文
        self.languages: Dict[str, Dict[str, str]] = {}
        
        # 确保语言目录存在
        os.makedirs(self.languages_dir, exist_ok=True)
        
        # 加载默认语言
        self._load_default_languages()
    
    def _load_default_languages(self):
        """加载默认语言包"""
        # 中文语言包
        zh_cn = {
            "app_title": "VisionDeploy Studio",
            "menu_file": "文件",
            "menu_edit": "编辑",
            "menu_view": "视图",
            "menu_help": "帮助",
            "menu_language": "语言",
            "tab_models": "模型",
            "tab_inference": "推理",
            "tab_environments": "环境",
            "tab_settings": "设置",
            "button_refresh": "刷新",
            "button_download": "下载",
            "button_use": "使用",
            "button_delete": "删除",
            "status_ready": "准备就绪",
            "error_network": "网络错误",
            "success_operation": "操作成功",
            "hardware_info": "硬件信息",
            "system_os": "操作系统",
            "cpu_info": "CPU信息",
            "cpu_brand": "品牌",
            "cpu_cores": "核心数",
            "cpu_name": "型号",
            "gpu_info": "GPU信息",
            "gpu_brand": "品牌",
            "gpu_type": "类型",
            "gpu_name": "型号",
            "gpu_memory": "显存",
            "performance_monitor": "性能监控",
            "cpu_usage": "CPU使用率",
            "memory_usage": "内存使用率",
            "gpu_usage": "GPU使用率",
            "language_settings": "语言设置",
            "select_language": "选择语言",
            "language_name": "中文",
            "about_dialog_title": "关于",
            "third_party_components": "使用的第三方组件:",
            "close": "关闭"
        }
        
        # 英文语言包
        en_US = {
            "app_title": "VisionDeploy Studio",
            "menu_file": "File",
            "menu_edit": "Edit",
            "menu_view": "View",
            "menu_help": "Help",
            "menu_language": "Language",
            "tab_models": "Models",
            "tab_inference": "Inference",
            "tab_environments": "Environments",
            "tab_settings": "Settings",
            "button_refresh": "Refresh",
            "button_download": "Download",
            "button_use": "Use",
            "button_delete": "Delete",
            "status_ready": "Ready",
            "error_network": "Network Error",
            "success_operation": "Operation Success",
            "hardware_info": "Hardware Info",
            "system_os": "Operating System",
            "cpu_info": "CPU Info",
            "cpu_brand": "Brand",
            "cpu_cores": "Cores",
            "cpu_name": "Model",
            "gpu_info": "GPU Info",
            "gpu_brand": "Brand",
            "gpu_type": "Type",
            "gpu_name": "Model",
            "gpu_memory": "Memory",
            "performance_monitor": "Performance Monitor",
            "cpu_usage": "CPU Usage",
            "memory_usage": "Memory Usage",
            "gpu_usage": "GPU Usage",
            "language_settings": "Language Settings",
            "select_language": "Select Language",
            "language_name": "English",
            "about_dialog_title": "About",
            "third_party_components": "Third Party Components:",
            "close": "Close"
        }
        
        # 保存默认语言包
        self.languages = {
            "zh_CN": zh_cn,
            "en_US": en_US
        }
        
        # 保存到文件
        self._save_language("zh_CN", zh_cn)
        self._save_language("en_US", en_US)
    
    def _save_language(self, lang_code: str, lang_data: Dict[str, str]):
        """保存语言包到文件
        
        Args:
            lang_code: 语言代码 (如 zh_CN, en_US)
            lang_data: 语言数据字典
        """
        file_path = os.path.join(self.languages_dir, f"{lang_code}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(lang_data, f, ensure_ascii=False, indent=4)
    
    def load_custom_language(self, lang_code: str) -> bool:
        """加载自定义语言包
        
        Args:
            lang_code: 语言代码
            
        Returns:
            bool: 是否加载成功
        """
        file_path = os.path.join(self.languages_dir, f"{lang_code}.json")
        if not os.path.exists(file_path):
            return False
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.languages[lang_code] = json.load(f)
            return True
        except Exception:
            return False
    
    def set_language(self, lang_code: str) -> bool:
        """设置当前语言
        
        Args:
            lang_code: 语言代码
            
        Returns:
            bool: 是否设置成功
        """
        if lang_code in self.languages:
            self.current_language = lang_code
            return True
        return False
    
    def get_text(self, key: str, default: Optional[str] = None) -> str:
        """获取当前语言的文本
        
        Args:
            key: 文本键
            default: 默认值
            
        Returns:
            str: 对应的文本或默认值
        """
        lang_data = self.languages.get(self.current_language, {})
        return lang_data.get(key, default or key)
    
    def get_available_languages(self) -> Dict[str, str]:
        """获取可用语言列表
        
        Returns:
            Dict[str, str]: 语言代码到语言名称的映射
        """
        # 这里可以扩展为返回更友好的语言名称
        return {
            code: self.get_text("language_name", code)
            for code in self.languages.keys()
        }