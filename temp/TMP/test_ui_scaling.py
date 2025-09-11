#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试UI缩放功能
验证字体和UI组件在不同窗口大小下的自适应缩放
"""

import dearpygui.dearpygui as dpg
import os
import sys
from pathlib import Path

# 添加app目录到路径
sys.path.append(str(Path(__file__).parent / "app"))

from gui_application import YOLODeployApp

def test_scaling_behavior():
    """测试缩放行为"""
    print("=== UI缩放功能测试（基于窗口比例）===")
    
    # 创建应用实例
    app = YOLODeployApp()
    
    # 测试不同分辨率和比例的缩放
    test_resolutions = [
        # (宽度, 高度, 描述)
        (1280, 720, "HD 16:9"),
        (1920, 1080, "Full HD 16:9 (基准)"),
        (2560, 1440, "2K 16:9"),
        (3840, 2160, "4K 16:9"),
        (1920, 1200, "16:10 比例"),
        (2560, 1600, "2K 16:10"),
        (1600, 1200, "4:3 比例"),
        (2400, 600, "超宽屏 4:1"),
        (800, 1200, "竖屏 2:3"),
        (1200, 800, "小窗口"),
    ]
    
    print("\n字体缩放测试（基于窗口比例）:")
    for width, height, desc in test_resolutions:
        scale = app._calculate_font_scale_for_resolution(width, height)
        base_font_size = 16
        scaled_font_size = int(base_font_size * scale)
        ratio = width / height if height > 0 else 1.0
        
        print(f"{desc}: {width}x{height} (比例: {ratio:.2f}) -> 缩放因子: {scale:.2f} -> 字体大小: {scaled_font_size}px")
    
    print("\nUI组件缩放测试:")
    for width, height, desc in test_resolutions:
        scale = app._calculate_font_scale_for_resolution(width, height)
        ui_scale = max(0.8, min(2.0, scale * 0.9 + 0.1))
        
        button_width = int(app.base_button_width * ui_scale)
        slider_width = int(app.base_slider_width * ui_scale)
        
        print(f"{desc}: UI缩放: {ui_scale:.2f} -> 按钮: {button_width}px, 滑动条: {slider_width}px")
    
    print("\n=== 测试完成 ===")
    
    # 启动GUI进行实际测试
    print("\n启动GUI进行实际测试...")
    print("请尝试以下操作:")
    print("1. 调整为16:9比例窗口（如1920x1080）")
    print("2. 调整为16:10比例窗口（如1920x1200）") 
    print("3. 调整为超宽屏比例（如2400x800）")
    print("4. 调整为竖屏比例（如800x1200）")
    print("5. 观察字体缩放的变化和合理性")
    
    app.run()

def add_scaling_calculation_method():
    """为YOLODeployApp添加用于测试的缩放计算方法"""
    def _calculate_font_scale_for_resolution(self, width, height):
        """计算指定分辨率的字体缩放因子"""
        return self._calculate_font_scale(width, height)
    
    # 动态添加方法到类
    YOLODeployApp._calculate_font_scale_for_resolution = _calculate_font_scale_for_resolution

if __name__ == "__main__":
    # 添加测试方法
    add_scaling_calculation_method()
    
    # 运行测试
    test_scaling_behavior()
