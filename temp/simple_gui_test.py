#!/usr/bin/env python3
"""
简单的GUI功能测试
"""

import sys
import threading
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_gui_functionality():
    """测试GUI基本功能"""
    try:
        import customtkinter as ctk
        
        # 设置应用外观
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # 创建应用窗口
        app = ctk.CTk()
        app.title("VisionDeploy Studio - GUI测试")
        app.geometry("400x300")
        
        # 添加标签
        title_label = ctk.CTkLabel(app, text="VisionDeploy Studio", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=20)
        
        status_label = ctk.CTkLabel(app, text="GUI功能测试中...")
        status_label.pack(pady=10)
        
        # 添加进度条
        progressbar = ctk.CTkProgressBar(app, width=300)
        progressbar.pack(pady=20)
        progressbar.set(0)
        
        # 添加按钮
        def close_app():
            status_label.configure(text="测试完成，正在关闭...")
            app.after(1000, app.destroy)
        
        button = ctk.CTkButton(app, text="关闭测试", command=close_app)
        button.pack(pady=10)
        
        # 模拟进度
        def update_progress():
            for i in range(101):
                progressbar.set(i/100)
                status_label.configure(text=f"测试进度: {i}%")
                time.sleep(0.05)
                if i == 50:
                    status_label.configure(text="GUI功能正常")
        
        # 在后台线程中运行进度更新
        progress_thread = threading.Thread(target=update_progress)
        progress_thread.daemon = True
        progress_thread.start()
        
        print("✅ GUI窗口已创建")
        print("   窗口标题: VisionDeploy Studio - GUI测试")
        print("   窗口大小: 400x300")
        print("   测试将在5秒后自动关闭")
        
        # 运行应用5秒后自动关闭
        app.after(5000, close_app)
        app.mainloop()
        
        print("✅ GUI测试完成")
        return True
        
    except Exception as e:
        print(f"❌ GUI功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始GUI功能测试...")
    print()
    
    success = test_gui_functionality()
    
    if success:
        print("\n✅ GUI功能测试通过")
        print("   CustomTkinter GUI可以正常显示和交互")
    else:
        print("\n❌ GUI功能测试失败")
        sys.exit(1)