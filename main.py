#!/usr/bin/env python3
"""
VisionDeploy Studio - 主应用程序
支持多硬件后端和模型环境的按需部署和推理
"""

import sys
import os
import time
import locale
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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

def setup_environment():
    """设置应用程序环境"""
    print("=" * 60)
    print("VisionDeploy Studio - 环境初始化")
    print("=" * 60)
    
    try:
        # 尝试导入核心模块
        try:
            from core.on_demand_environment_manager import OnDemandEnvironmentManager
            from core.hardware_detector import hardware_detector
            environment_manager = OnDemandEnvironmentManager(str(project_root))
        except ImportError as e:
            print(f"❌ 核心模块导入失败: {e}")
            print("请确保已安装所需依赖: pip install -r requirements.txt")
            return False
        
        # 检测网络环境
        print("🔍 检测网络环境...")
        # 简化网络检测
        is_china = True  # 默认使用国内源
        print(f"   网络环境: {'国内' if is_china else '国际'}")
        
        # 检测硬件
        print("🔍 检测硬件配置...")
        # 修复：使用正确的方法名
        try:
            hardware_info = hardware_detector.detect_all_hardware()
            recommended_backend = hardware_detector.get_recommended_backend()
            recommended_env = hardware_detector.get_recommended_model_env()
            
            print(f"   NVIDIA GPU: {'✅' if hardware_info['nvidia_gpu'] else '❌'}")
            print(f"   AMD GPU: {'✅' if hardware_info['amd_gpu'] else '❌'}")
            print(f"   Intel GPU: {'✅' if hardware_info['intel_gpu'] else '❌'}")
            print(f"   Intel AI能力: {'✅' if hardware_info['intel_ai_capable'] else '❌'}")
            print(f"   CUDA可用: {'✅' if hardware_info['cuda_available'] else '❌'}")
            print(f"   推荐后端: {recommended_backend.upper()}")
            print(f"   推荐环境: {recommended_env}")
        except Exception as e:
            print(f"   硬件检测失败: {e}")
            recommended_env = "yolov5-cuda"  # 默认环境
            print(f"   推荐环境: {recommended_env}")
        
        # 显示可用环境
        print("🛠️  可用环境:")
        try:
            environments = environment_manager.list_available_environments()
            for env in environments:
                status = "✅ 已准备" if env['ready'] else "⏳ 未准备"
                print(f"   {env['name']} (Python {env['python_version']}) - {status}")
        except Exception as e:
            print(f"   环境列表获取失败: {e}")
        
        print("✅ 环境初始化完成!")
        return True
            
    except Exception as e:
        print(f"❌ 环境初始化失败: {e}")
        print("请检查网络连接或手动设置环境")
        print("应用程序将继续运行，但部分功能可能受限")
        return True  # 仍然继续运行，提供基础功能

def start_application():
    """启动主应用程序"""
    print("\n" + "=" * 60)
    print("🚀 启动VisionDeploy Studio")
    print("=" * 60)
    
    # 重新获取项目根目录
    current_project_root = Path(__file__).parent
    
    try:
        # 检查是否安装了DearPyGui
        try:
            import dearpygui.dearpygui as dpg
        except ImportError:
            print("❌ 未安装DearPyGui，正在安装...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "dearpygui"])
            import dearpygui.dearpygui as dpg
            print("✅ DearPyGui安装完成")
        
        # 在启动GUI之前加载中文字体
        try:
            # 确保DearPyGui上下文已创建
            try:
                dpg.create_context()
            except:
                # 上下文可能已存在，忽略错误
                pass
            
            # 加载中文字体
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
            
            font_path = None
            for font_file in font_files:
                path = current_project_root / "resources" / "fonts" / font_file
                if path.exists():
                    font_path = str(path)
                    break
            
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
                        
                        # 添加新字体并包含中文字体范围
                        default_font = dpg.add_font(font_path, 18, tag="default_font")
                        # 添加常用的中文字体范围
                        dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Simplified_Common, parent=default_font)
                        dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full, parent=default_font)
                        # 添加一些额外的字符范围
                        dpg.add_font_range(0x4e00, 0x9fff, parent=default_font)  # CJK统一汉字区块
                    
                    dpg.bind_font("default_font")
                    print(f"✅ 成功加载中文字体: {font_path}")
                except Exception as e:
                    print(f"⚠️ 字体加载时出错: {e}")
                    # 尝试不带字体范围的加载方式
                    try:
                        with dpg.font_registry():
                            if dpg.does_item_exist("default_font"):
                                dpg.delete_item("default_font")
                            
                            default_font = dpg.add_font(font_path, 18, tag="default_font")
                            dpg.bind_font(default_font)
                        
                        print(f"✅ 成功加载中文字体（简化方式）: {font_path}")
                    except Exception as e2:
                        print(f"⚠️ 简化字体加载也失败: {e2}")
        except Exception as e:
            print(f"⚠️ 加载中文字体时出错: {e}")
        
        # 启动GUI应用
        try:
            # 修复相对导入问题
            sys.path.insert(0, str(current_project_root))
            from app.gui_application import YOLODeployApp
        except ImportError:
            # 添加项目根目录到Python路径
            sys.path.insert(0, str(current_project_root))
            from app.gui_application import YOLODeployApp
        
        app = YOLODeployApp()
        app.run()
        
    except Exception as e:
        print(f"❌ 应用程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")
        return False

def main():
    """主函数"""
    print("VisionDeploy Studio v1.0")
    print("MIT License - 版权所有 (c) 2025")
    print()
    
    # 环境初始化
    if not setup_environment():
        print("❌ 初始化失败，无法启动应用程序")
        input("按回车键退出...")
        return
    
    # 启动主应用
    try:
        start_application()
    except KeyboardInterrupt:
        print("\n👋 用户中断，退出应用程序")
    except Exception as e:
        print(f"\n❌ 应用程序异常: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main()