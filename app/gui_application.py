import dearpygui.dearpygui as dpg
import threading
import time
from pathlib import Path
from datetime import datetime
import psutil
import GPUtil
import sys
import os
import locale
from pathlib import Path
import ctypes

# 在程序最开始就设置编码
# 设置系统编码以支持中文
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 尝试设置系统区域以支持中文
try:
    locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Chinese_China.936')
    except:
        pass

# 修复相对导入问题
# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置系统编码以支持中文
try:
    # 设置控制台编码为UTF-8
    if hasattr(sys.stdout, 'reconfigure') and callable(getattr(sys.stdout, 'reconfigure', None)):
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure') and callable(getattr(sys.stderr, 'reconfigure', None)):
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

# 确保子进程也使用UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
# 设置子进程的环境变量
subprocess_env = os.environ.copy()
subprocess_env['PYTHONIOENCODING'] = 'utf-8'

# 在 Windows 上启用进程 DPI 感知，避免非整数缩放导致的文字发虚
try:
    if os.name == 'nt':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor v2
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()  # 旧版兜底
except Exception:
    pass

# 需要 YAML 支持用于保存模型->设备映射
try:
    import yaml
except Exception:
    yaml = None

# 初始化默认的模拟类
class MockModelInvoker:
    def invoke_best_model(self, *args, **kwargs):
        raise Exception("模型调用失败：缺少依赖")
    def invoke_model(self, *args, **kwargs):
        raise Exception("模型调用失败：缺少依赖")
    def stop_all_processes(self):
        pass

class MockHardwareDetector:
    def get_recommended_model_env(self):
        return "yolov5-cuda"

class MockEnvironmentManager:
    def is_environment_ready(self, env_name):
        return False
    
    def prepare_environment(self, env_name, callback=None):
        # 模拟环境准备过程
        if callback:
            callback("准备环境...", 0)
            time.sleep(1)
            callback("下载Python...", 20)
            time.sleep(1)
            callback("创建虚拟环境...", 40)
            time.sleep(1)
            callback("安装依赖包...", 60)
            time.sleep(2)
            callback("环境准备完成", 100)
        return True
    
    def list_available_environments(self):
        return [
            {'name': 'yolov5-cuda', 'python_version': '3.8.10', 'packages': [], 'ready': False},
            {'name': 'yolov8-cuda', 'python_version': '3.9.7', 'packages': [], 'ready': False},
            {'name': 'ppyolo-xpu', 'python_version': '3.10.0', 'packages': [], 'ready': False}
        ]

# 初始化默认的模拟对象
model_invoker = MockModelInvoker()
hardware_detector = MockHardwareDetector()
OnDemandEnvironmentManager = MockEnvironmentManager  # 默认使用模拟类

try:
    from core.model_invoker import model_invoker
    from core.hardware_detector import hardware_detector
    from core.on_demand_environment_manager import OnDemandEnvironmentManager
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        from core.model_invoker import model_invoker
        from core.hardware_detector import hardware_detector
        from core.on_demand_environment_manager import OnDemandEnvironmentManager
    except ImportError as e:
        print(f"导入核心模块失败: {e}")
        # 使用模拟对象以避免程序崩溃
        model_invoker = MockModelInvoker()
        hardware_detector = MockHardwareDetector()
        OnDemandEnvironmentManager = MockEnvironmentManager

