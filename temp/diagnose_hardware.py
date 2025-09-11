#!/usr/bin/env python3
"""temp/diagnose_hardware.py - 诊断硬件检测输出用于调试。
用法: python temp/diagnose_hardware.py
将打印 hardware_detector.get_device_summary(), GPUtil.getGPUs(), platform 信息, wmic/lspci 输出。
"""

import sys
import os
import subprocess
import platform
import json

# 尝试导入项目的 hardware_detector
hardware_detector = None
try:
    from core import hardware_detector as core_hd
    hardware_detector = core_hd
except Exception:
    try:
        import app.hardware_detector as app_hd
        hardware_detector = app_hd
    except Exception:
        hardware_detector = None

# GPUtil
try:
    import GPUtil
except Exception:
    GPUtil = None

def print_header(title):
    print("="*60)
    print(title)
    print("-"*60)

def run():
    print_header("Environment")
    print(f"Python: {sys.executable} / {platform.python_version()}")
    print(f"Platform: {platform.platform()}")
    print(f"Processor: {platform.processor()}")
    print(f"PROCESSOR_IDENTIFIER env: {os.environ.get('PROCESSOR_IDENTIFIER')}")

    # hardware_detector summary
    print_header("hardware_detector.get_device_summary()")
    if hardware_detector and hasattr(hardware_detector, 'get_device_summary'):
        try:
            summary = hardware_detector.get_device_summary()
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"调用 hardware_detector.get_device_summary() 失败: {e}")
    else:
        print("无法导入 hardware_detector 或未实现 get_device_summary()")

    # GPUtil
    print_header("GPUtil.getGPUs()")
    if GPUtil:
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                print("GPUtil 未检测到 GPU 列表或返回空")
            else:
                for g in gpus:
                    try:
                        info = {
                            "id": getattr(g, 'id', None),
                            "name": getattr(g, 'name', None),
                            "load": getattr(g, 'load', None),
                            "memoryTotal": getattr(g, 'memoryTotal', None),
                            "memoryUsed": getattr(g, 'memoryUsed', None),
                            "driver": getattr(g, 'driver', None)
                        }
                        print(json.dumps(info, ensure_ascii=False))
                    except Exception as e:
                        print(f"读取 GPUtil GPU 信息失败: {e}")
        except Exception as e:
            print(f"调用 GPUtil.getGPUs() 失败: {e}")
    else:
        print("GPUtil 模块不可用")

    # 平台命令
    print_header("Platform commands (wmic / lspci)")
    if os.name == 'nt':
        try:
            res = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], capture_output=True, text=True, env=os.environ)
            print("wmic output:")
            print(res.stdout)
        except Exception as e:
            print(f"调用 wmic 失败: {e}")
    else:
        try:
            res = subprocess.run(['lspci'], capture_output=True, text=True)
            lines = [l for l in (res.stdout or "").splitlines() if ('vga' in l.lower() or '3d controller' in l.lower())]
            if lines:
                print("lspci relevant lines:")
                for l in lines:
                    print(l)
            else:
                print("lspci 未找到 VGA/3D 控制器相关条目")
        except Exception as e:
            print(f"调用 lspci 失败: {e}")

    print_header("Done")

if __name__ == "__main__":
    run()