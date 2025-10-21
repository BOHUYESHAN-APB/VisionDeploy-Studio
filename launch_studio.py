#!/usr/bin/env python3
"""
VisionDeploy Studio 启动器
AI模型部署平台 - 专注于计算机视觉模型
"""

import sys
import os
import locale
from pathlib import Path
import argparse
import logging

# setup minimal logger early so we can capture messages during startup
def configure_logging(level: str = 'INFO'):
    try:
        lvl = getattr(logging, level.upper(), logging.INFO)
    except Exception:
        lvl = logging.INFO
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    logfile = logs_dir / 'visiondeploy.log'
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler(logfile, encoding='utf-8')]
    logging.basicConfig(level=lvl, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=handlers)
    logging.getLogger().info(f"日志已配置 level={level} -> {logfile}")

def check_dependencies():
    """检查并按需安装所需依赖（按模块导入检测，按需 pip 安装）"""
    # 映射：pip 包名 -> 导入检测函数/模块名
    checks = {
        "dearpygui": ("dearpygui.dearpygui", None),
        "psutil": ("psutil", None),
        "requests": ("requests", None),
        "Pillow": ("PIL", "Pillow"),
        "gputil": ("GPUtil", None),
        "PyYAML": ("yaml", "pyyaml"),
        "pynvml": ("pynvml", None),
    }
    # Windows 特有建议包
    try:
        if os.name == 'nt':
            checks["wmi"] = ("wmi", None)
    except Exception:
        pass

    missing = []
    for pkg, (module_name, alt_name) in checks.items():
        try:
            __import__(module_name)
        except Exception:
            # 有些包在 pip 名称和 import 名不同，优先记录 pip 包名 if provided
            if alt_name:
                missing.append(alt_name)
            else:
                missing.append(pkg)

    if not missing:
        print("✅ 所需依赖已安装")
        return True

    print(f"⚠️ 检测到缺失依赖: {', '.join(missing)}")
    print("正在尝试通过 pip 安装缺失依赖...")

    try:
        import subprocess
        # 使用 --upgrade 保证获取最新兼容版本
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + missing
        print("执行命令:", " ".join(cmd))
        subprocess.check_call(cmd)
    except Exception as e:
        print(f"❌ 自动安装依赖失败: {e}")
        return False

    # 再次验证导入
    failed_after_install = []
    for pkg, (module_name, alt_name) in checks.items():
        try:
            __import__(module_name)
        except Exception:
            failed_after_install.append(pkg if not alt_name else alt_name)

    if failed_after_install:
        print(f"❌ 以下依赖仍不可用: {', '.join(failed_after_install)}")
        print("请手动安装: python -m pip install " + " ".join(failed_after_install))
        return False

    print("✅ 依赖安装并验证通过")
    return True


def setup_environment():
    """Set up minimal runtime environment (paths, resources).

    Kept small to avoid heavy imports at module load time.
    """
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
    """Attempt to load Chinese fonts using the font initializer shim.

    This avoids importing DearPyGui at module import time. The shim will
    delegate to legacy code only when explicitly needed.
    """
    try:
        # Use the shim which will call the legacy initializer on demand.
        # Pass project_root when available to shims that need it.
        from app.font_initializer import initialize_chinese_font
        try:
            project_root = Path(__file__).parent
            return initialize_chinese_font(project_root)
        except TypeError:
            # shim may accept no args (backwards compatible); fall back
            return initialize_chinese_font()
    except Exception as e:
        print(f"⚠️ 加载中文字体失败（已降级）：{e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--log-level', default=os.environ.get('VISIONDEPLOY_LOG', 'INFO'), help='日志级别 (DEBUG/INFO/WARNING/ERROR)')
    args, _ = parser.parse_known_args()
    configure_logging(args.log_level)

    logging.getLogger().info("🎯 VisionDeploy Studio - AI模型部署平台")
    logging.getLogger().info("📝 专注于计算机视觉模型的本地部署")
    logging.getLogger().info("=" * 50)
    
    # 设置环境
    setup_environment()
    
    # 加载中文字体
    load_chinese_fonts()
    
    # 确保 requests 可用（若缺失，优先自动安装以支持模型下载）
    try:
        import requests  # type: ignore
    except Exception:
        print("requests 未安装，尝试自动安装 requests...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "requests"])
            try:
                import importlib
                if 'requests' in sys.modules:
                    importlib.reload(sys.modules['requests'])
                else:
                    __import__('requests')
                print("requests 安装完成")
            except Exception:
                # 即使 reload 失败，后续的 check_dependencies 会再次验证
                pass
        except Exception as e:
            print(f"自动安装 requests 失败: {e}")
            print("将继续执行全依赖检查，可能需要手动安装 requests")
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 请手动安装依赖: pip install dearpygui psutil requests Pillow")
        input("按回车键退出...")
        return
    
    # 启动应用程序 — 优先使用 CustomTkinter 原型，其次尝试 PySide6，再回退到原有 MainApplication
    try:
        # 修复导入问题
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        # 优先使用 customtkinter 前端（若已安装）
        try:
            import importlib
            has_ctk = False
            try:
                import customtkinter  # type: ignore
                has_ctk = True
            except Exception:
                has_ctk = False

            if has_ctk:
                try:
                    from app.gui_ctk import run_app as run_ctk_app
                    print("\n✅ 检测到 customtkinter，启动 CTk 前端...")
                    try:
                        resources_dir = project_root / 'resources'
                        mirror_choice = os.environ.get('VISIONDEPLOY_MIRROR', 'auto')
                        ctx = { 'project_root': str(project_root), 'resources_dir': str(resources_dir), 'mirror': mirror_choice }
                    except Exception:
                        ctx = None
                    # Try calling with context, fall back if the function doesn't accept args
                    try:
                        run_ctk_app(ctx)
                    except TypeError:
                        run_ctk_app()
                    sys.exit(0)
                except Exception as e:
                    print(f"启动 CTk 前端失败，回退：{e}")

            # 若未安装 CTk，尝试 PySide6 前端
            try:
                import PySide6  # type: ignore
                try:
                    from app.gui_pyside import run_app as run_pyside_app
                    print("\n✅ 检测到 PySide6，启动 PySide6 前端...")
                    try:
                        # pass same ctx if available
                        run_pyside_app(ctx)
                    except TypeError:
                        run_pyside_app()
                    sys.exit(0)
                except Exception as e:
                    print(f"启动 PySide6 前端失败，回退：{e}")
            except Exception:
                # PySide6 不可用，继续回退
                pass

        except Exception as e:
            print(f"前端探测失败: {e}")

        # 最后回退到主应用（原有 DearPyGui 实现）
        try:
            if 'app' not in sys.modules:
                import app
            from app.main_application import MainApplication
            print("\n✅ 启动 VisionDeploy Studio (主应用)...")
            app = MainApplication()
            app.run()
        except Exception as e:
            raise

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()