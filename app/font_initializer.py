"""
字体初始化模块 - VisionDeploy Studio
专门处理中文字体的加载和初始化
"""

import os
import dearpygui.dearpygui as dpg
from pathlib import Path

# 添加一个全局变量来跟踪字体是否已加载
_font_loaded = False

def initialize_chinese_font(project_root):
    """初始化中文字体
    
    Args:
        project_root: 项目根目录路径
        
    Returns:
        bool: 是否成功加载字体
    """
    global _font_loaded
    
    # 如果字体已经加载过，直接返回True
    if _font_loaded:
        return True
    
    # 初始化font_path变量
    font_path = None
    
    try:
        # 确保DearPyGui上下文已创建
        try:
            dpg.create_context()
        except:
            # 上下文可能已存在，忽略错误
            pass
        
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
        for font_file in font_files:
            path = os.path.join(project_root, "resources", "fonts", font_file)
            if os.path.exists(path):
                font_path = path
                break
        
        # 如果找到字体文件，则加载
        if font_path and os.path.exists(font_path):
            # 先移除已存在的字体
            if dpg.does_item_exist("default_font"):
                dpg.delete_item("default_font")
            
            # 添加新字体并包含中文字体范围
            with dpg.font_registry():
                default_font = dpg.add_font(font_path, 18, tag="default_font")
                # 添加常用的中文字体范围
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Simplified_Common, parent=default_font)
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full, parent=default_font)
                # 添加一些额外的字符范围
                dpg.add_font_range(0x4e00, 0x9fff, parent=default_font)
            
            dpg.bind_font("default_font")
            
            print(f"✅ 成功加载中文字体: {font_path}")
            _font_loaded = True  # 标记字体已加载
            return True
        else:
            print("⚠️ 未找到可用的中文字体文件")
            return False
            
    except Exception as e:
        print(f"⚠️ 加载中文字体时出错: {e}")
        # 尝试不带字体范围的加载方式
        try:
            if font_path and os.path.exists(font_path):
                with dpg.font_registry():
                    if dpg.does_item_exist("default_font"):
                        dpg.delete_item("default_font")
                    
                    default_font = dpg.add_font(font_path, 18, tag="default_font")
                    dpg.bind_font(default_font)
                
                print(f"✅ 成功加载中文字体（简化方式）: {font_path}")
                _font_loaded = True  # 标记字体已加载
                return True
        except Exception as e2:
            print(f"⚠️ 简化字体加载也失败: {e2}")
            return False
    
    return False