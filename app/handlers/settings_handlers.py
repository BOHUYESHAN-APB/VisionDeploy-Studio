"""
设置处理模块 - VisionDeploy Studio
包含设置相关的处理函数
"""

import os
import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

class SettingsHandlers:
    """设置处理类，包含设置相关的处理函数"""
    
    def __init__(self, app):
        """初始化设置处理
        
        Args:
            app: 主应用程序实例
        """
        self.app = app
        self.logger = app.logger
    
    def exit_app(self):
        """退出应用程序"""
        # 这里可以添加退出前的清理工作
        try:
            # 保存当前设置
            self.app.save_config()
            
            # 清理资源
            if hasattr(self.app, 'ui') and self.app.ui:
                try:
                    dpg.destroy_context()
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"退出应用程序时出错: {e}")
        finally:
            # 强制退出
            import sys
            sys.exit(0)
    
    def toggle_theme(self):
        """切换主题"""
        self.app.app_state['dark_mode'] = not self.app.app_state['dark_mode']
        self.app.ui.apply_theme(self.app.app_state['dark_mode'])
        
        # 更新复选框状态
        if dpg.does_item_exist("dark_mode_checkbox"):
            dpg.set_value("dark_mode_checkbox", self.app.app_state['dark_mode'])
    
    def toggle_performance_monitoring(self):
        """切换性能监控"""
        self.app.app_state['performance_monitoring'] = not self.app.app_state['performance_monitoring']
        
        if self.app.app_state['performance_monitoring']:
            self.app.performance_monitor.start_monitoring()
        else:
            self.app.performance_monitor.stop_monitoring()
        
        # 更新复选框状态
        if dpg.does_item_exist("performance_monitoring_checkbox"):
            dpg.set_value("performance_monitoring_checkbox", self.app.app_state['performance_monitoring'])
    
    def set_network_timeout(self, sender, value):
        """设置网络超时时间"""
        self.app.app_state['network_timeout'] = value
    
    def set_network_retries(self, sender, value):
        """设置网络重试次数"""
        self.app.app_state['network_retries'] = value
    
    def set_models_path(self, sender, value):
        """设置模型存储路径"""
        self.app.app_state['models_path'] = value
        self.app.model_manager.models_dir = value
    
    def browse_models_path(self):
        """浏览模型存储路径"""
        # 在实际应用中，这里应该打开一个文件夹选择对话框
        pass
    
    def set_environments_path(self, sender, value):
        """设置环境存储路径"""
        self.app.app_state['environments_path'] = value
        self.app.environment_manager.environments_dir = value
    
    def browse_environments_path(self):
        """浏览环境存储路径"""
        # 在实际应用中，这里应该打开一个文件夹选择对话框
        pass
    
    def save_settings(self):
        """保存设置"""
        self.app.save_config()
        
        # 显示保存成功提示
        with dpg.window(label="提示", modal=True, width=300, height=100, tag="settings_saved_window"):
            dpg.add_text("设置已保存")
            dpg.add_button(label="确定", callback=lambda: dpg.delete_item("settings_saved_window"))
    
    def reset_settings(self):
        """重置设置"""
        # 恢复默认设置
        self.app.app_state = {
            'dark_mode': True,
            'performance_monitoring': True,
            'network_timeout': 30,
            'network_retries': 3,
            'models_path': os.path.join(self.app.base_dir, "resources", "models"),
            'environments_path': os.path.join(self.app.base_dir, "environments")
        }
        
        # 更新UI
        if dpg.does_item_exist("dark_mode_checkbox"):
            dpg.set_value("dark_mode_checkbox", self.app.app_state['dark_mode'])
        
        if dpg.does_item_exist("performance_monitoring_checkbox"):
            dpg.set_value("performance_monitoring_checkbox", self.app.app_state['performance_monitoring'])
        
        if dpg.does_item_exist("network_timeout_input"):
            dpg.set_value("network_timeout_input", self.app.app_state['network_timeout'])
        
        if dpg.does_item_exist("network_retries_input"):
            dpg.set_value("network_retries_input", self.app.app_state['network_retries'])
        
        if dpg.does_item_exist("models_path_input"):
            dpg.set_value("models_path_input", self.app.app_state['models_path'])
        
        if dpg.does_item_exist("environments_path_input"):
            dpg.set_value("environments_path_input", self.app.app_state['environments_path'])
        
        # 应用主题
        self.app.ui.apply_theme(self.app.app_state['dark_mode'])
        
        # 显示重置成功提示
        with dpg.window(label="提示", modal=True, width=300, height=100, tag="settings_reset_window"):
            dpg.add_text("设置已重置为默认值")
            dpg.add_button(label="确定", callback=lambda: dpg.delete_item("settings_reset_window"))
    
    def show_settings(self):
        """显示设置对话框"""
        # 这里应该实现设置对话框的显示逻辑
        pass
    
    def open_docs(self):
        """打开文档"""
        # 这里应该实现打开文档的逻辑
        pass
    
    def show_about(self):
        """显示关于对话框"""
        try:
            # 读取第三方组件信息
            import json
            third_party_file = os.path.join(self.app.base_dir, "resources", "third_party_components.json")
            with open(third_party_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 创建关于对话框
            with dpg.window(label=self.app.get_text("about_dialog_title", "关于"), 
                          modal=True, 
                          width=600, 
                          height=400, 
                          tag="about_window"):
                
                # 项目信息
                dpg.add_text(f"{data['project_name']}", color=(0, 200, 255))
                dpg.add_text(data['project_description'])
                dpg.add_separator()
                
                # 第三方组件信息
                dpg.add_text(self.app.get_text("third_party_components", "使用的第三方组件:"), color=(0, 200, 0))
                
                # 创建可滚动的组件列表
                with dpg.child_window(height=250):
                    for component in data['third_party_components']:
                        with dpg.group():
                            # 组件名称和版本
                            dpg.add_text(f"{component['name']} {component['version']}", color=(255, 255, 0))
                            
                            # 链接
                            if component['url']:
                                dpg.add_text(component['url'], color=(100, 100, 255))
                            
                            # 许可证
                            dpg.add_text(f"License: {component['license']}", color=(200, 200, 200))
                            
                            # 许可证链接
                            if component['license_url']:
                                dpg.add_text(component['license_url'], color=(100, 100, 255))
                            
                            dpg.add_separator()
                
                # 关闭按钮
                dpg.add_button(label=self.app.get_text("close", "关闭"), 
                             callback=lambda: dpg.delete_item("about_window"))
        
        except Exception as e:
            self.logger.error(f"显示关于对话框时出错: {e}")
            # 显示简化版的关于对话框
            with dpg.window(label=self.app.get_text("about_dialog_title", "关于"), 
                          modal=True, 
                          width=400, 
                          height=200, 
                          tag="about_window_error"):
                dpg.add_text("VisionDeploy Studio")
                dpg.add_text("专为计算机视觉模型设计的本地部署工具")
                dpg.add_text(f"错误: {str(e)}", color=(255, 0, 0))
                dpg.add_button(label=self.app.get_text("close", "关闭"), 
                             callback=lambda: dpg.delete_item("about_window_error"))