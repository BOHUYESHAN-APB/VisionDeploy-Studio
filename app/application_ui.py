"""
应用程序UI模块 - VisionDeploy Studio
包含主应用程序的UI相关功能
"""

import dearpygui.dearpygui as dpg
import os
import sys
from typing import Dict, Any

class ApplicationUI:
    """管理应用程序的用户界面"""
    
    def __init__(self, app):
        """初始化UI
        
        Args:
            app: 主应用程序实例
        """
        self.app = app
        self.dpg = dpg
        self.ui_text: Dict[str, str] = {}
        
        # 不在初始化时设置UI，而是在run方法中调用
        # self.setup_ui()
    
    def reset_layout(self):
        """重置布局"""
        # 这里可以添加重置布局的逻辑
        pass
    
    def setup_ui(self):
        """设置应用程序UI"""
        
        # 确保先销毁现有上下文（如果存在）
        try:
            if dpg.is_dearpygui_running():
                dpg.destroy_context()
        except:
            pass
        
        # 创建新上下文
        dpg.create_context()
        
        # 加载中文字体支持
        self._load_chinese_font()
        
        # 创建主窗口
        with dpg.window(tag="main_window", label="VisionDeploy Studio", width=1200, height=800):
            
            # 添加菜单栏
            with dpg.menu_bar():
                dpg.add_menu_item(label=self.app.get_text("menu_file", "文件"))
                dpg.add_menu_item(label=self.app.get_text("menu_edit", "编辑"))
                dpg.add_menu_item(label=self.app.get_text("menu_view", "视图"))
                
                # 语言菜单
                with dpg.menu(label=self.app.get_text("menu_language", "语言")):
                    for code, name in self.app.language_manager.get_available_languages().items():
                        dpg.add_menu_item(
                            label=name,
                            callback=lambda s, a, u: self.app.set_language(u),
                            user_data=code
                        )
                
                dpg.add_menu_item(label=self.app.get_text("menu_help", "帮助"), 
                                 callback=self.app.show_about)
            
            # 添加主标签页
            with dpg.tab_bar(tag="main_tabs"):
                    # 模型标签页
                    with dpg.tab(label=self.app.get_text("tab_models", "模型"), tag="models_tab"):
                        dpg.add_text("模型管理功能开发中...")
                    
                    # 推理标签页
                    with dpg.tab(label=self.app.get_text("tab_inference", "推理"), tag="inference_tab"):
                        dpg.add_text("实时推理功能开发中...")
                    
                    # 环境标签页
                    with dpg.tab(label=self.app.get_text("tab_environments", "环境"), tag="environments_tab"):
                        dpg.add_text("环境管理功能开发中...")
                    
                    # 设置标签页
                    with dpg.tab(label=self.app.get_text("tab_settings", "设置"), tag="settings_tab"):
                        self._setup_settings_tab()
        
        # 设置主窗口
        dpg.set_primary_window("main_window", True)
        
        # 创建视图端口
        dpg.create_viewport(title='VisionDeploy Studio', width=1200, height=800)
        dpg.setup_dearpygui()
    
    def is_dearpygui_running(self):
        """检查DearPyGui是否正在运行"""
        return dpg.is_dearpygui_running()
    
    def render_dearpygui_frame(self):
        """渲染DearPyGui帧"""
        dpg.render_dearpygui_frame()
    
    def _load_chinese_font(self):
        """加载中文字体以支持中文显示"""
        try:
            # 定义字体文件优先级列表
            font_files = [
                "MiSans-Regular.otf",
                "MiSans-Normal.otf",
                "MiSans-Medium.otf",
                "MiSans-Semibold.otf",
                "MiSans-Bold.otf",
                "MiSans-Demibold.otf",
                "MiSans-Light.otf",
                "MiSans-ExtraLight.otf",
                "MiSans-Thin.otf",
                "MiSans-Heavy.otf",
                "NotoSansCJKsc-Regular.otf"
            ]
            
            # 查找可用的字体文件
            font_path = None
            for font_file in font_files:
                path = os.path.join(self.app.base_dir, "resources", "fonts", font_file)
                if os.path.exists(path):
                    font_path = path
                    break
            
            # 如果找到字体文件，则加载
            if font_path:
                # 加载字体
                with dpg.font_registry():
                    default_font = dpg.add_font(font_path, 18)
                    dpg.bind_font(default_font)
                self.app.logger.info(f"成功加载中文字体: {font_path}")
                return True
            else:
                self.app.logger.warning("未找到可用的中文字体文件，将使用系统默认字体")
                return False
        except Exception as e:
            self.app.logger.warning(f"加载中文字体失败: {e}，将使用系统默认字体")
            return False
    
    def _setup_models_tab(self):
        """设置模型标签页UI"""
        # 模型列表和操作按钮的实现
        pass
    
    def _setup_inference_tab(self):
        """设置推理标签页UI"""
        # 推理界面和控件的实现
        pass
    
    def _setup_environments_tab(self):
        """设置环境标签页UI"""
        # 环境管理界面的实现
        pass
    
    def _setup_settings_tab(self):
        """设置设置标签页UI"""
        # 硬件信息面板
        with dpg.collapsing_header(label=self.app.get_text("hardware_info", "硬件信息"), default_open=True):
            # 系统信息
            with dpg.group(horizontal=True):
                dpg.add_text(self.app.get_text("system_os", "操作系统") + ":")
                self.system_os_text = dpg.add_text("", tag="system_os_value")
            
            # CPU信息
            with dpg.collapsing_header(label=self.app.get_text("cpu_info", "CPU信息")):
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("cpu_brand", "品牌") + ":")
                    self.cpu_brand_text = dpg.add_text("", tag="cpu_brand_value")
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("cpu_cores", "核心数") + ":")
                    self.cpu_cores_text = dpg.add_text("", tag="cpu_cores_value")
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("cpu_name", "型号") + ":")
                    self.cpu_name_text = dpg.add_text("", tag="cpu_name_value")
            
            # GPU信息
            with dpg.collapsing_header(label=self.app.get_text("gpu_info", "GPU信息")):
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("gpu_brand", "品牌") + ":")
                    self.gpu_brand_text = dpg.add_text("", tag="gpu_brand_value")
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("gpu_type", "类型") + ":")
                    self.gpu_type_text = dpg.add_text("", tag="gpu_type_value")
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("gpu_name", "型号") + ":")
                    self.gpu_name_text = dpg.add_text("", tag="gpu_name_value")
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("gpu_memory", "显存") + ":")
                    self.gpu_memory_text = dpg.add_text("", tag="gpu_memory_value")
            
            # 性能监控
            with dpg.collapsing_header(label=self.app.get_text("performance_monitor", "性能监控")):
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("cpu_usage", "CPU使用率") + ":")
                    self.cpu_usage_text = dpg.add_text("0%", tag="cpu_usage_value")
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("memory_usage", "内存使用率") + ":")
                    self.memory_usage_text = dpg.add_text("0%", tag="memory_usage_value")
                with dpg.group(horizontal=True):
                    dpg.add_text(self.app.get_text("gpu_usage", "GPU使用率") + ":")
                    self.gpu_usage_text = dpg.add_text("0%", tag="gpu_usage_value")
        
        # 语言设置
        with dpg.collapsing_header(label=self.app.get_text("language_settings", "语言设置")):
            dpg.add_text(self.app.get_text("select_language", "选择语言") + ":")
            with dpg.group(horizontal=True):
                for code, name in self.app.language_manager.get_available_languages().items():
                    dpg.add_button(
                        label=name,
                        callback=lambda s, a, u: self.app.set_language(u),
                        user_data=code
                    )
    
    def update_ui_text(self):
        """更新UI文本以匹配当前语言"""
        # 安全地更新UI元素，只在元素存在时更新
        ui_elements = [
            "menu_file", "menu_edit", "menu_view", "menu_help", "menu_language",
            "models_tab", "inference_tab", "environments_tab", "settings_tab"
        ]
        
        for element in ui_elements:
            if dpg.does_item_exist(element):
                try:
                    # 为不同的UI元素提供默认文本
                    default_texts = {
                        "menu_file": "文件",
                        "menu_edit": "编辑",
                        "menu_view": "视图",
                        "menu_help": "帮助",
                        "menu_language": "语言",
                        "models_tab": "模型",
                        "inference_tab": "推理",
                        "environments_tab": "环境",
                        "settings_tab": "设置"
                    }
                    default_text = default_texts.get(element.replace("_tab", ""), element)
                    dpg.set_item_label(element, self.app.get_text(element.replace("_tab", ""), default_text))
                except:
                    pass
        
        # 更新硬件信息显示
        self.update_hardware_info()
    
    def update_hardware_info(self):
        """更新硬件信息显示"""
        if not hasattr(self, 'system_os_text'):
            return
            
        # 获取硬件信息
        hardware_info = self.app.core.hardware_detector.get_device_summary()
        
        # 更新系统信息
        dpg.set_value("system_os_value", hardware_info.get('os', 'Unknown'))
        
        # 更新CPU信息
        cpu_info = hardware_info.get('cpu', {})
        dpg.set_value("cpu_brand_value", cpu_info.get('brand', 'Unknown'))
        dpg.set_value("cpu_cores_value", str(cpu_info.get('cores', 'Unknown')))
        dpg.set_value("cpu_name_value", cpu_info.get('name', 'Unknown'))
        
        # 更新GPU信息
        gpu_list = hardware_info.get('gpu', [])
        if gpu_list:
            gpu_info = gpu_list[0]
            dpg.set_value("gpu_brand_value", gpu_info.get('brand', 'Unknown'))
            dpg.set_value("gpu_type_value", gpu_info.get('type', 'Unknown'))
            dpg.set_value("gpu_name_value", gpu_info.get('name', 'Unknown'))
            dpg.set_value("gpu_memory_value", gpu_info.get('memory', 'Unknown'))
        else:
            dpg.set_value("gpu_brand_value", "None")
            dpg.set_value("gpu_type_value", "None")
            dpg.set_value("gpu_name_value", "None")
            dpg.set_value("gpu_memory_value", "None")
    
    def update_performance_data(self, performance_data):
        """更新性能监控数据
        
        Args:
            performance_data: 性能数据字典
        """
        if not hasattr(self, 'cpu_usage_text'):
            return
            
        # 更新CPU使用率
        cpu_usage = performance_data.get('cpu', {}).get('usage', 0)
        dpg.set_value("cpu_usage_value", f"{cpu_usage:.1f}%")
        
        # 更新内存使用率
        memory_usage = performance_data.get('memory', {}).get('usage', 0)
        dpg.set_value("memory_usage_value", f"{memory_usage:.1f}%")
        
        # 更新GPU使用率
        gpu_usage = performance_data.get('gpu', {}).get('usage', 0)
        dpg.set_value("gpu_usage_value", f"{gpu_usage:.1f}%")