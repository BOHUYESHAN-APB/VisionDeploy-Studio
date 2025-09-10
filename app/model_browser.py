import dearpygui.dearpygui as dpg
from pathlib import Path
from core.model_manager import model_manager

class ModelBrowser:
    """模型浏览器 - 类似LM Studio的界面"""
    
    def __init__(self):
        self.selected_model = None
        self.available_models = []
        self.downloaded_models = []
        
    def create_window(self):
        """创建模型浏览器窗口"""
        with dpg.window(label="模型浏览器", width=800, height=600):
            
            # 顶部工具栏
            with dpg.group(horizontal=True):
                dpg.add_button(label="刷新", callback=self.refresh_models)
                dpg.add_button(label="下载选中", callback=self.download_selected)
                dpg.add_combo(["全部", "PyTorch", "ONNX", "PaddlePaddle"], 
                             default_value="全部", label="框架过滤")
            
            # 分割视图
            with dpg.child_window(width=300, height=500):
                dpg.add_text("📦 可用模型")
                self.model_list = dpg.add_listbox([], num_items=10, callback=self.on_model_selected)
            
            with dpg.child_window(width=450, height=500, pos=(310, 40)):
                dpg.add_text("模型详情")
                self.details_text = dpg.add_text("选择模型查看详情", wrap=400)
                
                with dpg.group(horizontal=True):
                    dpg.add_button(label="下载", callback=self.download_current)
                    dpg.add_button(label="运行", callback=self.run_model)
            
            # 下载进度
            dpg.add_progress_bar(default_value=0, label="下载进度", overlay="等待下载")
            self.progress_bar = dpg.last_item()
            
            # 初始化加载模型
            self.refresh_models()
    
    def refresh_models(self):
        """刷新模型列表"""
        self.available_models = model_manager.discover_models()
        self.downloaded_models = model_manager.list_downloaded_models()
        
        model_names = [f"{m['name']} ({m['framework']}) - {m['size']}" 
                      for m in self.available_models]
        
        dpg.configure_item(self.model_list, items=model_names)
    
    def on_model_selected(self, sender, app_data):
        """模型选择回调"""
        if app_data >= 0 and app_data < len(self.available_models):
            self.selected_model = self.available_models[app_data]
            self.update_details()
    
    def update_details(self):
        """更新模型详情"""
        if not self.selected_model:
            return
            
        details = f"""
名称: {self.selected_model['name']}
框架: {self.selected_model['framework']}
大小: {self.selected_model['size']}
任务: {', '.join(self.selected_model['tasks'])}

描述: 这是一个预训练的{self.selected_model['framework'].upper()}模型，
适用于{self.selected_model['tasks'][0]}任务。
        """
        
        dpg.configure_item(self.details_text, default_value=details)
    
    def download_current(self):
        """下载当前选中的模型"""
        if not self.selected_model:
            dpg.configure_item(self.progress_bar, overlay="请先选择模型")
            return
            
        dpg.configure_item(self.progress_bar, overlay="开始下载...")
        
        # 模拟下载进度更新
        def update_progress():
            for i in range(101):
                dpg.configure_item(self.progress_bar, default_value=i/100)
                dpg.configure_item(self.progress_bar, overlay=f"下载中... {i}%")
                dpg.render_dearpygui_frame()
                # 实际下载逻辑会在这里
        
        # 在实际实现中，这里会调用model_manager.download_model
        # 并使用回调更新进度条
        dpg.configure_item(self.progress_bar, overlay="下载完成")
        dpg.configure_item(self.progress_bar, default_value=1.0)
        
        self.refresh_models()
    
    def download_selected(self):
        """下载选中的模型"""
        self.download_current()
    
    def run_model(self):
        """运行选中的模型"""
        if not self.selected_model:
            return
            
        model_path = model_manager.get_model_path(self.selected_model['name'])
        if model_path:
            print(f"🚀 运行模型: {self.selected_model['name']}")
            # 这里会调用模型推理引擎
        else:
            print("❌ 模型未下载，请先下载")

# 创建全局实例
model_browser = ModelBrowser()