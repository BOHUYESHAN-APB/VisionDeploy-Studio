#!/usr/bin/env python3
"""临时字体初始化测试脚本 - 将结果写入 temp/font_init_result.log 并打印到 stdout

使用方式：在 VS Code 中打开此文件并运行 "Run Python File"（避免直接在终端中运行以遵循用户要求）。
"""
import traceback
from pathlib import Path
import sys

# 将项目根加入 sys.path，确保能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from app import font_initializer
except Exception as e:
    print("无法导入 app.font_initializer:", e)
    raise

def main():
    project_root = Path(__file__).resolve().parent.parent
    out = []
    out.append(f"project_root: {project_root}")
    fonts_dir = project_root / "resources" / "fonts"
    out.append(f"fonts_dir: {fonts_dir}")
    out.append(f"fonts_dir.exists: {fonts_dir.exists()}")
    if fonts_dir.exists():
        out.append("fonts files:")
        for p in sorted(fonts_dir.glob("*")):
            out.append(f" - {p.name}")
    try:
        result = font_initializer.initialize_chinese_font(project_root)
        out.append(f"initialize_chinese_font result: {result}")
    except Exception:
        out.append("initialize raised exception:")
        out.append(traceback.format_exc())

    log_path = project_root / "temp" / "font_init_result.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))

if __name__ == "__main__":
    main()