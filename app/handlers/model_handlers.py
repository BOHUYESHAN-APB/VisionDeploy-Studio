"""
模型处理模块 - VisionDeploy Studio
包含模型相关的处理函数
"""

import os
import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

class ModelHandlers:
    """模型处理类，包含模型相关的处理函数"""
    
    def __init__(self, app):
        """初始化模型处理
        
        Args:
            app: 主应用程序实例
        """
        self.app = app
        self.logger = app.logger
    
    def refresh_models(self):
        """刷新模型列表"""
        models = self.app.model_manager.list_models()
        
        # 更新模型下拉列表
        if dpg.does_item_exist("inference_model_combo"):
            model_names = [f"{model['name']} ({model['type']})" for model in models]
            dpg.configure_item("inference_model_combo", items=model_names)
        
        # 更新模型列表
        if dpg.does_item_exist("model_list"):
            dpg.delete_item("model_list", children_only=True)
            
            with dpg.child_window(parent="model_list"):
                for model in models:
                    with dpg.group(horizontal=True):
                        dpg.add_text(f"{model['name']} ({model['type']})")
                        dpg.add_button(label="查看", callback=lambda s, a, u: self.select_model(u), user_data=model)
    
    def filter_models(self, sender=None, value=None):
        """过滤模型列表"""
        # 获取过滤条件
        category = dpg.get_value("model_category_combo") if dpg.does_item_exist("model_category_combo") else "全部"
        search_text = dpg.get_value("model_search_input") if dpg.does_item_exist("model_search_input") else ""
        
        # 获取模型列表
        models = self.app.model_manager.list_models()
        
        # 应用过滤
        filtered_models = []
        for model in models:
            # 类别过滤
            if category != "全部" and model['type'].lower() != category.lower():
                continue
            
            # 搜索文本过滤
            if search_text and search_text.lower() not in model['name'].lower():
                continue
            
            filtered_models.append(model)
        
        # 更新模型列表
        if dpg.does_item_exist("model_list"):
            dpg.delete_item("model_list", children_only=True)
            
            with dpg.child_window(parent="model_list"):
                for model in filtered_models:
                    with dpg.group(horizontal=True):
                        dpg.add_text(f"{model['name']} ({model['type']})")
                        dpg.add_button(label="查看", callback=lambda s, a, u: self.select_model(u), user_data=model)
    
    def select_model(self, model):
        """选择模型
        
        Args:
            model: 模型信息字典
        """
        # 显示模型详情
        if dpg.does_item_exist("model_details_placeholder"):
            dpg.hide_item("model_details_placeholder")
        
        if dpg.does_item_exist("model_details_content"):
            dpg.show_item("model_details_content")
            
            # 更新模型详情
            dpg.set_value("model_name_text", f"名称: {model['name']}")
            dpg.set_value("model_category_text", f"类别: {model['type']}")
            dpg.set_value("model_type_text", f"类型: {model.get('subtype', '未知')}")
            dpg.set_value("model_task_text", f"任务: {model.get('task', '未知')}")
            dpg.set_value("model_description_text", f"描述: {model.get('description', '无描述')}")
            dpg.set_value("model_environment_text", f"环境: {model.get('environment', '默认')}")
            dpg.set_value("model_size_text", f"大小: {model.get('size', '未知')}")
            dpg.set_value("model_status_text", f"状态: {'已下载' if model.get('downloaded', False) else '未下载'}")
            
            # 更新按钮状态
            if model.get('downloaded', False):
                dpg.hide_item("download_model_button")
                dpg.show_item("use_model_button")
                dpg.show_item("delete_model_button")
            else:
                dpg.show_item("download_model_button")
                dpg.hide_item("use_model_button")
                dpg.hide_item("delete_model_button")
    
    def download_selected_model(self):
        """下载选中的模型"""
        # 获取选中的模型
        model_name = dpg.get_value("model_name_text").split(": ")[1]
        model_type = dpg.get_value("model_category_text").split(": ")[1]
        
        # 下载模型
        success = self.app.model_manager.download_model(model_name, model_type)
        
        if success:
            # 更新模型状态
            dpg.set_value("model_status_text", "状态: 已下载")
            
            # 更新按钮状态
            dpg.hide_item("download_model_button")
            dpg.show_item("use_model_button")
            dpg.show_item("delete_model_button")
            
            # 显示下载成功提示
            with dpg.window(label="提示", modal=True, width=300, height=100, tag="model_download_success_window"):
                dpg.add_text(f"模型 {model_name} 下载成功")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("model_download_success_window"))
        else:
            # 显示下载失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="model_download_error_window"):
                dpg.add_text(f"模型 {model_name} 下载失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("model_download_error_window"))
    
    def use_selected_model(self):
        """使用选中的模型"""
        # 获取选中的模型
        model_name = dpg.get_value("model_name_text").split(": ")[1]
        model_type = dpg.get_value("model_category_text").split(": ")[1]
        
        # 设置推理引擎的模型
        success = self.app.inference_engine.set_model(model_name, model_type)
        
        if success:
            # 切换到推理标签页
            dpg.set_value("main_tabs", "inference_tab")
            
            # 更新推理模型下拉列表
            if dpg.does_item_exist("inference_model_combo"):
                dpg.set_value("inference_model_combo", f"{model_name} ({model_type})")
        else:
            # 显示加载失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="model_load_error_window"):
                dpg.add_text(f"模型 {model_name} 加载失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("model_load_error_window"))
    
    def delete_selected_model(self):
        """删除选中的模型"""
        # 获取选中的模型
        model_name = dpg.get_value("model_name_text").split(": ")[1]
        model_type = dpg.get_value("model_category_text").split(": ")[1]
        
        # 确认删除
        with dpg.window(label="确认", modal=True, width=300, height=150, tag="confirm_delete_model_window"):
            dpg.add_text(f"确定要删除模型 {model_name} 吗？")
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="确定", callback=lambda: self._confirm_delete_model(model_name, model_type))
                dpg.add_button(label="取消", callback=lambda: dpg.delete_item("confirm_delete_model_window"))
    
    def _confirm_delete_model(self, model_name, model_type):
        """确认删除模型
        
        Args:
            model_name: 模型名称
            model_type: 模型类型
        """
        # 关闭确认对话框
        dpg.delete_item("confirm_delete_model_window")
        
        # 删除模型
        success = self.app.model_manager.delete_model(model_name, model_type)
        
        if success:
            # 更新模型状态
            dpg.set_value("model_status_text", "状态: 未下载")
            
            # 更新按钮状态
            dpg.show_item("download_model_button")
            dpg.hide_item("use_model_button")
            dpg.hide_item("delete_model_button")
            
            # 刷新模型列表
            self.refresh_models()
            
            # 显示删除成功提示
            with dpg.window(label="提示", modal=True, width=300, height=100, tag="model_delete_success_window"):
                dpg.add_text(f"模型 {model_name} 删除成功")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("model_delete_success_window"))
        else:
            # 显示删除失败提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="model_delete_error_window"):
                dpg.add_text(f"模型 {model_name} 删除失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("model_delete_error_window"))
    
    def select_inference_model(self, sender, value):
        """选择推理模型
        
        Args:
            sender: 发送者
            value: 选中的值
        """
        if not value:
            return
        
        # 解析模型名称和类型
        model_name, model_type = value.split(" (")
        model_type = model_type.rstrip(")")
        
        # 设置推理引擎的模型
        self.app.inference_engine.set_model(model_name, model_type)