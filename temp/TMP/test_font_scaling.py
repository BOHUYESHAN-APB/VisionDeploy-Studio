#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体动态缩放测试脚本
用于验证在不同窗口尺寸下字体是否正确缩放
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.gui_application import YOLODeployApp

def test_font_scaling():
    """测试字体缩放功能"""
    print("=== 字体动态缩放测试 ===")
    
    # 创建应用实例
    app = YOLODeployApp()
    
    # 测试不同窗口宽度下的字体缩放计算
    test_widths = [1280, 1920, 2560, 3440, 3840]  # 常见显示器宽度，包括4K
    
    print(f"基础字体大小: {app.base_font_size}px")
    print(f"屏幕DPI: {app.screen_dpi}")
    print(f"DPI缩放因子: {app.dpi_scale:.2f}")
    print()
    
    for width in test_widths:
        scale = app._calculate_font_scale(width)
        font_size = int(app.base_font_size * scale)
        resolution_type = {
            1280: "HD+(小窗口)",
            1920: "1080p(标准)", 
            2560: "2K/1440p",
            3440: "3440x1440(超宽)",
            3840: "4K/2160p"
        }.get(width, f"{width}px")
        print(f"{resolution_type:15} 窗口宽度 {width}px: 缩放因子 {scale:.2f}, 字体大小 {font_size}px")
    
    print()
    print("启动GUI进行实际测试...")
    print("提示: 拖动窗口边缘改变大小，观察字体是否自动调整")
    print("提示: 可使用左侧面板底部的字体调试滑块手动测试不同字体大小")
    
    # 运行GUI
    app.run()

if __name__ == "__main__":
    test_font_scaling()
