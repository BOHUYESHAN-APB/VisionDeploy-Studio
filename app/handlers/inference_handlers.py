"""
推理处理模块 - VisionDeploy Studio
包含推理相关的处理函数
"""

import os
import dearpygui.dearpygui as dpg
import cv2  # 添加cv2导入
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

class InferenceHandlers:
    """推理处理类，包含推理相关的处理函数"""
    
    def __init__(self, app):
        """初始化推理处理
        
        Args:
            app: 主应用程序实例
        """
        self.app = app
        self.logger = app.logger
    
    def select_input_source(self, sender, value):
        """选择输入源
        
        Args:
            sender: 发送者
            value: 选中的值
        """
        if value == "摄像头":
            # 显示摄像头选项，隐藏文件选项
            dpg.show_item("camera_options")
            dpg.hide_item("file_options")
            
            # 设置输入源
            self.app.inference_engine.set_input_source("camera", dpg.get_value("camera_id_input"))
        else:
            # 隐藏摄像头选项，显示文件选项
            dpg.hide_item("camera_options")
            dpg.show_item("file_options")
            
            # 设置输入源类型
            source_type = "image" if value == "图片文件" else "video"
            self.app.inference_engine.set_input_source(source_type, None)
    
    def set_camera_id(self, sender, value):
        """设置摄像头ID
        
        Args:
            sender: 发送者
            value: 摄像头ID
        """
        self.app.inference_engine.set_input_source("camera", value)
    
    def select_input_file(self):
        """选择输入文件"""
        # 在实际应用中，这里应该打开一个文件选择对话框
        # 这里简化为直接设置一个示例文件路径
        input_source = dpg.get_value("input_source_radio")
        
        if input_source == "图片文件":
            file_path = "example.jpg"  # 示例路径
            self.app.inference_engine.set_input_source("image", file_path)
            dpg.set_value("selected_file_text", f"已选择: {file_path}")
        else:  # 视频文件
            file_path = "example.mp4"  # 示例路径
            self.app.inference_engine.set_input_source("video", file_path)
            dpg.set_value("selected_file_text", f"已选择: {file_path}")
    
    def set_confidence_threshold(self, sender, value):
        """设置置信度阈值
        
        Args:
            sender: 发送者
            value: 阈值
        """
        self.app.inference_engine.set_inference_params(confidence_threshold=value)
    
    def set_iou_threshold(self, sender, value):
        """设置IOU阈值
        
        Args:
            sender: 发送者
            value: 阈值
        """
        self.app.inference_engine.set_inference_params(iou_threshold=value)
    
    def start_inference(self):
        """开始推理"""
        # 检查是否选择了模型
        if not self.app.inference_engine.current_model:
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="no_model_error_window"):
                dpg.add_text("请先选择一个模型")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("no_model_error_window"))
            return
        
        # 检查是否选择了输入源
        input_source = dpg.get_value("input_source_radio")
        if input_source != "摄像头" and not self.app.inference_engine.input_file:
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="no_input_error_window"):
                dpg.add_text("请先选择输入文件")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("no_input_error_window"))
            return
        
        # 设置输出选项
        save_results = dpg.get_value("save_results_checkbox")
        output_path = None
        if save_results:
            # 在实际应用中，这里应该让用户选择输出路径
            output_path = os.path.join(self.app.base_dir, "output")
            os.makedirs(output_path, exist_ok=True)
        
        self.app.inference_engine.set_output_options(save_results, output_path)
        
        # 开始推理
        success = self.app.inference_engine.start_inference(self._inference_result_callback)
        
        if success:
            # 更新UI状态
            dpg.configure_item("start_inference_button", enabled=False)
            dpg.configure_item("stop_inference_button", enabled=True)
            dpg.set_value("inference_status_text", "正在推理...")
        else:
            # 显示错误提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="inference_error_window"):
                dpg.add_text("启动推理失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("inference_error_window"))
    
    def stop_inference(self):
        """停止推理"""
        success = self.app.inference_engine.stop_inference()
        
        if success:
            # 更新UI状态
            dpg.configure_item("start_inference_button", enabled=True)
            dpg.configure_item("stop_inference_button", enabled=False)
            dpg.set_value("inference_status_text", "推理已停止")
        else:
            # 显示错误提示
            with dpg.window(label="错误", modal=True, width=300, height=100, tag="inference_stop_error_window"):
                dpg.add_text("停止推理失败")
                dpg.add_button(label="确定", callback=lambda: dpg.delete_item("inference_stop_error_window"))
    
    def _inference_result_callback(self, frame, results, fps, inference_time, progress=None):
        """推理结果回调
        
        Args:
            frame: 带有结果的帧
            results: 推理结果
            fps: 每秒帧数
            inference_time: 推理时间（毫秒）
            progress: 进度（仅视频推理时提供）
        """
        # 更新推理统计信息
        if dpg.does_item_exist("fps_text"):
            dpg.set_value("fps_text", f"FPS: {fps:.2f}")
        
        if dpg.does_item_exist("inference_time_text"):
            dpg.set_value("inference_time_text", f"推理时间: {inference_time:.2f} ms")
        
        if dpg.does_item_exist("detected_objects_text"):
            dpg.set_value("detected_objects_text", f"检测到的对象: {len(results)}")
        
        # 更新推理图像
        if dpg.does_item_exist("inference_texture"):
            # 转换图像格式
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if 'cv2' in globals() and frame is not None else frame
            frame_flipped = cv2.flip(frame_rgb, 0) if 'cv2' in globals() and frame_rgb is not None else frame_rgb
            
            # 更新纹理
            dpg.set_value("inference_texture", frame_flipped)
        
        # 更新进度（如果是视频推理）
        if progress is not None and dpg.does_item_exist("inference_progress_bar"):
            dpg.set_value("inference_progress_bar", progress)