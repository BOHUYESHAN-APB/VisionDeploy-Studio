#!/usr/bin/env python3
"""
简单的GUI测试脚本
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_gui_imports():
    """测试GUI相关模块是否能正常导入"""
    try:
        import customtkinter as ctk
        print("✅ CustomTkinter 导入成功")
        print(f"   版本: {ctk.__version__}")
    except Exception as e:
        print(f"❌ CustomTkinter 导入失败: {e}")
        return False
    
    try:
        from app.gui_ctk import MainApp
        print("✅ GUI CTk 主应用导入成功")
    except Exception as e:
        print(f"❌ GUI CTk 主应用导入失败: {e}")
        return False
        
    try:
        from app.hf_browser import search_models, get_model_metadata
        print("✅ HF浏览器模块导入成功")
    except Exception as e:
        print(f"❌ HF浏览器模块导入失败: {e}")
        return False
        
    return True

def test_simple_gui():
    """测试创建一个简单的GUI窗口"""
    try:
        import customtkinter as ctk
        
        # 创建一个简单的窗口
        app = ctk.CTk()
        app.title("GUI测试")
        app.geometry("300x200")
        
        label = ctk.CTkLabel(app, text="GUI测试成功!")
        label.pack(pady=20)
        
        button = ctk.CTkButton(app, text="关闭", command=app.destroy)
        button.pack(pady=10)
        
        print("✅ 简单GUI窗口创建成功")
        print("   如果看到窗口，请手动关闭它")
        
        # 运行GUI（这会阻塞直到窗口关闭）
        app.mainloop()
        
        print("✅ GUI测试完成")
        return True
    except Exception as e:
        print(f"❌ 简单GUI测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始GUI测试...")
    print()
    
    # 测试导入
    if not test_gui_imports():
        print("\n❌ GUI导入测试失败")
        sys.exit(1)
    
    print()
    
    # 测试简单GUI
    if not test_simple_gui():
        print("\n❌ 简单GUI测试失败")
        sys.exit(1)
    
    print("\n✅ 所有GUI测试通过")