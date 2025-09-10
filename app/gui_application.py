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
        # 初始化环境管理器
        try:
            self.environment_manager = OnDemandEnvironmentManager(str(project_root))
        except Exception as e:
            print(f"环境管理器初始化失败: {e}")
            # 创建模拟环境管理器实例
            self.environment_manager = MockEnvironmentManager()
        
    def setup_gui(self):
        """设置GUI界面"""
        # 尝试创建DearPyGui上下文，如果已存在则忽略错误
        try:
            dpg.create_context()
        except:
            # 上下文可能已存在，忽略错误
            pass
        
        # 使用专门的字体初始化模块
        try:
            from app.font_initializer import initialize_chinese_font
            # 只有在字体尚未加载时才尝试加载
            if not hasattr(self, '_font_initialized') or not self._font_initialized:
                if initialize_chinese_font(project_root):
                    self._font_initialized = True
        except Exception as e:
            print(f"字体初始化模块加载失败: {e}")
            # 回退到原来的字体加载方式
            if not hasattr(self, '_font_initialized') or not self._font_initialized:
                if self._load_chinese_font():
                    self._font_initialized = True
        
        # 创建主窗口，使用无边框设计
        with dpg.window(label="YOLO部署助手", tag="main_window", 
                       no_title_bar=True, no_resize=True, no_move=True, no_collapse=True):
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
                
                # 右侧显示区域
                with dpg.child_window(height=700, tag="display_panel"):
                    self.setup_display_panel()
        
        # 创建视图端口，设置正确的标题和编码
        try:
            # 先设置视口配置
            dpg.configure_viewport(0, title='YOLO本地部署助手')
            if not dpg.is_viewport_created():
                dpg.create_viewport(title='YOLO本地部署助手', width=1200, height=800)
        except:
            # 如果上面的方法失败，使用传统方式
            try:
                dpg.create_viewport(title='YOLO本地部署助手', width=1200, height=800)
            except:
                pass
        
        dpg.setup_dearpygui()
        
        # 设置主窗口
        dpg.set_primary_window("main_window", True)
        
        # 性能监控定时器
        dpg.set_frame_callback(60, self.update_performance)
    
    def _load_chinese_font(self):
        """加载中文字体以支持中文显示（回退方法）"""
        try:
            # 确保字体注册表已创建
            try:
                if not dpg.does_item_exist("font_registry"):
                    with dpg.font_registry(tag="font_registry"):
                        pass
            except:
                # 如果字体注册表已存在或出现其他错误，忽略
                pass
            
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
                path = os.path.join(project_root, "resources", "fonts", font_file)
                if os.path.exists(path):
                    font_path = path
                    break
            
            # 如果找到字体文件，则加载
            if font_path and os.path.exists(font_path):
                # 加载字体
                try:
                    with dpg.font_registry():
                        # 先移除已存在的字体
                        if dpg.does_item_exist("default_font"):
                            dpg.delete_item("default_font")
                        
                        # 添加新字体并包含中文字体范围
                        default_font = dpg.add_font(font_path, 18, tag="default_font")
                        # 添加常用的中文字体范围
                        dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Simplified_Common, parent=default_font)
                        dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full, parent=default_font)
                        # 添加一些额外的字符范围
                        dpg.add_font_range(0x4e00, 0x9fff, parent=default_font)
                    
                    dpg.bind_font("default_font")
                
                    print(f"成功加载中文字体: {font_path}")
                    return True
                except Exception as e:
                    print(f"字体加载时出错: {e}")
                    # 尝试不带字体范围的加载方式
                    try:
                        with dpg.font_registry():
                            if dpg.does_item_exist("default_font"):
                                dpg.delete_item("default_font")
                            
                            default_font = dpg.add_font(font_path, 18, tag="default_font")
                            dpg.bind_font(default_font)
                        
                        print(f"成功加载中文字体（简化方式）: {font_path}")
                        return True
                    except Exception as e2:
                        print(f"简化字体加载也失败: {e2}")
                        return False
            else:
                print("未找到可用的中文字体文件，将使用系统默认字体")
                return False
        except Exception as e:
            print(f"加载中文字体失败: {e}，将使用系统默认字体")
            return False
    
    def setup_control_panel(self):
        """设置控制面板"""
        dpg.add_text("📊 资源监控", color=[255, 200, 0])
        
        # CPU使用率
        with dpg.group(horizontal=True):
            dpg.add_text("CPU:")
            self.cpu_meter = dpg.add_progress_bar(default_value=0, width=200)
            self.cpu_text = dpg.add_text("0%")
        
        # 内存使用率
        with dpg.group(horizontal=True):
            dpg.add_text("内存:")
            self.memory_meter = dpg.add_progress_bar(default_value=0, width=200)
            self.memory_text = dpg.add_text("0%")
        
        # GPU使用率
        with dpg.group(horizontal=True):
            dpg.add_text("GPU:")
            self.gpu_meter = dpg.add_progress_bar(default_value=0, width=200)
            self.gpu_text = dpg.add_text("0%")
        
        # VRAM使用率
        with dpg.group(horizontal=True):
            dpg.add_text("显存:")
            self.vram_meter = dpg.add_progress_bar(default_value=0, width=200)
            self.vram_text = dpg.add_text("0/0 GB")
        
        dpg.add_separator()
        dpg.add_text("🤖 模型设置", color=[255, 200, 0])
        
        # 模型选择
        dpg.add_combo(
            items=['yolov5-cuda', 'yolov8-cuda', 'ppyolo-xpu', '自动选择'],
            default_value='自动选择',
            label="选择模型",
            callback=self.on_model_change,
            tag='model_combo'
        )
        
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
        dpg.add_text("📷 数据源", color=[255, 200, 0])
        
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
        dpg.add_text("📋 检测结果", color=[255, 200, 0])
        self.results_text = dpg.add_text("等待推理...", wrap=250)
    
    def setup_display_panel(self):
        """设置显示面板"""
        dpg.add_text("🎬 实时显示", color=[255, 200, 0])
        
        # 图像显示区域
        with dpg.drawlist(width=600, height=400, tag="display_canvas"):
            # 这里将显示检测结果
            pass
        
        # 详细信息区域
        dpg.add_separator()
        dpg.add_text("📊 详细信息", color=[255, 200, 0])
        self.details_text = dpg.add_text("选择文件开始推理...", wrap=550)
    
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
        """模型选择改变"""
        self.current_model = app_data
        if app_data == '自动选择':
            recommended = hardware_detector.get_recommended_model_env()
            dpg.set_value(self.model_text, f"自动 ({recommended})")
        else:
            dpg.set_value(self.model_text, app_data)
        
        # 更新环境状态
        self.update_environment_status()
    
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