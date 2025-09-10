#!/usr/bin/env python3
"""
VisionDeploy Studio 启动器
AI模型部署平台 - 专注于计算机视觉模型
"""

import sys
import os
import locale
from pathlib import Path

def check_dependencies():
    """检查所需依赖"""
    try:
        import dearpygui.dearpygui as dpg
        print("✅ DearPyGUI 已安装")
        return True
    except ImportError:
        print("❌ DearPyGUI 未安装")
        print("正在安装所需依赖...")
        
        try:
            import subprocess
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "dearpygui", "psutil", "requests", "Pillow"
            ])
            print("✅ 依赖安装完成")
            return True
        except Exception as e:
            print(f"❌ 依赖安装失败: {e}")
            return False

def setup_environment():
    """设置运行环境"""
    # 设置系统编码以支持中文
    try:
        # 设置控制台编码为UTF-8
        if hasattr(sys.stdout, 'reconfigure') and callable(getattr(sys.stdout, 'reconfigure', None)):
            if sys.stdout.encoding != 'utf-8':
                sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure') and callable(getattr(sys.stderr, 'reconfigure', None)):
            if sys.stderr.encoding != 'utf-8':
                sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass
    
    # 设置系统区域以支持中文
    try:
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Chinese_China.936')
        except:
            pass
    
    print("=" * 50)
    print("🚀 VisionDeploy Studio - 环境准备")
    print("=" * 50)
    
    # 添加项目路径
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # 检查资源目录
    resources_dir = project_root / "resources"
    resources_dir.mkdir(exist_ok=True)
    
    print("✅ 环境设置完成")

def load_chinese_fonts():
    """加载中文字体"""
    try:
        import dearpygui.dearpygui as dpg
        project_root = Path(__file__).parent
        
        # 尝试创建DearPyGui上下文，如果已存在则忽略错误
        try:
            dpg.create_context()
        except:
            # 上下文可能已存在，忽略错误
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
            "MiSans-Heavy.otf"
        ]
        
        # 查找可用的字体文件
        font_path = None
        for font_file in font_files:
            path = project_root / "resources" / "fonts" / font_file
            if path.exists():
                font_path = str(path)
                break
        
        # 如果找到字体文件，则加载
        if font_path:
            # 确保字体注册表已创建
            try:
                if not dpg.does_item_exist("font_registry"):
                    with dpg.font_registry(tag="font_registry"):
                        pass
            except:
                # 如果字体注册表已存在或出现其他错误，忽略
                pass
            
            try:
                with dpg.font_registry():
                    # 先移除已存在的字体
                    if dpg.does_item_exist("default_font"):
                        dpg.delete_item("default_font")
                    
                    # 添加新字体
                    default_font = dpg.add_font(font_path, 18, tag="default_font")
                    dpg.bind_font(default_font)
                
                print(f"✅ 成功加载中文字体: {font_path}")
                return True
            except Exception as e:
                print(f"⚠️ 字体加载时出错: {e}")
                return False
        else:
            print("⚠️ 未找到可用的中文字体文件")
            return False
    except Exception as e:
        print(f"⚠️ 加载中文字体失败: {e}")
        return False

def main():
    """主函数"""
    print("🎯 VisionDeploy Studio - AI模型部署平台")
    print("📝 专注于计算机视觉模型的本地部署")
    print("=" * 50)
    
    # 设置环境
    setup_environment()
    
    # 加载中文字体
    load_chinese_fonts()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 请手动安装依赖: pip install dearpygui psutil requests Pillow")
        input("按回车键退出...")
        return
    
    # 启动应用程序
    try:
        # 修复导入问题
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        # 确保使用正确的导入路径
        if 'app' not in sys.modules:
            import app
        
        from app.main_application import MainApplication
        print("\n✅ 启动 VisionDeploy Studio...")
        
        # 创建并运行主应用程序
        app = MainApplication()
        app.run()
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()