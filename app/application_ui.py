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
        from pathlib import Path
        self.app = app
        self.dpg = dpg
        self.ui_text: Dict[str, str] = {}
        
        # 字体与缩放相关默认值
        self.base_font_size = 16
        self.current_font_size = 16
        self.font_scale_factor = 1.0
        self._current_font_tag = None
        
        # 推断项目根（用于查找 resources）
        try:
            self.project_root = getattr(self.app, "base_dir", None)
            if not self.project_root:
                self.project_root = str(Path(__file__).resolve().parents[1])
        except Exception:
            self.project_root = "."
        
        # 不在初始化时设置UI，而是在run方法中调用
        # self.setup_ui()
    
    def reset_layout(self):
        """重置布局"""
        # 保留兼容接口：可由外部调用以重新应用布局和字体
        try:
            if hasattr(self, "_apply_layout"):
                self._apply_layout()
        except Exception:
            pass
    
    def setup_ui(self):
        """设置应用程序UI（增强版，含字体自动调整与DPI处理）"""
        try:
            # 销毁可能存在的旧上下文
            try:
                if dpg.is_dearpygui_running():
                    dpg.destroy_context()
            except:
                pass
            
            dpg.create_context()
            
            # 尝试启用 DPI 感知（Windows）
            try:
                import os, ctypes
                if os.name == 'nt':
                    try:
                        ctypes.windll.shcore.SetProcessDpiAwareness(2)
                    except Exception:
                        try:
                            ctypes.windll.user32.SetProcessDPIAware()
                        except:
                            pass
            except:
                pass
            
            # 先尝试加载并绑定中文字体
            self._load_chinese_font()
            
            # 创建主窗口与菜单（保留原有文本国际化钩子）
            with dpg.window(tag="main_window", label="VisionDeploy Studio", width=1200, height=800):
                with dpg.menu_bar():
                    dpg.add_menu_item(label=self.app.get_text("menu_file", "文件"))
                    dpg.add_menu_item(label=self.app.get_text("menu_edit", "编辑"))
                    dpg.add_menu_item(label=self.app.get_text("menu_view", "视图"))
                    with dpg.menu(label=self.app.get_text("menu_language", "语言")):
                        for code, name in self.app.language_manager.get_available_languages().items():
                            dpg.add_menu_item(
                                label=name,
                                callback=lambda s, a, u: self.app.set_language(u),
                                user_data=code
                            )
                    dpg.add_menu_item(label=self.app.get_text("menu_help", "帮助"), callback=self.app.show_about)
                
                # 主标签页（保持与原实现一致）
                with dpg.tab_bar(tag="main_tabs"):
                    with dpg.tab(label=self.app.get_text("tab_models", "模型"), tag="models_tab"):
                        dpg.add_text("模型管理功能开发中...")
                    with dpg.tab(label=self.app.get_text("tab_inference", "推理"), tag="inference_tab"):
                        dpg.add_text("实时推理功能开发中...")
                    with dpg.tab(label=self.app.get_text("tab_environments", "环境"), tag="environments_tab"):
                        dpg.add_text("环境管理功能开发中...")
                    with dpg.tab(label=self.app.get_text("tab_settings", "设置"), tag="settings_tab"):
                        self._setup_settings_tab()
            
            # 标记主窗口
            dpg.set_primary_window("main_window", True)
            
            # 创建视口并启动 DPG
            try:
                if not dpg.is_viewport_created():
                    dpg.create_viewport(title='VisionDeploy Studio', width=1200, height=800)
            except:
                try:
                    dpg.create_viewport(title='VisionDeploy Studio', width=1200, height=800)
                except:
                    pass
            dpg.setup_dearpygui()
            
            # 应用首次布局与字体调整
            def _apply_layout_inner():
                try:
                    # 计算缩放并更新字体
                    try:
                        vw = dpg.get_viewport_width()
                        vh = dpg.get_viewport_height()
                    except:
                        vw, vh = 1200, 800
                    self._calculate_and_apply_font(vw, vh)
                except Exception:
                    pass
            self._apply_layout = _apply_layout_inner
            _apply_layout_inner()
            
            # 注册视口大小变化回调以动态调整字体与布局
            try:
                dpg.set_viewport_resize_callback(lambda s,a: self._apply_layout())
            except:
                pass
            
            return True
        except Exception as e:
            try:
                self.app.logger.error(f"setup_ui 错误: {e}")
            except:
                pass
            return False
    
    def is_dearpygui_running(self):
        """检查DearPyGui是否正在运行"""
        return dpg.is_dearpygui_running()
    
    def render_dearpygui_frame(self):
        """渲染DearPyGui帧"""
        dpg.render_dearpygui_frame()
    
    def _load_chinese_font(self):
        """加载中文字体以支持中文显示（使用 app.font_initializer 统一初始化）"""
        try:
            from app.font_initializer import initialize_chinese_font, initialize_chinese_font_debug, rebind_default_font
        except Exception:
            try:
                self.app.logger.warning("无法导入 app.font_initializer，跳过字体初始化")
            except:
                pass
            return False
        
        try:
            root = getattr(self.app, "base_dir", None) or self.project_root
            success = initialize_chinese_font(root)
            if success:
                try:
                    self.app.logger.info("字体初始化成功（来自 app.font_initializer）")
                except:
                    pass
                # 在某些 DPG 版本中需要在视口创建后重绑定一次
                try:
                    rebind_default_font()
                except:
                    pass
                return True
            else:
                return False
        except Exception as e:
            try:
                dbg = initialize_chinese_font_debug(root)
                try:
                    self.app.logger.warning(f"调用字体初始化失败: {e}; debug={dbg}")
                except:
                    pass
            except:
                try:
                    self.app.logger.warning(f"调用字体初始化失败: {e}")
                except:
                    pass
            return False
    
    def _calculate_and_apply_font(self, window_width=1200, window_height=800):
        """计算字体缩放并尝试应用"""
        try:
            # 参考 YOLODeployApp 的缩放逻辑，保持保守范围
            current_ratio = window_width / window_height if window_height > 0 else 1.78
            if 1.75 <= current_ratio <= 1.85:
                reference_width, reference_height = 1920, 1080
            else:
                reference_width, reference_height = 1920, 1080
            width_scale = window_width / reference_width
            height_scale = window_height / reference_height
            geometric_scale = (width_scale * height_scale) ** 0.5
            dpi_scale = 1.0
            try:
                # 尝试读取系统 DPI 影响（仅在 Windows 上启用）
                if os.name == 'nt':
                    import ctypes
                    user32 = ctypes.windll.user32
                    user32.SetProcessDPIAware()
                    dc = user32.GetDC(0)
                    dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)
                    user32.ReleaseDC(0, dc)
                    dpi_scale = max(1.0, dpi / 96.0)
            except:
                dpi_scale = 1.0
            final_scale = geometric_scale * max(1.0, dpi_scale * 0.8)
            final_scale = max(0.7, min(3.0, final_scale))
            self.font_scale_factor = final_scale
            new_font_size = int(self.base_font_size * final_scale)
            if new_font_size != self.current_font_size:
                if self._reload_font_with_size(new_font_size):
                    self.current_font_size = new_font_size
                    try:
                        self._force_ui_refresh()
                    except:
                        pass
        except Exception:
            pass
    
    def _reload_font_with_size(self, font_size):
        """尝试使用项目中的字体文件并设置全局缩放"""
        try:
            from pathlib import Path
            fonts_dir = Path(self.project_root) / "resources" / "fonts"
            candidates = []
            vf = fonts_dir / "MiSans VF.ttf"
            if vf.exists():
                candidates.append(vf)
            candidates += sorted(fonts_dir.glob("MiSans*.ttf"))
            candidates += sorted(fonts_dir.glob("*.ttf"))
            candidates += sorted(fonts_dir.glob("*.ttc"))
            if not candidates:
                candidates += sorted(fonts_dir.glob("*.otf"))
            if not candidates:
                return False
            scale_factor = font_size / self.base_font_size if self.base_font_size > 0 else 1.0
            try:
                dpg.set_global_font_scale(scale_factor)
            except:
                pass
            # Ensure base font exists
            base_tag = f"base_font_{self.base_font_size}"
            try:
                if not dpg.does_item_exist(base_tag):
                    with dpg.font_registry():
                        f = dpg.add_font(str(candidates[0]), self.base_font_size, tag=base_tag)
                        try:
                            dpg.add_font_range(0x4e00, 0x9fff, parent=f)
                            dpg.add_font_range(0x0020, 0x007F, parent=f)
                        except:
                            pass
                        try:
                            dpg.bind_font(f)
                        except:
                            pass
                self._current_font_tag = base_tag
                return True
            except Exception:
                return False
        except Exception:
            return False
    
    def _update_ui_component_sizes(self):
        """更新UI组件的尺寸以适配字体缩放（保守策略）"""
        try:
            current_scale = dpg.get_global_font_scale()
            ui_scale = max(0.8, min(2.0, current_scale * 0.9 + 0.1))
            # 更新常见组件（若存在）
            updates = [
                ('start_btn', int(100 * ui_scale), int(23 * ui_scale)),
                ('stop_btn', int(100 * ui_scale), int(23 * ui_scale)),
                ('prepare_env_btn', None, int(23 * ui_scale)),
            ]
            for tag, w, h in updates:
                try:
                    if dpg.does_item_exist(tag):
                        cfg = {}
                        if w is not None:
                            cfg['width'] = w
                        if h is not None:
                            cfg['height'] = h
                        if cfg:
                            dpg.configure_item(tag, **cfg)
                except:
                    pass
        except:
            pass
    
    def _force_ui_refresh(self):
        """强制刷新UI以应用字体变化"""
        try:
            for i in range(2):
                dpg.split_frame()
            try:
                if hasattr(self, 'font_status_text') and dpg.does_item_exist(self.font_status_text):
                    cur = dpg.get_value(self.font_status_text)
                    dpg.set_value(self.font_status_text, cur + " ")
                    dpg.set_value(self.font_status_text, cur)
            except:
                pass
        except:
            pass
    
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