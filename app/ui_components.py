"""
UI组件模块 - VisionDeploy Studio
包含所有UI组件的创建和管理功能
"""

import os
import sys
import dearpygui.dearpygui as dpg
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

class UIComponents:
    """UI组件类，负责创建和管理所有UI元素"""
    
    def __init__(self, app):
        """初始化UI组件
        
        Args:
            app: 主应用程序实例
        """
        self.app = app
        self.base_dir = app.base_dir
        
        # 主题
        self.dark_theme = None
        self.light_theme = None
    
    def init_themes(self):
        """初始化主题"""
        # 设置主题
        with dpg.theme() as self.dark_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (25, 25, 25))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (40, 40, 40))
                dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 60, 60))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70, 70, 70))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (80, 80, 80))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (65, 105, 225))
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (70, 130, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (65, 105, 225))
        
        with dpg.theme() as self.light_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (240, 240, 240))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (220, 220, 220))
                dpg.add_theme_color(dpg.mvThemeCol_Button, (200, 200, 200))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (190, 190, 190))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (180, 180, 180))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (100, 150, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (120, 170, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (100, 150, 255))
    
    def apply_theme(self, dark_mode=True):
        """应用主题
        
        Args:
            dark_mode: 是否使用暗色主题
        """
        if dark_mode and self.dark_theme:
            dpg.bind_theme(self.dark_theme)
        elif not dark_mode and self.light_theme:
            dpg.bind_theme(self.light_theme)
        else:
            # 如果主题未初始化，使用默认主题
            dpg.bind_theme(0)  # 使用0而不是None
    
    def reset_layout(self):
        """重置布局"""
        # 这里可以添加重置布局的逻辑
        pass
    
    def create_main_window(self):
        """创建主窗口"""
        # 主窗口
        with dpg.window(label="VisionDeploy Studio", tag="main_window", no_title_bar=True, no_resize=True, no_move=True, no_collapse=True):
            # 顶部菜单栏
            with dpg.menu_bar():
                with dpg.menu(label="文件"):
                    dpg.add_menu_item(label="设置", callback=self.app.show_settings)
                    dpg.add_menu_item(label="退出", callback=self.app.exit_app)
                
                with dpg.menu(label="视图"):
                    dpg.add_menu_item(label="切换暗色/亮色模式", callback=self.app.toggle_theme)
                    dpg.add_menu_item(label="重置布局", callback=self.app.reset_layout)
                
                with dpg.menu(label="帮助"):
                    dpg.add_menu_item(label="关于", callback=self.app.show_about)
                    dpg.add_menu_item(label="文档", callback=self.app.open_docs)
            
            # 主要内容区域
            with dpg.tab_bar(tag="main_tabs"):
                # 仪表盘标签页
                with dpg.tab(label="仪表盘", tag="dashboard_tab"):
                    self.create_dashboard_tab()
                
                # 模型浏览器标签页
                with dpg.tab(label="模型浏览器", tag="model_browser_tab"):
                    self.create_model_browser_tab()
                
                # 推理标签页
                with dpg.tab(label="推理", tag="inference_tab"):
                    self.create_inference_tab()
                
                # 环境管理标签页
                with dpg.tab(label="环境管理", tag="environment_tab"):
                    self.create_environment_tab()
                
                # 设置标签页
                with dpg.tab(label="设置", tag="settings_tab"):
                    self.create_settings_tab()
            
            # 底部状态栏
            with dpg.group(horizontal=True):
                dpg.add_text("状态: 就绪")
                dpg.add_spacer(width=20)
                dpg.add_text(f"最佳设备: {self.app.device_summary['best_device']['type'].upper()} - {self.app.device_summary['best_device']['name']}")
                dpg.add_spacer(width=20)
                dpg.add_text(f"Python: {sys.version.split()[0]}")
                dpg.add_spacer(width=20)
                dpg.add_text("VisionDeploy Studio v1.0.0")
    
    def create_dashboard_tab(self):
        """创建仪表盘标签页"""
        with dpg.group(horizontal=True):
            # 左侧系统信息
            with dpg.child_window(width=400, height=600, tag="system_info_window"):
                dpg.add_text("系统信息", color=(65, 105, 225))
                dpg.add_separator()
                
                # 操作系统信息
                dpg.add_text("操作系统", color=(150, 150, 150))
                dpg.add_text(f"名称: {self.app.device_summary['system']['os']}")
                dpg.add_text(f"版本: {self.app.device_summary['system']['os_version']}")
                dpg.add_text(f"架构: {self.app.device_summary['system']['architecture']}")
                dpg.add_spacer(height=10)
                
                # CPU信息
                dpg.add_text("CPU", color=(150, 150, 150))
                dpg.add_text(f"处理器: {self.app.device_summary['system']['processor']}")
                dpg.add_text(f"物理核心: {self.app.device_summary['devices']['cpu']['cores']}")
                dpg.add_text(f"逻辑核心: {self.app.device_summary['devices']['cpu']['threads']}")
                dpg.add_spacer(height=10)
                
                # 内存信息
                dpg.add_text("内存", color=(150, 150, 150))
                dpg.add_text(f"总内存: {self.app.device_summary['devices']['memory']['total_gb']} GB")
                dpg.add_text(f"可用内存: {self.app.device_summary['devices']['memory']['available_gb']} GB")
                dpg.add_spacer(height=10)
                
                # GPU信息
                dpg.add_text("GPU", color=(150, 150, 150))
                
                # NVIDIA GPU
                if 'nvidia' in self.app.device_summary['devices']:
                    dpg.add_text(f"NVIDIA GPU: {self.app.device_summary['devices']['nvidia']['count']} 个")
                    for i, model in enumerate(self.app.device_summary['devices']['nvidia']['models']):
                        dpg.add_text(f"  {i+1}. {model}")
                
                # AMD GPU
                if 'amd' in self.app.device_summary['devices']:
                    dpg.add_text(f"AMD GPU: {self.app.device_summary['devices']['amd']['count']} 个")
                    for i, model in enumerate(self.app.device_summary['devices']['amd']['models']):
                        dpg.add_text(f"  {i+1}. {model}")
                
                # Intel GPU
                if 'intel' in self.app.device_summary['devices']:
                    dpg.add_text(f"Intel GPU: {self.app.device_summary['devices']['intel']['count']} 个")
                    for i, model in enumerate(self.app.device_summary['devices']['intel']['models']):
                        dpg.add_text(f"  {i+1}. {model}")
                
                # 华为NPU
                if 'huawei' in self.app.device_summary['devices']:
                    dpg.add_text(f"华为NPU: {self.app.device_summary['devices']['huawei']['count']} 个")
                    for i, model in enumerate(self.app.device_summary['devices']['huawei']['models']):
                        dpg.add_text(f"  {i+1}. {model}")
                
                # 摩尔线程MUSA
                if 'musa' in self.app.device_summary['devices']:
                    dpg.add_text(f"摩尔线程MUSA: {self.app.device_summary['devices']['musa']['count']} 个")
                    for i, model in enumerate(self.app.device_summary['devices']['musa']['models']):
                        dpg.add_text(f"  {i+1}. {model}")
                
                if not any(gpu in self.app.device_summary['devices'] for gpu in ['nvidia', 'amd', 'intel', 'huawei', 'musa']):
                    dpg.add_text("未检测到GPU")
                
                dpg.add_spacer(height=10)
                
                # Python信息
                dpg.add_text("Python", color=(150, 150, 150))
                dpg.add_text(f"版本: {self.app.device_summary['system']['python_version'].split()[0]}")
                
                # 刷新按钮
                dpg.add_spacer(height=20)
                dpg.add_button(label="刷新系统信息", callback=self.app.refresh_system_info)
            
            # 右侧性能监控
            with dpg.child_window(width=-1, height=600, tag="performance_window"):
                dpg.add_text("性能监控", color=(65, 105, 225))
                dpg.add_separator()
                
                # CPU使用率图表
                dpg.add_text("CPU使用率")
                with dpg.plot(label="CPU使用率", height=100, width=-1, tag="cpu_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, label="时间", tag="cpu_x_axis")
                    dpg.set_axis_limits(dpg.last_item(), 0, 100)
                    
                    dpg.add_plot_axis(dpg.mvYAxis, label="使用率 (%)", tag="cpu_y_axis")
                    dpg.set_axis_limits(dpg.last_item(), 0, 100)
                    
                    dpg.add_line_series([], [], label="CPU使用率", parent="cpu_y_axis", tag="cpu_series")
                
                # 内存使用率图表
                dpg.add_text("内存使用率")
                with dpg.plot(label="内存使用率", height=100, width=-1, tag="memory_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, label="时间", tag="memory_x_axis")
                    dpg.set_axis_limits(dpg.last_item(), 0, 100)
                    
                    dpg.add_plot_axis(dpg.mvYAxis, label="使用率 (%)", tag="memory_y_axis")
                    dpg.set_axis_limits(dpg.last_item(), 0, 100)
                    
                    dpg.add_line_series([], [], label="内存使用率", parent="memory_y_axis", tag="memory_series")
                
                # GPU使用率图表
                dpg.add_text("GPU使用率")
                with dpg.plot(label="GPU使用率", height=100, width=-1, tag="gpu_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, label="时间", tag="gpu_x_axis")
                    dpg.set_axis_limits(dpg.last_item(), 0, 100)
                    
                    dpg.add_plot_axis(dpg.mvYAxis, label="使用率 (%)", tag="gpu_y_axis")
                    dpg.set_axis_limits(dpg.last_item(), 0, 100)
                    
                    dpg.add_line_series([], [], label="GPU使用率", parent="gpu_y_axis", tag="gpu_series")
                
                # GPU内存使用率图表
                dpg.add_text("GPU内存使用率")
                with dpg.plot(label="GPU内存使用率", height=100, width=-1, tag="gpu_memory_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, label="时间", tag="gpu_memory_x_axis")
                    dpg.set_axis_limits(dpg.last_item(), 0, 100)
                    
                    dpg.add_plot_axis(dpg.mvYAxis, label="使用率 (%)", tag="gpu_memory_y_axis")
                    dpg.set_axis_limits(dpg.last_item(), 0, 100)
                    
                    dpg.add_line_series([], [], label="GPU内存使用率", parent="gpu_memory_y_axis", tag="gpu_memory_series")
    
    def create_model_browser_tab(self):
        """创建模型浏览器标签页"""
        with dpg.group(horizontal=True):
            # 左侧模型列表
            with dpg.child_window(width=300, height=600, tag="model_list_window"):
                dpg.add_text("模型列表", color=(65, 105, 225))
                dpg.add_separator()
                
                # 模型类别选择
                dpg.add_text("模型类别")
                dpg.add_combo(["全部", "YOLO", "CNN", "Transformer"], default_value="全部", callback=self.app.filter_models, tag="model_category_combo")
                
                dpg.add_spacer(height=10)
                
                # 模型搜索
                dpg.add_text("搜索模型")
                dpg.add_input_text(callback=self.app.filter_models, tag="model_search_input")
                
                dpg.add_spacer(height=10)
                
                # 模型列表
                dpg.add_text("可用模型")
                
                with dpg.child_window(height=400, tag="model_list"):
                    # 模型列表将在运行时填充
                    pass
                
                # 刷新按钮
                dpg.add_button(label="刷新模型列表", callback=self.app.refresh_models)
            
            # 右侧模型详情
            with dpg.child_window(width=-1, height=600, tag="model_details_window"):
                dpg.add_text("模型详情", color=(65, 105, 225))
                dpg.add_separator()
                
                # 模型详情将在选择模型时填充
                dpg.add_text("请从左侧列表选择一个模型查看详情", tag="model_details_placeholder")
                
                # 模型详情内容
                with dpg.group(tag="model_details_content", show=False):
                    dpg.add_text("", tag="model_name_text")
                    dpg.add_text("", tag="model_category_text")
                    dpg.add_text("", tag="model_type_text")
                    dpg.add_text("", tag="model_task_text")
                    dpg.add_text("", tag="model_description_text")
                    dpg.add_text("", tag="model_environment_text")
                    dpg.add_text("", tag="model_size_text")
                    dpg.add_text("", tag="model_status_text")
                    
                    dpg.add_spacer(height=20)
                    
                    # 模型操作按钮
                    with dpg.group(horizontal=True, tag="model_actions"):
                        dpg.add_button(label="下载模型", callback=self.app.download_selected_model, tag="download_model_button")
                        dpg.add_button(label="使用此模型", callback=self.app.use_selected_model, tag="use_model_button")
                        dpg.add_button(label="删除模型", callback=self.app.delete_selected_model, tag="delete_model_button")
    
    def create_inference_tab(self):
        """创建推理标签页"""
        with dpg.group(horizontal=True):
            # 左侧控制面板
            with dpg.child_window(width=300, height=600, tag="inference_control_window"):
                dpg.add_text("推理控制", color=(65, 105, 225))
                dpg.add_separator()
                
                # 模型选择
                dpg.add_text("选择模型")
                dpg.add_combo([], callback=self.app.select_inference_model, tag="inference_model_combo")
                
                dpg.add_spacer(height=10)
                
                # 输入源选择
                dpg.add_text("输入源")
                dpg.add_radio_button(["摄像头", "图片文件", "视频文件"], default_value="摄像头", callback=self.app.select_input_source, tag="input_source_radio")
                
                # 摄像头选项
                with dpg.group(tag="camera_options"):
                    dpg.add_text("摄像头ID")
                    dpg.add_input_int(default_value=0, min_value=0, max_value=10, callback=self.app.set_camera_id, tag="camera_id_input")
                
                # 文件选项
                with dpg.group(tag="file_options", show=False):
                    dpg.add_button(label="选择文件", callback=self.app.select_input_file)
                    dpg.add_text("未选择文件", tag="selected_file_text")
                
                dpg.add_spacer(height=10)
                
                # 推理参数
                dpg.add_text("推理参数")
                
                dpg.add_text("置信度阈值")
                dpg.add_slider_float(default_value=0.25, min_value=0.01, max_value=1.0, format="%.2f", callback=self.app.set_confidence_threshold, tag="confidence_slider")
                
                dpg.add_text("IOU阈值")
                dpg.add_slider_float(default_value=0.45, min_value=0.01, max_value=1.0, format="%.2f", callback=self.app.set_iou_threshold, tag="iou_slider")
                
                dpg.add_spacer(height=20)
                
                # 推理控制按钮
                dpg.add_button(label="开始推理", callback=self.app.start_inference, tag="start_inference_button")
                dpg.add_button(label="停止推理", callback=self.app.stop_inference, tag="stop_inference_button", enabled=False)
                
                dpg.add_spacer(height=20)
                
                # 输出选项
                dpg.add_text("输出选项")
                dpg.add_checkbox(label="保存结果", tag="save_results_checkbox")
                
                with dpg.group(tag="output_options", show=False):
                    dpg.add_button(label="选择保存路径", callback=self.app.select_output_path)
                    dpg.add_text("未选择保存路径", tag="output_path_text")
            
            # 右侧推理结果显示
            with dpg.child_window(width=-1, height=600, tag="inference_result_window"):
                dpg.add_text("推理结果", color=(65, 105, 225))
                dpg.add_separator()
                
                # 推理结果图像
                with dpg.group(horizontal=True):
                    # 图像显示区域
                    with dpg.child_window(width=-1, height=400, tag="inference_image_window"):
                        dpg.add_text("等待推理开始...", tag="inference_status_text")
                        
                        # 图像纹理将在运行时创建
                        with dpg.texture_registry():
                            dpg.add_raw_texture(100, 100, [], tag="inference_texture")
                        
                        dpg.add_image("inference_texture", tag="inference_image")
                
                # 推理统计信息
                with dpg.group(tag="inference_stats"):
                    dpg.add_text("统计信息", color=(150, 150, 150))
                    dpg.add_text("FPS: -", tag="fps_text")
                    dpg.add_text("推理时间: - ms", tag="inference_time_text")
                    dpg.add_text("检测到的对象: -", tag="detected_objects_text")
    
    def create_environment_tab(self):
        """创建环境管理标签页"""
        with dpg.group(horizontal=True):
            # 左侧环境列表
            with dpg.child_window(width=300, height=600, tag="environment_list_window"):
                dpg.add_text("环境列表", color=(65, 105, 225))
                dpg.add_separator()
                
                # 环境搜索
                dpg.add_text("搜索环境")
                dpg.add_input_text(callback=self.app.filter_environments, tag="environment_search_input")
                
                dpg.add_spacer(height=10)
                
                # 环境列表
                dpg.add_text("可用环境")
                
                with dpg.child_window(height=400, tag="environment_list"):
                    # 环境列表将在运行时填充
                    pass
                
                # 刷新按钮
                dpg.add_button(label="刷新环境列表", callback=self.app.refresh_environments)
                dpg.add_button(label="添加新环境", callback=self.app.show_add_environment_dialog)
            
            # 右侧环境详情
            with dpg.child_window(width=-1, height=600, tag="environment_details_window"):
                dpg.add_text("环境详情", color=(65, 105, 225))
                dpg.add_separator()
                
                # 环境详情将在选择环境时填充
                dpg.add_text("请从左侧列表选择一个环境查看详情", tag="environment_details_placeholder")
                
                # 环境详情内容
                with dpg.group(tag="environment_details_content", show=False):
                    dpg.add_text("", tag="environment_name_text")
                    dpg.add_text("", tag="environment_python_version_text")
                    dpg.add_text("", tag="environment_status_text")
                    dpg.add_text("", tag="environment_path_text")
                    
                    dpg.add_spacer(height=10)
                    
                    # 包列表
                    dpg.add_text("包列表")
                    with dpg.child_window(height=300, tag="package_list_window"):
                        # 包列表将在选择环境时填充
                        pass
                    
                    dpg.add_spacer(height=20)
                    
                    # 环境操作按钮
                    with dpg.group(horizontal=True, tag="environment_actions"):
                        dpg.add_button(label="创建环境", callback=self.app.create_selected_environment, tag="create_environment_button")
                        dpg.add_button(label="删除环境", callback=self.app.delete_selected_environment, tag="delete_environment_button")
                        dpg.add_button(label="编辑环境", callback=self.app.edit_selected_environment, tag="edit_environment_button")
    
    def create_settings_tab(self):
        """创建设置标签页"""
        with dpg.group():
            dpg.add_text("应用设置", color=(65, 105, 225))
            dpg.add_separator()
            
            # 外观设置
            dpg.add_text("外观", color=(150, 150, 150))
            dpg.add_checkbox(label="暗色模式", default_value=self.app.app_state['dark_mode'], callback=self.app.toggle_theme, tag="dark_mode_checkbox")
            
            dpg.add_spacer(height=10)
            
            # 性能设置
            dpg.add_text("性能", color=(150, 150, 150))
            dpg.add_checkbox(label="启用性能监控", default_value=self.app.app_state['performance_monitoring'], callback=self.app.toggle_performance_monitoring, tag="performance_monitoring_checkbox")
            
            dpg.add_spacer(height=10)
            
            # 网络设置
            dpg.add_text("网络", color=(150, 150, 150))
            
            dpg.add_text("超时时间 (秒)")
            dpg.add_input_int(default_value=30, callback=self.app.set_network_timeout, tag="network_timeout_input")
            
            dpg.add_text("重试次数")
            dpg.add_input_int(default_value=3, callback=self.app.set_network_retries, tag="network_retries_input")
            
            dpg.add_spacer(height=10)
            
            # 路径设置
            dpg.add_text("路径设置", color=(150, 150, 150))
            
            dpg.add_text("模型存储路径")
            dpg.add_input_text(default_value=os.path.join(self.base_dir, "resources", "models"), callback=self.app.set_models_path, tag="models_path_input")
            dpg.add_button(label="浏览...", callback=self.app.browse_models_path)
            
            dpg.add_text("环境存储路径")
            dpg.add_input_text(default_value=os.path.join(self.base_dir, "environments"), callback=self.app.set_environments_path, tag="environments_path_input")
            dpg.add_button(label="浏览...", callback=self.app.browse_environments_path)
            
            dpg.add_spacer(height=20)
            
            # 保存设置按钮
            dpg.add_button(label="保存设置", callback=self.app.save_settings)
            dpg.add_button(label="重置设置", callback=self.app.reset_settings)