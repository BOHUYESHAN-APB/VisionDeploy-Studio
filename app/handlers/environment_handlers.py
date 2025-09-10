"""
环境处理模块 - VisionDeploy Studio
包含环境相关的处理函数
"""

import os
import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

class EnvironmentHandlers:
    """环境处理类，包含环境相关的处理函数"""
    
    def __init__(self, app):
        """初始化环境处理
        
        Args:
            app: 主应用程序实例
        """
        self.app = app
        self.logger = app.logger
    
    def refresh_environments(self):
        """刷新环境列表"""
        environments = self.app.environment_manager.list_environments()
        
        # 更新环境列表
        if dpg.does_item_exist("environment_list"):
            dpg.delete_item("environment_list", children_only=True)
            
            with dpg.child_window(parent="environment_list"):
                for env in environments:
                    with dpg.group(horizontal=True):
                        dpg.add_text(f"{env['name']} (Python {env['python_version']})")
                        dpg.add_button(label="查看", callback=lambda s, a, u: self.select_environment(u), user_data=env)
    
    def filter_environments(self, sender=None, value=None):
        """过滤环境列表"""
        # 获取搜索文本
        search_text = dpg.get_value("environment_search_input") if dpg.does_item_exist("environment_search_input") else ""
        
        # 获取环境列表
        environments = self.app.environment_manager.list_environments()
        
        # 应用过滤
        filtered_environments = []
        for env in environments:
            # 搜索文本过滤
            if search_text and search_text.lower() not in env['name'].lower():
                continue
            
            filtered_environments.append(env)
        
        # 更新环境列表
        if dpg.does_item_exist("environment_list"):
            dpg.delete_item("environment_list", children_only=True)
            
            with dpg.child_window(parent="environment_list"):
                for env in filtered_environments:
                    with dpg.group(horizontal=True):
                        dpg.add_text(f"{env['name']} (Python {env['python_version']})")
                        dpg.add_button(label="查看", callback=lambda s, a, u: self.select_environment(u), user_data=env)
    
    def select_environment(self, environment):
        """选择环境
        
        Args:
            environment: 环境信息字典
        """
        # 显示环境详情
        if dpg.does_item_exist("environment_details_placeholder"):
            dpg.hide_item("environment_details_placeholder")
        
        if dpg.does_item_exist("environment_details_content"):
            dpg.show_item("environment_details_content")
            
            # 更新环境详情
            dpg.set_value("environment_name_text", f"名称: {environment['name']}")
            dpg.set_value("environment_python_version_text", f"Python版本: {environment['python_version']}")
            dpg.set_value("environment_status_text", f"状态: {'激活' if environment['active'] else '未激活'}")
            dpg.set_value("environment_path_text", f"路径: {environment['path']}")
            
            # 更新包列表
            if dpg.does_item_exist("package_list_window"):
                dpg.delete_item("package_list_window", children_only=True)
                
                with dpg.child_window(parent="package_list_window"):
                    for pkg in environment.get('packages', []):
                        dpg.add_text(f"{pkg['name']}=={pkg['version']}")
            
            # 更新按钮状态
            if environment['active']:
                dpg.hide_item("create_environment_button")
                dpg.show_item("delete_environment_button")
                dpg.show_item("edit_environment_button")
            else:
                dpg.show_item("create_environment_button")
                dpg.hide_item("delete_environment_button")
                dpg.hide_item("edit_environment_button")
    
    def create_selected_environment(self):
        """创建选中的环境"""
        # 获取选中的环境名称
        env_name = dpg.get_value("environment_name_text").split(": ")[1]
        
        # 创建环境
        success = self.app.environment_manager.create_environment(env_name)
        
        if success:
            # 刷新环境列表
            self.refresh_environments()
            
            # 显示创建成功提示
            with dpg.window(label="提示", modal=True, width=300, height=100, tag="environment_create_success_window"):
                dpg.add_text(f"环境 {env_name} 创建成功")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("environment_create_success_window"))
        else:
            # 显示创建失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="environment_create_error_window"):
                dpg.add_text(f"环境 {env_name} 创建失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("environment_create_error_window"))
    
    def delete_selected_environment(self):
        """删除选中的环境"""
        # 获取选中的环境名称
        env_name = dpg.get_value("environment_name_text").split(": ")[1]
        
        # 确认删除
        with dpg.window(label="确认", modal=True, width=300, height=150, tag="confirm_delete_environment_window"):
            dpg.add_text(f"确定要删除环境 {env_name} 吗？")
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="确定", callback=lambda: self._confirm_delete_environment(env_name))
                dpg.add_button(label="取消", callback=lambda: dpg.delete_item("confirm_delete_environment_window"))
    
    def _confirm_delete_environment(self, env_name):
        """确认删除环境
        
        Args:
            env_name: 环境名称
        """
        # 关闭确认对话框
        dpg.delete_item("confirm_delete_environment_window")
        
        # 删除环境
        success = self.app.environment_manager.delete_environment(env_name)
        
        if success:
            # 刷新环境列表
            self.refresh_environments()
            
            # 显示删除成功提示
            with dpg.window(label="提示", modal=True, width=300, height=100, tag="environment_delete_success_window"):
                dpg.add_text(f"环境 {env_name} 删除成功")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("environment_delete_success_window"))
        else:
            # 显示删除失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="environment_delete_error_window"):
                dpg.add_text(f"环境 {env_name} 删除失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("environment_delete_error_window"))
    
    def edit_selected_environment(self):
        """编辑选中的环境"""
        # 获取选中的环境名称
        env_name = dpg.get_value("environment_name_text").split(": ")[1]
        
        # 显示编辑对话框
        with dpg.window(label="编辑环境", modal=True, width=400, height=300, tag="edit_environment_window"):
            dpg.add_text(f"编辑环境: {env_name}")
            dpg.add_separator()
            
            # 添加编辑控件
            dpg.add_text("Python版本")
            dpg.add_input_text(default_value=dpg.get_value("environment_python_version_text").split(": ")[1], tag="edit_python_version_input")
            
            dpg.add_spacer(height=20)
            
            # 添加包管理控件
            dpg.add_text("管理包")
            dpg.add_input_text(hint="包名==版本", tag="package_input")
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="添加", callback=lambda: self._add_package_to_environment(env_name))
                dpg.add_button(label="删除", callback=lambda: self._remove_package_from_environment(env_name))
            
            dpg.add_spacer(height=20)
            
            # 操作按钮
            with dpg.group(horizontal=True):
                dpg.add_button(label="保存", callback=lambda: self._save_environment_changes(env_name))
                dpg.add_button(label="取消", callback=lambda: dpg.delete_item("edit_environment_window"))
    
    def _add_package_to_environment(self, env_name):
        """添加包到环境
        
        Args:
            env_name: 环境名称
        """
        package_spec = dpg.get_value("package_input")
        if not package_spec:
            return
        
        # 添加包
        success = self.app.environment_manager.add_package(env_name, package_spec)
        
        if success:
            # 刷新环境详情
            env = self.app.environment_manager.get_environment(env_name)
            self.select_environment(env)
            
            # 清空输入框
            dpg.set_value("package_input", "")
        else:
            # 显示添加失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="package_add_error_window"):
                dpg.add_text(f"添加包 {package_spec} 失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("package_add_error_window"))
    
    def _remove_package_from_environment(self, env_name):
        """从环境移除包
        
        Args:
            env_name: 环境名称
        """
        package_spec = dpg.get_value("package_input")
        if not package_spec:
            return
        
        # 移除包
        success = self.app.environment_manager.remove_package(env_name, package_spec)
        
        if success:
            # 刷新环境详情
            env = self.app.environment_manager.get_environment(env_name)
            self.select_environment(env)
            
            # 清空输入框
            dpg.set_value("package_input", "")
        else:
            # 显示移除失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="package_remove_error_window"):
                dpg.add_text(f"移除包 {package_spec} 失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("package_remove_error_window"))
    
    def _save_environment_changes(self, env_name):
        """保存环境更改
        
        Args:
            env_name: 环境名称
        """
        # 获取新的Python版本
        new_python_version = dpg.get_value("edit_python_version_input")
        
        # 更新环境
        success = self.app.environment_manager.update_environment(env_name, new_python_version)
        
        if success:
            # 刷新环境详情
            env = self.app.environment_manager.get_environment(env_name)
            self.select_environment(env)
            
            # 关闭编辑窗口
            dpg.delete_item("edit_environment_window")
            
            # 显示保存成功提示
            with dpg.window(label="提示", modal=True, width=300, height=100, tag="environment_save_success_window"):
                dpg.add_text(f"环境 {env_name} 更新成功")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("environment_save_success_window"))
        else:
            # 显示保存失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="environment_save_error_window"):
                dpg.add_text(f"环境 {env_name} 更新失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("environment_save_error_window"))
    
    def show_add_environment_dialog(self):
        """显示添加环境对话框"""
        with dpg.window(label="添加新环境", modal=True, width=400, height=200, tag="add_environment_window"):
            dpg.add_text("创建新环境")
            dpg.add_separator()
            
            # 环境名称
            dpg.add_text("环境名称")
            dpg.add_input_text(tag="new_environment_name_input")
            
            # Python版本
            dpg.add_text("Python版本")
            dpg.add_combo(["3.8", "3.9", "3.10"], default_value="3.9", tag="new_environment_python_version_combo")
            
            dpg.add_spacer(height=20)
            
            # 操作按钮
            with dpg.group(horizontal=True):
                dpg.add_button(label="创建", callback=self._create_new_environment)
                dpg.add_button(label="取消", callback=lambda: dpg.delete_item("add_environment_window"))
    
    def _create_new_environment(self):
        """创建新环境"""
        env_name = dpg.get_value("new_environment_name_input")
        python_version = dpg.get_value("new_environment_python_version_combo")
        
        if not env_name:
            return
        
        # 创建环境
        success = self.app.environment_manager.create_environment(env_name, python_version)
        
        if success:
            # 刷新环境列表
            self.refresh_environments()
            
            # 关闭添加窗口
            dpg.delete_item("add_environment_window")
            
            # 显示创建成功提示
            with dpg.window(label="提示", modal=True, width=300, height=100, tag="new_environment_success_window"):
                dpg.add_text(f"环境 {env_name} 创建成功")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("new_environment_success_window"))
        else:
            # 显示创建失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="new_environment_error_window"):
                dpg.add_text(f"环境 {env_name} 创建失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("new_environment_error_window"))