class YOLODeployApp:
    def __init__(self):
        self.is_running = False
        self.current_model = None
        self.current_image = None
        self.inference_results = []
        self.performance_data = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'gpu_usage': 0,
            'vram_usage': 0
        }
        # 当前界面语言（'zh' 或 'en'）
        self.current_language = 'zh'
        # 分隔条与布局状态
        self.split_ratio = 0.28  # 左侧面板比例
        self._dragging_splitter = False
        self._drag_start_x = 0.0
        self._left_width = 320
        
        # 字体缩放状态
        self.base_font_size = 16  # 基础字体大小（1080p基准）
        self.current_font_size = 16
        self.font_scale_factor = 1.0
        self._current_font_tag = None
        
        # UI组件基础尺寸（与base_font_size对应）
        self.base_button_width = 100
        self.base_button_height = 23
        self.base_slider_width = 120
        self.base_progress_width = 200
        self.base_input_width = 150
        
        # 获取屏幕DPI信息
        self.screen_dpi = self._get_screen_dpi()
        self.dpi_scale = max(1.0, self.screen_dpi / 96.0)  # 96 DPI为基准

        # 初始化环境管理器
        try:
            self.environment_manager = OnDemandEnvironmentManager(str(project_root))
        except Exception as e:
            print(f"环境管理器初始化失败: {e}")
            # 创建模拟环境管理器实例
            self.environment_manager = MockEnvironmentManager()

    def switch_language(self, lang: str):
        """在运行时切换中/英文界面（只切换可控项的标签与文本）"""
        try:
            lang = str(lang).lower()
            self.current_language = 'en' if lang.startswith('en') else 'zh'
            if self.current_language == 'en':
                # 状态与主要字段
                try:
                    dpg.set_value(self.status_text, "Ready")
                except:
                    pass
                try:
                    dpg.set_value(self.model_text, "None")
                except:
                    pass
                try:
                    dpg.set_value(self.backend_text, "CPU")
                except:
                    pass
                # 按钮与控件标签（通过 tag）
                for tag, label in [
                    ('prepare_env_btn', "Prepare Env"),
                    ('select_file_btn', "Select Image"),
                    ('start_btn', "Start"),
                    ('stop_btn', "Stop"),
                    ('save_btn', "Save Results"),
                    ('model_combo', "Select model"),
                    ('source_radio', "Source")
                ]:
                    try:
                        if dpg.does_item_exist(tag):
                            dpg.set_item_label(tag, label)
                    except:
                        pass
                # 面板标题（若存在可设置标签的项）
                try:
                    dpg.set_item_label("main_window", "VisionDeploy Studio")
                except:
                    pass
            else:
                # 切回中文（尽量保留原文）
                try:
                    dpg.set_value(self.status_text, "就绪")
                except:
                    pass
                try:
                    dpg.set_value(self.model_text, "未选择")
                except:
                    pass
                try:
                    dpg.set_value(self.backend_text, "CPU")
                except:
                    pass
                for tag, label in [
                    ('prepare_env_btn', "准备选中环境"),
                    ('select_file_btn', "选择图片文件"),
                    ('start_btn', "开始推理"),
                    ('stop_btn', "停止"),
                    ('save_btn', "保存结果"),
                    ('model_combo', "选择模型"),
                    ('source_radio', "数据源")
                ]:
                    try:
                        if dpg.does_item_exist(tag):
                            dpg.set_item_label(tag, label)
                    except:
                        pass
                try:
                    dpg.set_item_label("main_window", "YOLO部署助手")
                except:
                    pass
        except Exception as e:
            print(f"switch_language 错误: {e}")
    
    def _get_screen_dpi(self):
        """获取屏幕DPI"""
        try:
            if os.name == 'nt':  # Windows
                import ctypes
                user32 = ctypes.windll.user32
                user32.SetProcessDPIAware()
                dc = user32.GetDC(0)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
                user32.ReleaseDC(0, dc)
                return dpi
            else:
                # Linux/macOS 默认值
                return 96
        except Exception:
            return 96
    
    def _calculate_font_scale(self, window_width=1200, window_height=800):
        """
        基于窗口尺寸和标准分辨率比例计算字体缩放因子
        支持常见的16:9和16:10比例，避免极端拉伸导致的过度缩放
        
        Args:
            window_width: 当前窗口宽度
            window_height: 当前窗口高度
            
        Returns:
            字体缩放因子
        """
        try:
            # 标准分辨率参考点（16:9比例）
            standard_resolutions = {
                # 分辨率: (宽度, 高度, 预期缩放)
                'hd': (1280, 720, 0.8),      # HD
                'fhd': (1920, 1080, 1.0),    # Full HD (基准)
                '2k': (2560, 1440, 1.33),    # 2K
                '4k': (3840, 2160, 2.0),     # 4K
            }
            
            # 计算当前窗口比例
            current_ratio = window_width / window_height if window_height > 0 else 1.78
            
            # 常见比例范围
            ratio_16_9 = 16/9  # ≈ 1.78
            ratio_16_10 = 16/10  # = 1.6
            ratio_4_3 = 4/3    # ≈ 1.33
            
            # 判断窗口比例类型并选择合适的参考分辨率
            if 1.75 <= current_ratio <= 1.85:  # 接近16:9
                reference_width, reference_height = 1920, 1080
            elif 1.55 <= current_ratio <= 1.65:  # 接近16:10
                reference_width, reference_height = 1920, 1200
            elif 1.25 <= current_ratio <= 1.4:   # 接近4:3或更方形
                reference_width, reference_height = 1600, 1200
            else:
                # 异常比例：使用保守的缩放策略
                if current_ratio > 2.0:  # 过宽窗口
                    # 主要基于高度，限制最大缩放
                    height_scale = min(2.5, window_height / 800)
                    return max(0.7, min(2.5, height_scale * self.dpi_scale * 0.8))
                elif current_ratio < 1.0:  # 过高窗口
                    # 主要基于宽度，限制最大缩放
                    width_scale = min(2.5, window_width / 1200)
                    return max(0.7, min(2.5, width_scale * self.dpi_scale * 0.8))
                else:
                    # 默认处理
                    reference_width, reference_height = 1920, 1080
            
            # 计算相对于参考分辨率的缩放
            width_scale = window_width / reference_width
            height_scale = window_height / reference_height
            
            # 使用几何平均避免极端缩放
            geometric_scale = (width_scale * height_scale) ** 0.5
            
            # 应用DPI影响
            dpi_scale = max(1.0, self.dpi_scale * 0.8)
            
            # 综合缩放因子
            final_scale = geometric_scale * dpi_scale
            
            # 限制缩放范围，避免过小或过大
            return max(0.7, min(3.0, final_scale))
            
        except Exception as e:
            print(f"缩放计算错误: {e}")
            return 1.0
    
    def _update_font_size(self, force_reload=False):
        """
        根据当前窗口尺寸和比例更新字体
        
        Args:
            force_reload: 是否强制重新加载字体
        """
        try:
            # 获取当前窗口宽度和高度
            try:
                vw = dpg.get_viewport_width()
                vh = dpg.get_viewport_height()
            except:
                vw, vh = 1200, 800  # 默认值
            
            # 计算新的缩放因子（基于宽度和高度）
            new_scale = self._calculate_font_scale(vw, vh)
            
            # 如果缩放因子变化不大且不强制重载，则跳过
            if not force_reload and abs(new_scale - self.font_scale_factor) < 0.03:
                return False
            
            self.font_scale_factor = new_scale
            new_font_size = int(self.base_font_size * new_scale)
            
            # 如果字体大小没变化，跳过
            if not force_reload and new_font_size == self.current_font_size:
                return False
            
            # 计算窗口比例用于显示
            ratio = vw / vh if vh > 0 else 1.78
            print(f"窗口尺寸: {vw}x{vh}px (比例: {ratio:.2f}), 缩放因子: {new_scale:.2f}, 新字体大小: {new_font_size}px")
            self.current_font_size = new_font_size
            
            # 重新加载字体
            success = self._reload_font_with_size(new_font_size)
            
            if success:
                # 强制刷新界面以显示新字体
                self._force_ui_refresh()
                # 更新UI组件尺寸以适应新字体
                self._update_ui_component_sizes()
                
            return success
            
        except Exception as e:
            print(f"更新字体大小失败: {e}")
            return False
    
    def _reload_font_with_size(self, font_size):
        """
        重新加载指定大小的字体
        
        Args:
            font_size: 字体大小
            
        Returns:
            是否成功重新加载
        """
        try:
            # 查找字体文件
            fonts_dir = project_root / "resources" / "fonts"
            candidates = []
            
            # 按优先级查找字体文件
            vf = fonts_dir / "MiSans VF.ttf"
            if vf.exists():
                candidates.append(vf)
            candidates += sorted(fonts_dir.glob("MiSans*.ttf"))
            candidates += sorted(fonts_dir.glob("*.ttf"))
            candidates += sorted(fonts_dir.glob("*.ttc"))
            if not candidates:
                candidates += sorted(fonts_dir.glob("*.otf"))
            
            if not candidates:
                print(f"未找到字体文件，使用系统默认字体")
                return False
            
            # 新字体标签
            new_font_tag = f"dynamic_font_{font_size}"
            
            # 如果已存在相同大小的字体，直接使用
            if dpg.does_item_exist(new_font_tag):
                try:
                    # 关键修改：使用全局字体缩放而不是字体绑定
                    dpg.set_global_font_scale(font_size / self.base_font_size)
                    self._current_font_tag = new_font_tag
                    print(f"使用全局缩放切换字体: {font_size}px (缩放: {font_size / self.base_font_size:.2f})")
                    return True
                except Exception:
                    pass
            
            # 尝试创建新字体并使用全局缩放
            success = False
            for font_path in candidates:
                try:
                    # 先尝试全局字体缩放方法
                    scale_factor = font_size / self.base_font_size
                    dpg.set_global_font_scale(scale_factor)
                    
                    # 如果基础字体不存在，创建基础字体
                    base_font_tag = f"base_font_{self.base_font_size}"
                    if not dpg.does_item_exist(base_font_tag):
                        with dpg.font_registry():
                            font_obj = dpg.add_font(str(font_path), self.base_font_size, tag=base_font_tag)
                            # 添加中文字符范围
                            try:
                                dpg.add_font_range(0x4e00, 0x9fff, parent=font_obj)  # 中文字符
                                dpg.add_font_range(0x0020, 0x007F, parent=font_obj)  # ASCII
                            except Exception:
                                pass
                        # 绑定基础字体
                        dpg.bind_font(base_font_tag)
                    
                    self._current_font_tag = new_font_tag
                    success = True
                    print(f"成功设置字体缩放: {font_path.name}, 基础{self.base_font_size}px × {scale_factor:.2f} = {font_size}px")
                    break
                    
                except Exception as e:
                    print(f"设置字体缩放失败 {font_path.name}: {e}")
                    continue
            
            if not success:
                print(f"无法设置 {font_size}px 字体，保持当前字体")
            
            return success
            
        except Exception as e:
            print(f"重新加载字体失败: {e}")
            return False
    
    def _get_scaled_size(self, base_size, is_width=True):
        """
        根据当前字体缩放因子计算UI组件尺寸
        
        Args:
            base_size: 基础尺寸
            is_width: 是否为宽度（宽度和高度可能有不同的缩放策略）
            
        Returns:
            缩放后的尺寸
        """
        try:
            current_scale = dpg.get_global_font_scale()
            # UI组件的缩放比字体缩放稍微保守一些，避免界面过大
            ui_scale = max(0.8, min(2.0, current_scale * 0.9 + 0.1))
            return int(base_size * ui_scale)
        except Exception:
            return base_size
    
    def _update_ui_component_sizes(self):
        """
        更新所有UI组件的尺寸以适应新的字体大小
        """
        try:
            # 获取当前缩放因子
            current_scale = dpg.get_global_font_scale()
            
            # 计算UI组件的缩放比例（比字体缩放稍微保守）
            ui_scale = max(0.8, min(2.0, current_scale * 0.9 + 0.1))
            
            # 更新按钮尺寸
            button_width = int(self.base_button_width * ui_scale)
            button_height = int(self.base_button_height * ui_scale)
            small_button_width = int(60 * ui_scale)
            medium_button_width = int(80 * ui_scale)
            
            # 更新滑动条和进度条尺寸
            slider_width = int(self.base_slider_width * ui_scale)
            progress_width = int(self.base_progress_width * ui_scale)
            
            # 需要更新的组件列表
            button_updates = [
                ('prepare_env_btn', None, button_height),
                ('select_file_btn', None, button_height),
                ('start_btn', button_width, button_height),
                ('stop_btn', button_width, button_height),
                ('save_btn', None, button_height),
            ]
            
            slider_updates = [
                ('confidence_slider', slider_width, None),
                ('iou_slider', slider_width, None),
                ('font_size_slider', slider_width, None),
            ]
            
            progress_updates = [
                ('cpu_meter', progress_width, None),
                ('memory_meter', progress_width, None),
                ('gpu_meter', progress_width, None),
                ('vram_meter', progress_width, None),
            ]
            
            # 应用更新
            for tag, width, height in button_updates:
                if dpg.does_item_exist(tag):
                    config = {}
                    if width is not None:
                        config['width'] = width
                    if height is not None:
                        config['height'] = height
                    if config:
                        dpg.configure_item(tag, **config)
            
            for tag, width, height in slider_updates:
                if dpg.does_item_exist(tag):
                    if width is not None:
                        dpg.configure_item(tag, width=width)
            
            for tag, width, height in progress_updates:
                if dpg.does_item_exist(tag):
                    if width is not None:
                        dpg.configure_item(tag, width=width)
            
            # 更新自定义按钮
            custom_buttons = [
                ('test_small_font_btn', medium_button_width, button_height),
                ('test_large_font_btn', medium_button_width, button_height),
                ('force_refresh_btn', medium_button_width, button_height),
                ('auto_adjust_btn', medium_button_width, button_height),
                ('apply_font_btn', small_button_width, button_height),
            ]
            
            for tag, width, height in custom_buttons:
                if dpg.does_item_exist(tag):
                    dpg.configure_item(tag, width=width, height=height)
            
            print(f"UI组件尺寸更新完成，缩放比例: {ui_scale:.2f}")
            
        except Exception as e:
            print(f"更新UI组件尺寸失败: {e}")
    
    def _force_ui_refresh(self):
        """
        强制刷新UI以显示新字体效果
        """
        try:
            # 方法1: 强制重绘多帧
            for i in range(3):
                dpg.split_frame()
            
            # 方法2: 延迟刷新多次
            def _multi_refresh():
                try:
                    for i in range(5):
                        dpg.render_dearpygui_frame()
                        dpg.split_frame()
                except Exception:
                    pass
            
            # 在多个帧后执行刷新
            dpg.set_frame_callback(3, _multi_refresh)
            
            # 方法3: 更新所有相关UI元素
            try:
                if dpg.does_item_exist('font_size_slider'):
                    dpg.set_value('font_size_slider', self.current_font_size)
                
                # 强制重新设置一些文本内容来触发重绘
                if hasattr(self, 'status_text'):
                    current_status = dpg.get_value(self.status_text)
                    dpg.set_value(self.status_text, current_status + " ")
                    dpg.set_value(self.status_text, current_status)
                    
            except Exception:
                pass
                
            print(f"UI强制刷新完成，当前字体: {self.current_font_size}px")
            
        except Exception as e:
            print(f"UI刷新失败: {e}")
        
    def setup_gui(self):
        """设置GUI界面"""
        # 尝试创建DearPyGui上下文，如果已存在则忽略错误
        try:
            dpg.create_context()
        except:
            # 上下文可能已存在，忽略错误
            pass
        
        # Windows 下开启 DPI 感知，避免 125%/150% 缩放导致的字体发虚
        try:
            if hasattr(dpg, "configure_app"):
                dpg.configure_app(dpi_aware=True)
        except Exception:
            # 低版本 DPG 可能没有该参数，忽略
            pass
        
        # 初始字体加载（使用动态计算的大小）
        initial_font_size = int(self.base_font_size * self._calculate_font_scale())
        self.current_font_size = initial_font_size
        
        # 为与最小复现保持一致：在创建窗口前尽量完成字体注册与绑定（优先 TTF，再回退）
        try:
            from app.font_initializer import initialize_chinese_font
        except Exception:
            initialize_chinese_font = None

        if not getattr(self, '_font_initialized', False):
            fonts_dir = project_root / "resources" / "fonts"
            candidates = []
            try:
                # 优先 ttf（MiSans VF 或 MiSans*.ttf），然后 ttc，再 otf
                vf = fonts_dir / "MiSans VF.ttf"
                if vf.exists():
                    candidates.append(vf)
                candidates += sorted(fonts_dir.glob("MiSans*.ttf"))
                candidates += sorted(fonts_dir.glob("*.ttf"))
                candidates += sorted(fonts_dir.glob("*.ttc"))
                if not candidates:
                    candidates += sorted(fonts_dir.glob("MiSans-*.otf"))
                    candidates += sorted(fonts_dir.glob("*.otf"))
            except Exception:
                candidates = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))

            # 尝试 add_additional_font 优先加载（若可用）
            add_additional = getattr(dpg, "add_additional_font", None)
            if callable(add_additional) and candidates:
                for cand in candidates:
                    try:
                        try:
                            font_obj = add_additional(str(cand), initial_font_size, glyph_ranges='chinese_simplified_common')
                        except TypeError:
                            font_obj = add_additional(str(cand), initial_font_size, glyph_ranges='chinese_full')
                        try:
                            dpg.bind_font(font_obj)
                        except Exception:
                            # 记录对象以便后续在 setup_dearpygui 后重试绑定
                            self._additional_font_obj = font_obj
                        self._font_initialized = True
                        self._font_path_used = str(cand)
                        break
                    except Exception:
                        continue

            # 如果 add_additional_font 未成功，使用 add_font + range hints（确保在 font_registry 中）
            if not getattr(self, '_font_initialized', False) and candidates:
                for cand in candidates:
                    try:
                        with dpg.font_registry():
                            f = dpg.add_font(str(cand), initial_font_size, tag="default_font")
                            # 添加 range hint（若可用）
                            for hint_name in ("mvFontRangeHint_Default", "mvFontRangeHint_Chinese_Simplified_Common", "mvFontRangeHint_Chinese_Full"):
                                hint = getattr(dpg, hint_name, None)
                                if hint is not None:
                                    try:
                                        dpg.add_font_range_hint(hint, parent=f)
                                    except:
                                        pass
                            # 兜底 unicode 范围
                            try:
                                dpg.add_font_range(0x4e00, 0x9fff, parent=f)
                            except:
                                pass
                        try:
                            dpg.bind_font(f)
                        except Exception:
                            # 记录以便后续重试
                            self._additional_font_obj = f
                        self._font_initialized = True
                        self._font_path_used = str(cand)
                        break
                    except Exception:
                        continue

            # 最后回退到 initialize_chinese_font（保留兼容）
            if not getattr(self, '_font_initialized', False) and initialize_chinese_font:
                try:
                    if initialize_chinese_font(project_root):
                        self._font_initialized = True
                        self._font_path_used = "initialize_chinese_font-selected"
                except:
                    pass

        # 创建主窗口，使用无边框设计（使用英文项目名以避免中文字体兼容问题）
        with dpg.window(label="VisionDeploy Studio", tag="main_window",
                        no_title_bar=True, no_resize=False, no_move=True, no_collapse=True):
            # 顶部状态栏
            with dpg.group(horizontal=True):
                dpg.add_text("状态: ")
                self.status_text = dpg.add_text("就绪", color=[0, 255, 0])
                dpg.add_spacer(width=20)
                dpg.add_text("模型: ")
                self.model_text = dpg.add_text("未选择")
                dpg.add_spacer(width=20)
                dpg.add_text("后端: ")
                self.backend_text = dpg.add_text("CPU")

            # 主内容区域 - 使用水平分组而不是嵌套窗口
            with dpg.group(horizontal=True):
                # 左侧控制面板
                with dpg.child_window(width=300, height=700, tag="control_panel"):
                    self.setup_control_panel()

                # 分隔条（可拖动）
                with dpg.child_window(width=6, height=700, tag="splitter", no_scrollbar=True):
                    dpg.add_separator()

                # 右侧显示区域
                with dpg.child_window(height=700, tag="display_panel"):
                    self.setup_display_panel()

        # 创建视图端口，设置正确的标题和编码
        try:
            # 先设置视口配置（使用英文项目名）
            dpg.configure_viewport(0, title='VisionDeploy Studio')
            if not dpg.is_viewport_created():
                dpg.create_viewport(title='VisionDeploy Studio', width=1200, height=800)
        except:
            # 如果上面的方法失败，使用传统方式
            try:
                dpg.create_viewport(title='YOLO Deploy Assistant', width=1200, height=800)
            except:
                pass

        dpg.setup_dearpygui()

        # 注册视口缩放回调，按比例调整各区域尺寸
        def _apply_layout():
            try:
                vw = dpg.get_viewport_width()
                vh = dpg.get_viewport_height()
                left_w = max(240, int(vw * self.split_ratio))
                padding = 20
                panel_h = max(300, vh - 120)
                right_w = max(400, vw - left_w - padding*2 - 6)

                if dpg.does_item_exist("control_panel"):
                    dpg.configure_item("control_panel", width=left_w, height=panel_h)
                if dpg.does_item_exist("splitter"):
                    dpg.configure_item("splitter", width=6, height=panel_h)
                if dpg.does_item_exist("display_panel"):
                    dpg.configure_item("display_panel", width=right_w, height=panel_h)
                if dpg.does_item_exist("display_canvas"):
                    canvas_h = max(200, int(panel_h*0.7))
                    dpg.configure_item("display_canvas", width=right_w-10, height=canvas_h)
                    
                # 根据窗口尺寸和比例更新字体（关键修改：同时考虑宽度和高度）
                font_updated = self._update_font_size()
                if font_updated:
                    self._update_font_status_display()
            except Exception:
                pass

        def _on_viewport_resize(sender, app_data):
            _apply_layout()

        # 分隔条拖动：按下-移动-松开
        def _splitter_mouse_down(sender, app_data):
            self._dragging_splitter = True
            self._drag_start_x = dpg.get_mouse_pos(local=False)[0]
        def _splitter_mouse_up(sender, app_data):
            self._dragging_splitter = False
        def _splitter_mouse_move(sender, app_data):
            if not self._dragging_splitter:
                return
            vw = max(1, dpg.get_viewport_width())
            x = dpg.get_mouse_pos(local=False)[0]
            # 计算新的比例，限制范围
            new_ratio = min(0.6, max(0.18, x / vw))
            if abs(new_ratio - self.split_ratio) > 0.001:
                self.split_ratio = new_ratio
                _apply_layout()

        # 给分隔条绑定鼠标事件
        try:
            if dpg.does_item_exist("splitter"):
                dpg.set_item_callback("splitter", None)
                dpg.bind_item_handler_registry("splitter", dpg.add_item_handler_registry(tag="splitter_handlers"))
                dpg.add_item_clicked_handler(parent="splitter_handlers", callback=_splitter_mouse_down)
                dpg.add_item_released_handler(parent="splitter_handlers", callback=_splitter_mouse_up)
                dpg.add_item_active_handler(parent="splitter_handlers", callback=_splitter_mouse_move)
        except Exception:
            pass

        try:
            dpg.set_viewport_resize_callback(_on_viewport_resize)
        except Exception:
            pass

        # 尝试在视口/上下文设置完成后重试绑定字体以解决部分 DPG 版本的绑定时机问题
        try:
            from app.font_initializer import rebind_default_font
            # 立即尝试一次重绑定；若失败则安排在下一帧重试
            try:
                if not rebind_default_font():
                    def _rebind_later():
                        try:
                            rebind_default_font()
                        except:
                            pass
                    dpg.split_frame()
                    dpg.set_frame_callback(2, _rebind_later)
            except:
                pass
        except Exception:
            pass

        # 设置主窗口
        dpg.set_primary_window("main_window", True)
        
        # 首次应用布局和字体
        _apply_layout()
        
        # 性能监控定时器
        dpg.set_frame_callback(60, self.update_performance)
    
    def _load_chinese_font(self):
        """加载中文字体以支持中文显示（使用 app.font_initializer 统一初始化）"""
        try:
            from app.font_initializer import initialize_chinese_font, initialize_chinese_font_debug
        except Exception:
            print("无法导入 app.font_initializer，跳过字体初始化")
            return False

        try:
            success = initialize_chinese_font(project_root)
            if success:
                print("字体初始化成功（来自 app.font_initializer）")
                return True
            else:
                print("字体初始化模块未找到可用字体，继续使用系统默认字体")
                return False
        except Exception as e:
            # 尝试收集调试信息以便后续分析
            try:
                dbg = initialize_chinese_font_debug(project_root)
                print(f"调用字体初始化失败: {e}; debug={dbg}")
            except:
                print(f"调用字体初始化失败: {e}")
            return False
    
    def setup_control_panel(self):
        """设置控制面板"""
        # 去除 Emoji，避免在部分字体/平台显示为问号
        dpg.add_text("资源", color=[255, 200, 0])

        # CPU使用率
        with dpg.group(horizontal=True):
            dpg.add_text("CPU:")
            self.cpu_meter = dpg.add_progress_bar(default_value=0, width=200, tag="cpu_meter")
            self.cpu_text = dpg.add_text("0%")

        # 内存使用率
        with dpg.group(horizontal=True):
            dpg.add_text("内存:")
            self.memory_meter = dpg.add_progress_bar(default_value=0, width=200, tag="memory_meter")
            self.memory_text = dpg.add_text("0%")

        # GPU使用率
        with dpg.group(horizontal=True):
            dpg.add_text("GPU:")
            self.gpu_meter = dpg.add_progress_bar(default_value=0, width=200, tag="gpu_meter")
            self.gpu_text = dpg.add_text("0%")

        # VRAM使用率
        with dpg.group(horizontal=True):
            dpg.add_text("显存:")
            self.vram_meter = dpg.add_progress_bar(default_value=0, width=200, tag="vram_meter")
            self.vram_text = dpg.add_text("0/0 GB")

        dpg.add_separator()
        dpg.add_text("模型设置", color=[255, 200, 0])

        # 模型选择
        dpg.add_combo(
            items=['yolov5-cuda', 'yolov8-cuda', 'ppyolo-xpu', '自动选择'],
            default_value='自动选择',
            label="选择模型",
            callback=self.on_model_change,
            tag='model_combo'
        )

        # 推理设备选择（由用户决定；基于硬件检测构造选项，默认 CPU）
        try:
            device_items = ['CPU', 'Auto']
            summary = {}
            try:
                if hasattr(hardware_detector, 'get_device_summary'):
                    summary = hardware_detector.get_device_summary() or {}
            except:
                summary = {}

            cpu_brand = ''
            try:
                cpu_info = summary.get('cpu', {})
                if isinstance(cpu_info, dict):
                    cpu_brand = cpu_info.get('brand', '') or ''
            except:
                cpu_brand = ''

            # 收集来自 summary 的 GPU 条目（结构各异，做容错）
            gpus = summary.get('gpu', []) if isinstance(summary.get('gpu', []), list) else []

            # 尝试使用 GPUtil 作为补充来源（更可靠地发现独立 GPU）
            try:
                gputils = GPUtil.getGPUs() or []
                for g in gputils:
                    try:
                        gname = getattr(g, 'name', None) or getattr(g, 'brand', None) or str(g)
                        gpus.append({'brand': gname})
                    except:
                        continue
            except Exception:
                pass

            # 平台级别的回退检测（Windows: wmic, Linux: lspci）
            try:
                import subprocess
                import platform
                if os.name == 'nt':
                    try:
                        res = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], capture_output=True, text=True, env=subprocess_env)
                        for line in (res.stdout or "").splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            # 跳过表头
                            if line.lower().startswith('name'):
                                continue
                            gpus.append({'brand': line})
                    except Exception:
                        pass
                else:
                    try:
                        res = subprocess.run(['lspci'], capture_output=True, text=True)
                        for line in (res.stdout or "").splitlines():
                            if 'vga' in line.lower() or '3d controller' in line.lower():
                                # 取冒号后描述
                                parts = line.split(':', 2)
                                if len(parts) >= 3:
                                    brand_desc = parts[2].strip()
                                else:
                                    brand_desc = parts[-1].strip()
                                if brand_desc:
                                    gpus.append({'brand': brand_desc})
                    except Exception:
                        pass
            except Exception:
                pass

            # 最后尝试从平台信息或环境变量判断是否为 Intel 平台（用于增加集成 GPU 选项）
            try:
                import platform
                proc = (platform.processor() or "").lower()
                uname = " ".join(platform.uname()).lower()
                env_proc = (os.environ.get('PROCESSOR_IDENTIFIER') or "").lower()
                if 'intel' in proc or 'intel' in uname or 'intel' in env_proc or 'intel' in cpu_brand.lower():
                    likely_intel = True
                else:
                    likely_intel = False
            except Exception:
                likely_intel = False

            # 去重并优先把已检测到的独立 GPU 放到前面
            seen = set()
            for g in gpus:
                brand = (g.get('brand', '') or '').strip()
                if not brand:
                    continue
                b_lower = brand.lower()
                if 'nvidia' in b_lower:
                    manufacturer = 'NVIDIA'
                elif 'amd' in b_lower or 'radeon' in b_lower:
                    manufacturer = 'AMD'
                elif 'intel' in b_lower:
                    manufacturer = 'Intel'
                else:
                    manufacturer = brand.split()[0]
                label = f"GPU - {manufacturer}"
                if label not in seen:
                    # 把独立显卡放到前面
                    device_items.insert(0, label)
                    seen.add(label)

            # 若未检测到任何 GPU 条目，但平台可能是 Intel，回填集成 GPU 选项
            if not any(it.startswith('GPU -') for it in device_items) and likely_intel:
                device_items.insert(0, 'GPU - Intel')

            # 确保基础选项存在且去重
            if 'CPU' not in device_items:
                device_items.append('CPU')
            if 'Auto' not in device_items:
                device_items.append('Auto')

            # 最终去重并保持顺序（保留插入的优先顺序）
            final_items = []
            for it in device_items:
                if it not in final_items:
                    final_items.append(it)

            # 额外平台级别检测（wmic/lspci）再次尝试识别厂商并插入到选项顶部
            try:
                import subprocess
                gpu_manufacturers = set()
                if os.name == 'nt':
                    try:
                        res = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], capture_output=True, text=True, env=subprocess_env)
                        for line in (res.stdout or "").splitlines():
                            ln = line.strip()
                            if not ln:
                                continue
                            if ln.lower().startswith('name'):
                                continue
                            if 'nvidia' in ln.lower():
                                gpu_manufacturers.add('NVIDIA')
                            elif 'amd' in ln.lower() or 'radeon' in ln.lower():
                                gpu_manufacturers.add('AMD')
                            elif 'intel' in ln.lower():
                                gpu_manufacturers.add('Intel')
                    except Exception:
                        pass
                else:
                    try:
                        res = subprocess.run(['lspci'], capture_output=True, text=True)
                        for line in (res.stdout or "").splitlines():
                            if 'vga' in line.lower() or '3d controller' in line.lower():
                                ln = line.strip()
                                if 'nvidia' in ln.lower():
                                    gpu_manufacturers.add('NVIDIA')
                                elif 'amd' in ln.lower() or 'radeon' in ln.lower():
                                    gpu_manufacturers.add('AMD')
                                elif 'intel' in ln.lower():
                                    gpu_manufacturers.add('Intel')
                    except Exception:
                        pass

                # 将识别到的厂商置于选项顶部
                for m in sorted(gpu_manufacturers, reverse=True):
                    label = f"GPU - {m}"
                    if label not in final_items:
                        final_items.insert(0, label)

                # 最后兜底：若仍然只有 CPU/Auto，且平台可能为 Intel，则加入 GPU - Intel
                if len(final_items) <= 2 and likely_intel and 'GPU - Intel' not in final_items:
                    final_items.insert(0, 'GPU - Intel')
            except Exception:
                # 忽略检测错误，保持当前选项
                pass

            dpg.add_combo(items=final_items, default_value='CPU', label="选择设备", tag='device_combo')
        except Exception:
            # 极端降级：确保至少有 CPU/Auto 和 Intel 选项，避免空列表
            try:
                dpg.add_combo(items=['CPU', 'Auto', 'GPU - Intel'], default_value='CPU', label="选择设备", tag='device_combo')
            except Exception:
                dpg.add_combo(items=['CPU', 'Auto'], default_value='CPU', label="选择设备", tag='device_combo')

        # 环境准备按钮
        dpg.add_button(
            label="准备选中环境",
            callback=self.prepare_environment,
            tag='prepare_env_btn'
        )

        # 环境状态显示
        self.env_status_text = dpg.add_text("环境状态: 未准备", color=[255, 165, 0])

        # 参数设置
        with dpg.group(horizontal=True):
            dpg.add_slider_float(
                label="置信度",
                min_value=0.1,
                max_value=0.9,
                default_value=0.5,
                width=120,
                tag='confidence_slider'
            )
            dpg.add_slider_float(
                label="IOU阈值",
                min_value=0.1,
                max_value=0.9,
                default_value=0.45,
                width=120,
                tag='iou_slider'
            )

        dpg.add_separator()
        dpg.add_text("数据源", color=[255, 200, 0])

        # 数据源选择
        dpg.add_radio_button(
            items=['摄像头', '图片文件', '视频文件'],
            default_value='图片文件',
            callback=self.on_source_change,
            tag='source_radio'
        )

        # 文件选择
        dpg.add_button(
            label="选择图片文件",
            callback=self.select_image_file,
            tag='select_file_btn'
        )

        # 控制按钮
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="开始推理",
                callback=self.start_inference,
                tag='start_btn',
                width=100
            )
            dpg.add_button(
                label="停止",
                callback=self.stop_inference,
                tag='stop_btn',
                width=100,
                show=False
            )

        dpg.add_button(
            label="保存结果",
            callback=self.save_results,
            tag='save_btn'
        )

        # 结果显示
        dpg.add_separator()
        dpg.add_text("检测结果", color=[255, 200, 0])
        self.results_text = dpg.add_text("等待推理...", wrap=250)
        
        # 字体调试控制（可选）
        dpg.add_separator()
        dpg.add_text("字体调试", color=[200, 200, 200])
        with dpg.group(horizontal=True):
            dpg.add_slider_int(
                label="字体大小", 
                min_value=12, 
                max_value=48,  # 扩展到48以支持4K
                default_value=self.current_font_size,
                width=120,
                tag='font_size_slider',
                callback=self._on_font_size_change
            )
            dpg.add_button(
                label="应用",
                callback=self._apply_manual_font_size,
                width=60
            )
        
        # 添加强制刷新按钮和当前状态显示
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="强制刷新",
                callback=self._force_refresh_button,
                width=80,
                tag="force_refresh_btn"
            )
            dpg.add_button(
                label="自动调整",
                callback=self._auto_adjust_font,
                width=80,
                tag="auto_adjust_btn"
            )
        
        # 添加字体测试按钮
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="测试小字体",
                callback=lambda: self._test_font_size(14),
                width=80,
                tag="test_small_font_btn"
            )
            dpg.add_button(
                label="测试大字体", 
                callback=lambda: self._test_font_size(32),
                width=80,
                tag="test_large_font_btn"
            )
        
        # 显示当前字体状态
        self.font_status_text = dpg.add_text(f"当前: {self.current_font_size}px", color=[150, 255, 150])
    
    def setup_display_panel(self):
        """设置显示面板"""
        dpg.add_text("实时显示", color=[255, 200, 0])

        # 图像显示区域
        with dpg.drawlist(width=600, height=400, tag="display_canvas"):
            # 这里将显示检测结果
            pass

        # 详细信息区域
        dpg.add_separator()
        dpg.add_text("Details", color=[255, 200, 0])
        self.details_text = dpg.add_text("选择文件开始推理...", wrap=550)
    
    def _on_font_size_change(self, sender, app_data):
        """字体大小滑块变化回调"""
        pass  # 仅用于实时显示，实际应用由按钮触发
    
    def _apply_manual_font_size(self):
        """手动应用字体大小"""
        try:
            manual_size = dpg.get_value('font_size_slider')
            self.current_font_size = manual_size
            success = self._reload_font_with_size(manual_size)
            if success:
                self._force_ui_refresh()  # 手动模式也需要刷新
                self._update_font_status_display()
                print(f"手动设置字体大小为: {manual_size}px")
            else:
                print(f"手动设置字体大小失败")
        except Exception as e:
            print(f"手动应用字体大小错误: {e}")
    
    def _force_refresh_button(self):
        """强制刷新按钮回调"""
        try:
            self._force_ui_refresh()
            print("手动触发UI刷新")
        except Exception as e:
            print(f"手动刷新失败: {e}")
    
    def _auto_adjust_font(self):
        """自动调整字体按钮回调"""
        try:
            success = self._update_font_size(force_reload=True)
            if success:
                self._update_font_status_display()
                print("自动调整字体完成")
            else:
                print("自动调整字体失败")
        except Exception as e:
            print(f"自动调整字体错误: {e}")
    
    def _test_font_size(self, size):
        """测试特定字体大小"""
        try:
            print(f"测试字体大小: {size}px")
            self.current_font_size = size
            success = self._reload_font_with_size(size)
            if success:
                self._force_ui_refresh()
                self._update_font_status_display()
                # 更新滑块显示
                if dpg.does_item_exist('font_size_slider'):
                    dpg.set_value('font_size_slider', size)
                print(f"测试字体 {size}px 应用成功")
            else:
                print(f"测试字体 {size}px 应用失败")
        except Exception as e:
            print(f"测试字体大小错误: {e}")
    
    def _update_font_status_display(self):
        """更新字体状态显示"""
        try:
            if hasattr(self, 'font_status_text') and dpg.does_item_exist(self.font_status_text):
                try:
                    vw = dpg.get_viewport_width()
                    vh = dpg.get_viewport_height()
                    current_scale = dpg.get_global_font_scale()
                    ratio = vw / vh if vh > 0 else 1.78
                except:
                    vw, vh = 1200, 800  # 默认值
                    current_scale = 1.0
                    ratio = 1.5
                status_text = f"当前: {self.current_font_size}px ({vw}x{vh}, 比例: {ratio:.2f}, 缩放: {current_scale:.2f})"
                dpg.set_value(self.font_status_text, status_text)
        except Exception:
            pass
    
    def update_performance(self):
        """更新性能监控数据"""
        if not self.is_running:
            return
        
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent()
            dpg.set_value(self.cpu_meter, cpu_usage / 100)
            dpg.set_value(self.cpu_text, f"{cpu_usage}%")
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            dpg.set_value(self.memory_meter, memory_usage / 100)
            dpg.set_value(self.memory_text, f"{memory_usage}%")
            
            # GPU使用率
            gpus = GPUtil.getGPUs()
            gpu_usage = 0  # 初始化默认值
            vram_usage = 0  # 初始化默认值
            
            if gpus:
                gpu = gpus[0]
                gpu_usage = gpu.load * 100
                vram_usage = gpu.memoryUsed / gpu.memoryTotal * 100
                
                dpg.set_value(self.gpu_meter, gpu.load)
                dpg.set_value(self.gpu_text, f"{gpu_usage:.1f}%")
                dpg.set_value(self.vram_meter, vram_usage / 100)
                dpg.set_value(self.vram_text, f"{gpu.memoryUsed:.1f}/{gpu.memoryTotal:.1f} GB")
            else:
                # 没有GPU时的默认值显示
                dpg.set_value(self.gpu_meter, 0)
                dpg.set_value(self.gpu_text, "0%")
                dpg.set_value(self.vram_meter, 0)
                dpg.set_value(self.vram_text, "0/0 GB")
            
            self.performance_data = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'gpu_usage': gpu_usage,
                'vram_usage': vram_usage
            }
            
        except Exception as e:
            print(f"性能监控错误: {e}")
        
        # 继续更新
        dpg.set_frame_callback(60, self.update_performance)
    
    def on_model_change(self, sender, app_data):
        """模型选择改变 — 弹窗让用户为该模型选择/确认推理设备并保存映射"""
        self.current_model = app_data
        try:
            if app_data == '自动选择':
                recommended = hardware_detector.get_recommended_model_env()
                dpg.set_value(self.model_text, f"自动 ({recommended})")
            else:
                dpg.set_value(self.model_text, app_data)
        except:
            pass

        # 弹出交互式对话，询问并保存模型->设备映射
        try:
            self._open_model_device_modal(app_data)
        except Exception as e:
            print(f"打开模型设备映射对话框失败: {e}")

        # 更新环境状态（仍保持原行为）
        try:
            self.update_environment_status()
        except:
            pass

    def _open_model_device_modal(self, model_name):
        """打开模型->设备选择模态对话；若已有映射则回填并直接应用"""
        try:
            # 准备映射存储路径
            map_path = project_root / "config" / "model_device_map.yaml"
            mapping = {}

            # 尝试读取已有映射（若 yaml 可用）
            if map_path.exists():
                try:
                    if yaml:
                        mapping = yaml.safe_load(map_path.read_text(encoding='utf-8')) or {}
                    else:
                        # 简单解析文本回退（键: 值 每行）
                        raw = map_path.read_text(encoding='utf-8').splitlines()
                        for line in raw:
                            if ':' in line:
                                k, v = line.split(':', 1)
                                mapping[k.strip()] = v.strip()
                except Exception:
                    mapping = {}

            # 若已有映射，则直接回填并应用（不再弹窗）
            if mapping and model_name in mapping:
                device = mapping.get(model_name)
                try:
                    if dpg.does_item_exist('device_combo'):
                        dpg.set_value('device_combo', device)
                except:
                    pass
                try:
                    dpg.set_value(self.backend_text, device)
                except:
                    pass
                print(f"使用已保存映射: {model_name} -> {device}")
                return True

            # 构造 device 选项（从界面中读取或使用预设）
            items = []
            try:
                if dpg.does_item_exist('device_combo'):
                    # config 中的 items 字段在不同 DPG 版本中可能不可用，做容错处理
                    try:
                        cfg = dpg.get_item_configuration('device_combo')
                        items = cfg.get('items', []) or []
                    except Exception:
                        try:
                            items = dpg.get_value('device_combo')  # 尝试读取单值作为回退（会失败但捕获）
                        except:
                            items = []
                if not isinstance(items, list):
                    items = []
            except Exception:
                items = []

            if not items:
                items = ['CPU', 'Auto']

            # 创建唯一 tag
            safe_model_tag = str(model_name).replace(" ", "_").replace("/", "_")
            modal_tag = f"modal_model_device_{safe_model_tag}"
            combo_tag = f"modal_device_combo_{safe_model_tag}"

            # 若该 modal 已存在，先删除（避免重复）
            try:
                if dpg.does_item_exist(modal_tag):
                    dpg.delete_item(modal_tag)
            except:
                pass

            # 创建模态窗口
            with dpg.window(label="为模型选择推理设备", modal=True, tag=modal_tag, width=420, height=160):
                dpg.add_text(f"为模型 {model_name} 选择推理设备：")
                dpg.add_separator()
                dpg.add_combo(items=items, default_value=items[0], tag=combo_tag)
                dpg.add_spacer(height=8)
                # 确认并保存按钮
                def _confirm_cb(sender, app_data, user_data=None):
                    try:
                        selected = dpg.get_value(combo_tag)
                    except:
                        selected = items[0] if items else 'CPU'
                    self._on_model_device_confirm(model_name, selected, modal_tag)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="确认并保存", callback=_confirm_cb)
                    dpg.add_button(label="取消", callback=lambda s,a, t=modal_tag: dpg.delete_item(t))

            return True
        except Exception as e:
            print(f"_open_model_device_modal 错误: {e}")
            return False

    def _on_model_device_confirm(self, model_name, device_value, modal_tag=None):
        """处理用户在模态中确认设备选择并保存到 config/model_device_map.yaml"""
        try:
            # 确保配置目录存在
            cfg_dir = project_root / "config"
            try:
                cfg_dir.mkdir(parents=True, exist_ok=True)
            except:
                pass

            map_path = cfg_dir / "model_device_map.yaml"
            mapping = {}

            # 读取现有映射
            if map_path.exists():
                try:
                    if yaml:
                        mapping = yaml.safe_load(map_path.read_text(encoding='utf-8')) or {}
                    else:
                        raw = map_path.read_text(encoding='utf-8').splitlines()
                        for line in raw:
                            if ':' in line:
                                k, v = line.split(':', 1)
                                mapping[k.strip()] = v.strip()
                except Exception:
                    mapping = {}

            # 更新映射并写回（优先使用 yaml 模块）
            mapping[model_name] = device_value
            try:
                if yaml:
                    map_path.write_text(yaml.safe_dump(mapping, allow_unicode=True), encoding='utf-8')
                else:
                    # 回退为简单 key: value 文件
                    content = "\n".join(f"{k}: {v}" for k, v in mapping.items())
                    map_path.write_text(content, encoding='utf-8')
                print(f"已保存模型设备映射: {model_name} -> {device_value}")
            except Exception as e:
                print(f"写入映射文件失败: {e}")

            # 应用到 UI（回填 device_combo 与 backend_text）
            try:
                if dpg.does_item_exist('device_combo'):
                    dpg.set_value('device_combo', device_value)
            except:
                pass
            try:
                dpg.set_value(self.backend_text, device_value)
            except:
                pass

            # 关闭 modal（若有）
            try:
                if modal_tag and dpg.does_item_exist(modal_tag):
                    dpg.delete_item(modal_tag)
            except:
                pass

            return True
        except Exception as e:
            print(f"_on_model_device_confirm 错误: {e}")
            return False
    
    def update_environment_status(self):
        """更新环境状态显示"""
        if not self.environment_manager:
            dpg.set_value(self.env_status_text, "环境状态: 管理器未初始化")
            dpg.configure_item(self.env_status_text, color=[255, 0, 0])
            return
        
        model = dpg.get_value('model_combo')
        if model == '自动选择':
            model = hardware_detector.get_recommended_model_env()
        
        # 确保environment_manager有is_environment_ready方法
        if hasattr(self.environment_manager, 'is_environment_ready'):
            if self.environment_manager.is_environment_ready(model):
                dpg.set_value(self.env_status_text, f"环境状态: {model} 已准备")
                dpg.configure_item(self.env_status_text, color=[0, 255, 0])
            else:
                dpg.set_value(self.env_status_text, f"环境状态: {model} 未准备")
                dpg.configure_item(self.env_status_text, color=[255, 165, 0])
        else:
            dpg.set_value(self.env_status_text, "环境状态: 管理器不可用")
            dpg.configure_item(self.env_status_text, color=[255, 0, 0])
    
    def prepare_environment(self):
        """准备环境"""
        if not self.environment_manager:
            dpg.set_value(self.status_text, "环境管理器未初始化")
            dpg.configure_item(self.status_text, color=[255, 0, 0])
            return
        
        model = dpg.get_value('model_combo')
        if model == '自动选择':
            model = hardware_detector.get_recommended_model_env()
        
        # 确保environment_manager有prepare_environment方法
        if not hasattr(self.environment_manager, 'prepare_environment'):
            dpg.set_value(self.status_text, "环境管理器不支持准备环境")
            dpg.configure_item(self.status_text, color=[255, 0, 0])
            return
        
        # 禁用按钮防止重复点击
        dpg.configure_item('prepare_env_btn', enabled=False)
        dpg.set_value(self.status_text, "正在准备环境...")
        dpg.configure_item(self.status_text, color=[255, 255, 0])
        
        # 在后台线程中准备环境
        def prepare_thread():
            def progress_callback(message, progress):
                # 在主线程中更新UI
                def update_ui():
                    dpg.set_value(self.status_text, message)
                    if progress >= 0:
                        # 这里可以添加进度条显示
                        pass
                
                dpg.split_frame()
                dpg.set_frame_callback(2, update_ui)
            
            try:
                success = self.environment_manager.prepare_environment(model, callback=progress_callback)
                
                # 在主线程中更新最终状态
                def final_update():
                    if success:
                        dpg.set_value(self.status_text, "环境准备完成")
                        dpg.configure_item(self.status_text, color=[0, 255, 0])
                        self.update_environment_status()
                    else:
                        dpg.set_value(self.status_text, "环境准备失败")
                        dpg.configure_item(self.status_text, color=[255, 0, 0])
                    
                    # 重新启用按钮
                    dpg.configure_item('prepare_env_btn', enabled=True)
                
                dpg.split_frame()
                dpg.set_frame_callback(2, final_update)
                
            except Exception as e:
                def error_update():
                    dpg.set_value(self.status_text, f"环境准备错误: {str(e)}")
                    dpg.configure_item(self.status_text, color=[255, 0, 0])
                    dpg.configure_item('prepare_env_btn', enabled=True)
                
                dpg.split_frame()
                dpg.set_frame_callback(2, error_update)
        
        thread = threading.Thread(target=prepare_thread)
        thread.daemon = True
        thread.start()
    
    def on_source_change(self, sender, app_data):
        """数据源改变"""
        # 显示/隐藏文件选择按钮
        if app_data == '图片文件':
            dpg.show_item('select_file_btn')
        else:
            dpg.hide_item('select_file_btn')
    
    def select_image_file(self):
        """选择图片文件"""
        # 这里应该使用文件对话框，但DearPyGui的文件对话框需要额外处理
        # 暂时使用固定文件路径
        self.current_image = "test_image.jpg"
        dpg.set_value(self.details_text, f"已选择文件: {self.current_image}")
    
    def start_inference(self):
        """开始推理"""
        if not self.current_image:
            dpg.set_value(self.status_text, "请先选择文件")
            dpg.configure_item(self.status_text, color=[255, 0, 0])
            return
        
        # 检查环境是否已准备
        model = dpg.get_value('model_combo')
        if model == '自动选择':
            model = hardware_detector.get_recommended_model_env()
        
        # 确保environment_manager存在且有is_environment_ready方法
        if self.environment_manager and hasattr(self.environment_manager, 'is_environment_ready'):
            if not self.environment_manager.is_environment_ready(model):
                dpg.set_value(self.status_text, "请先准备环境")
                dpg.configure_item(self.status_text, color=[255, 165, 0])
                return
        else:
            # 如果环境管理器不可用，继续执行但给出警告
            dpg.set_value(self.status_text, "警告: 环境管理器不可用")
            dpg.configure_item(self.status_text, color=[255, 165, 0])
        
        self.is_running = True
        dpg.set_value(self.status_text, "推理中...")
        dpg.configure_item(self.status_text, color=[255, 255, 0])
        dpg.hide_item('start_btn')
        dpg.show_item('stop_btn')
        
        # 获取参数
        confidence = dpg.get_value('confidence_slider')
        iou = dpg.get_value('iou_slider')
        model = dpg.get_value('model_combo')
        # 由用户在界面选择推理设备；不在此处默认使用GPU
        try:
            selected_device = dpg.get_value('device_combo') if dpg.does_item_exist('device_combo') else 'CPU'
        except:
            selected_device = 'CPU'
        try:
            dpg.set_value(self.backend_text, selected_device)
        except:
            pass
        
        # 异步执行推理
        thread = threading.Thread(
            target=self.run_inference,
            args=(model, self.current_image, confidence, iou)
        )
        thread.daemon = True
        thread.start()
    
    def stop_inference(self):
        """停止推理"""
        self.is_running = False
        model_invoker.stop_all_processes()
        dpg.set_value(self.status_text, "已停止")
        dpg.configure_item(self.status_text, color=[255, 0, 0])
        dpg.show_item('start_btn')
        dpg.hide_item('stop_btn')
    
    def run_inference(self, model_name, image_path, confidence, iou):
        """执行推理任务"""
        try:
            if model_name == '自动选择':
                result, used_env = model_invoker.invoke_best_model(
                    image_path, confidence, iou
                )
            else:
                result = model_invoker.invoke_model(
                    model_name, image_path, confidence, iou
                )
                used_env = model_name
            
            # 更新UI（需要在主线程中执行）
            def update_ui():
                if self.is_running:
                    dpg.set_value(self.status_text, "推理完成")
                    dpg.configure_item(self.status_text, color=[0, 255, 0])
                    dpg.set_value(self.model_text, used_env)
                    dpg.set_value(self.backend_text, result.get('device', 'unknown').upper())
                    
                    # 显示结果
                    total_objects = result.get('total_objects', 0)
                    processing_time = result.get('processing_time', 0)
                    
                    results_text = f"检测到 {total_objects} 个对象\n耗时: {processing_time:.2f}秒\n\n"
                    for i, det in enumerate(result.get('detections', [])):
                        results_text += f"{i+1}. {det['class']} ({det['confidence']:.3f})\n"
                    
                    dpg.set_value(self.results_text, results_text)
                    dpg.set_value(self.details_text, f"推理成功! 使用环境: {used_env}")
                    
                    self.inference_results.append({
                        'timestamp': datetime.now(),
                        'model': used_env,
                        'results': result,
                        'image_path': image_path
                    })
                    
                    dpg.show_item('start_btn')
                    dpg.hide_item('stop_btn')
                    self.is_running = False
            
            dpg.split_frame()
            dpg.set_frame_callback(2, update_ui)
            
        except Exception as e:
            def show_error():
                dpg.set_value(self.status_text, f"错误: {str(e)}")
                dpg.configure_item(self.status_text, color=[255, 0, 0])
                dpg.set_value(self.details_text, f"推理失败: {str(e)}")
                dpg.show_item('start_btn')
                dpg.hide_item('stop_btn')
                self.is_running = False
            
            dpg.split_frame()
            dpg.set_frame_callback(2, show_error)
    
    def save_results(self):
        """保存推理结果"""
        if not self.inference_results:
            dpg.set_value(self.status_text, "没有结果可保存")
            dpg.configure_item(self.status_text, color=[255, 0, 0])
            return
        
        # 这里应该实现文件保存逻辑
        # 暂时只是显示消息
        latest_result = self.inference_results[-1]
        timestamp = latest_result['timestamp'].strftime("%Y%m%d_%H%M%S")
        
        dpg.set_value(self.status_text, f"结果已保存 ({timestamp})")
        dpg.configure_item(self.status_text, color=[0, 200, 255])
        
        # 在实际实现中，这里应该保存图片和JSON结果文件
        print(f"保存结果: {latest_result}")
    
    def run(self):
        """运行应用程序"""
        self.setup_gui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

if __name__ == "__main__":
    app = YOLODeployApp()
    app.run()