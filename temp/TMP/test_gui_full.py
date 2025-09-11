#!/usr/bin/env python3
"""
完整GUI测试程序
"""

import sys
import os
from pathlib import Path

def main():
    """主函数"""
    print("🎯 完整GUI测试程序")
    print("=" * 30)
    
    # 添加项目路径
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    try:
        print("正在导入模块...")
        from app.gui_application import YOLODeployApp
        print("✅ YOLODeployApp 导入成功")
        
        # 创建应用实例并运行
        print("正在创建并运行应用...")
        app = YOLODeployApp()
        print("✅ 应用实例创建成功，正在运行...")
        
        # 运行应用（这将显示GUI界面）
        app.run()
        
        print("🎉 GUI测试完成!")
        
    except Exception as e:
        print(f"❌ GUI测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()