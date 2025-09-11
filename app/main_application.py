"""
主应用程序 - VisionDeploy Studio
负责初始化和管理整个应用程序
"""

import os
import sys
import logging
from app.application_core import ApplicationCore
from app.application_ui import ApplicationUI
from app.language_manager import LanguageManager
from app.handlers.model_handlers import ModelHandlers
from app.handlers.inference_handlers import InferenceHandlers
from app.handlers.environment_handlers import EnvironmentHandlers
from app.handlers.settings_handlers import SettingsHandlers

class MainApplication:
    """主应用程序类，负责初始化和管理整个应用程序"""
    
    def __init__(self):
        """初始化主应用程序"""
        # 设置基本路径
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 验证项目结构
        from app.file_validator import FileValidator
        validator = FileValidator(self.base_dir)
        is_valid, message = validator.validate_project_structure()
        if not is_valid:
            raise RuntimeError(f"项目结构验证失败: {message}")
        
        # 初始化日志
        import logging
        self.logger = logging.getLogger("VisionDeploy.MainApplication")
        
        # 初始化核心功能
        self.core = ApplicationCore(self.base_dir)
        
        # 初始化语言管理器
        self.language_manager = LanguageManager(self.base_dir)
        
        # 初始化UI（不在这里调用setup_ui，而是在run方法中调用）
        from app.application_ui import ApplicationUI
        self.ui = ApplicationUI(self)
        
        # 初始化处理模块
        self.model_handlers = ModelHandlers(self)
        self.inference_handlers = InferenceHandlers(self)
        self.environment_handlers = EnvironmentHandlers(self)
        self.settings_handlers = SettingsHandlers(self)
        
        # 将核心功能暴露为属性
        self.app_state = self.core.app_state
        self.device_summary = self.core.device_summary
        self.model_manager = self.core.model_manager
        self.environment_manager = self.core.environment_manager
        self.performance_monitor = self.core.performance_monitor
        self.inference_engine = self.core.inference_engine
    
    def get_text(self, key: str, default: str | None = None) -> str:
        """获取当前语言的文本
        
        Args:
            key: 文本键
            default: 默认值
            
        Returns:
            str: 对应的文本或默认值
        """
        return self.language_manager.get_text(key, default)
    
    def set_language(self, lang_code: str) -> bool:
        """设置当前语言
        
        Args:
            lang_code: 语言代码
            
        Returns:
            bool: 是否设置成功
        """
        if self.language_manager.set_language(lang_code):
            self.ui.update_ui_text()
            return True
        return False
    
    def run(self):
        """运行应用程序"""
        # 初始化日志
        self.core.init_logging()
        self.logger.info("项目结构验证通过")
        self.logger = logging.getLogger("VisionDeploy.MainApplication")
        self.logger.info("正在启动VisionDeploy Studio...")
        
        # 加载配置
        self.core.load_config()
        
        # 设置UI
        try:
            self.ui.setup_ui()
            # 显示视图端口
            try:
                self.ui.dpg.show_viewport()
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"设置UI时出错: {e}")
            raise
        
        # 启动性能监控
        if self.app_state.get('performance_monitoring'):
            try:
                self.performance_monitor.start_monitoring()
            except Exception:
                pass
        
        # 加载模型列表
        try:
            self.model_handlers.refresh_models()
        except Exception:
            pass
        
        # 加载环境列表
        try:
            self.environment_handlers.refresh_environments()
        except Exception:
            pass
        
        # 使用 DearPyGUI 的内置循环来确保 viewport 正确启动（相较于手动 render 循环更稳定）
        try:
            # 尝试以非阻塞方式启动（某些 DPG 版本需直接调用 start_dearpygui）
            self.ui.dpg.start_dearpygui()
        except Exception:
            # 若 start_dearpygui 不可用或抛异常，尝试手动渲染循环作为回退
            try:
                while self.ui.dpg.is_dearpygui_running():
                    if self.app_state.get('performance_monitoring'):
                        try:
                            self.performance_monitor.update_ui()
                        except:
                            pass
                    try:
                        self.ui.dpg.render_dearpygui_frame()
                    except:
                        break
            except Exception:
                pass
        
        # 清理资源
        try:
            self.core.cleanup()
        except Exception:
            pass
    
    # 代理方法到各个处理模块
    def refresh_models(self):
        """刷新模型列表"""
        self.model_handlers.refresh_models()
    
    def filter_models(self, sender=None, value=None):
        """过滤模型列表"""
        self.model_handlers.filter_models(sender, value)
    
    def select_model(self, model):
        """选择模型"""
        self.model_handlers.select_model(model)
    
    def download_selected_model(self):
        """下载选中的模型"""
        self.model_handlers.download_selected_model()
    
    def use_selected_model(self):
        """使用选中的模型"""
        self.model_handlers.use_selected_model()
    
    def delete_selected_model(self):
        """删除选中的模型"""
        self.model_handlers.delete_selected_model()
    
    def select_inference_model(self, sender, value):
        """选择推理模型"""
        self.model_handlers.select_inference_model(sender, value)
    
    def select_input_source(self, sender, value):
        """选择输入源"""
        self.inference_handlers.select_input_source(sender, value)
    
    def set_camera_id(self, sender, value):
        """设置摄像头ID"""
        self.inference_handlers.set_camera_id(sender, value)
    
    def select_input_file(self):
        """选择输入文件"""
        self.inference_handlers.select_input_file()
    
    def set_confidence_threshold(self, sender, value):
        """设置置信度阈值"""
        self.inference_handlers.set_confidence_threshold(sender, value)
    
    def set_iou_threshold(self, sender, value):
        """设置IOU阈值"""
        self.inference_handlers.set_iou_threshold(sender, value)
    
    def start_inference(self):
        """开始推理"""
        self.inference_handlers.start_inference()
    
    def stop_inference(self):
        """停止推理"""
        self.inference_handlers.stop_inference()
    
    def refresh_environments(self):
        """刷新环境列表"""
        self.environment_handlers.refresh_environments()
    
    def filter_environments(self, sender=None, value=None):
        """过滤环境列表"""
        self.environment_handlers.filter_environments(sender, value)
    
    def select_environment(self, environment):
        """选择环境"""
        self.environment_handlers.select_environment(environment)
    
    def create_selected_environment(self):
        """创建选中的环境"""
        self.environment_handlers.create_selected_environment()
    
    def delete_selected_environment(self):
        """删除选中的环境"""
        self.environment_handlers.delete_selected_environment()
    
    def edit_selected_environment(self):
        """编辑选中的环境"""
        self.environment_handlers.edit_selected_environment()
    
    def show_add_environment_dialog(self):
        """显示添加环境对话框"""
        self.environment_handlers.show_add_environment_dialog()
    
    def exit_app(self):
        """退出应用程序"""
        self.settings_handlers.exit_app()
    
    def toggle_theme(self):
        """切换主题"""
        self.settings_handlers.toggle_theme()
    
    def reset_layout(self):
        """重置布局"""
        if hasattr(self.ui, 'reset_layout') and callable(getattr(self.ui, 'reset_layout', None)):
            self.ui.reset_layout()
        else:
            # 如果UI组件没有reset_layout方法，则忽略
            pass
    
    def show_settings(self):
        """显示设置"""
        if hasattr(self.settings_handlers, 'show_settings'):
            self.settings_handlers.show_settings()
    
    def show_about(self):
        """显示关于对话框"""
        if hasattr(self.settings_handlers, 'show_about'):
            self.settings_handlers.show_about()
    
    def open_docs(self):
        """打开文档"""
        if hasattr(self.settings_handlers, 'open_docs'):
            self.settings_handlers.open_docs()
    
    def refresh_system_info(self):
        """刷新系统信息"""
        self.device_summary = self.core.hardware_detector.get_device_summary()
        self.reset_layout()
    
    def toggle_performance_monitoring(self):
        """切换性能监控"""
        self.settings_handlers.toggle_performance_monitoring()
    
    def set_network_timeout(self, sender, value):
        """设置网络超时时间"""
        self.settings_handlers.set_network_timeout(sender, value)
    
    def set_network_retries(self, sender, value):
        """设置网络重试次数"""
        self.settings_handlers.set_network_retries(sender, value)
    
    def set_models_path(self, sender, value):
        """设置模型存储路径"""
        self.settings_handlers.set_models_path(sender, value)
    
    def browse_models_path(self):
        """浏览模型存储路径"""
        self.settings_handlers.browse_models_path()
    
    def set_environments_path(self, sender, value):
        """设置环境存储路径"""
        self.settings_handlers.set_environments_path(sender, value)
    
    def browse_environments_path(self):
        """浏览环境存储路径"""
        self.settings_handlers.browse_environments_path()
    
    def save_settings(self):
        """保存设置"""
        self.settings_handlers.save_settings()
    
    def reset_settings(self):
        """重置设置"""
        self.settings_handlers.reset_settings()