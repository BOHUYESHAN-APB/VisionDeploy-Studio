"""
主入口点 - VisionDeploy Studio
负责启动应用程序
"""

import os
import sys
import logging

# 确保能正确导入app模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main_application import MainApplication

def main():
    """主函数"""
    try:
        # 创建主应用程序实例
        app = MainApplication()
        
        # 运行应用程序
        app.run()
    except Exception as e:
        logging.error(f"应用程序运行时出错: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()