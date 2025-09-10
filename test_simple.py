#!/usr/bin/env python3
"""
简单测试程序
"""

import sys
import os
from pathlib import Path

def main():
    """主函数"""
    print("🎯 简单测试程序")
    print("=" * 30)
    
    # 添加项目路径
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    try:
        print("正在导入模块...")
        from app.application_core import ApplicationCore
        print("✅ ApplicationCore 导入成功")
        
        # 创建核心应用
        print("正在创建核心应用...")
        core = ApplicationCore(str(project_root))
        print("✅ 核心应用创建成功")
        
        # 初始化日志
        print("正在初始化日志...")
        core.init_logging()
        print("✅ 日志初始化成功")
        
        # 加载配置
        print("正在加载配置...")
        core.load_config()
        print("✅ 配置加载成功")
        
        print("🎉 测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()