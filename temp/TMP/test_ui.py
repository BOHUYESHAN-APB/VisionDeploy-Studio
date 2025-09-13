#!/usr/bin/env python3
"""
UI测试程序
"""

import sys
import os
from pathlib import Path

def main():
    """主函数"""
    print("🎯 UI测试程序")
    print("=" * 30)
    
    # 添加项目路径
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    try:
        print("正在导入模块...")
        # DearPyGui usage archived; see legacy_dearpygui/ for original tests
        print("DearPyGui tests have been archived to legacy_dearpygui/")

    # The remainder of the original test has been archived.
        
        from app.application_ui import ApplicationUI
        print("✅ ApplicationUI 导入成功")
        
        # 创建简单的UI测试
        print("正在创建UI...")
        dpg.create_context()
        
        # 创建窗口
        with dpg.window(label="测试窗口", width=400, height=300):
            dpg.add_text("Hello, VisionDeploy Studio!")
            dpg.add_button(label="关闭", callback=lambda: dpg.stop_dearpygui())
        
        # 设置主窗口
        dpg.set_primary_window(dpg.last_container(), True)
        
        # 创建视图端口
        dpg.create_viewport(title='UI测试', width=400, height=300)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        
        print("✅ UI创建成功，正在运行...")
        
        # 运行主循环
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
        
        # 清理
        dpg.destroy_context()
        print("✅ UI测试完成!")
        
    except Exception as e:
        print(f"❌ UI测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()