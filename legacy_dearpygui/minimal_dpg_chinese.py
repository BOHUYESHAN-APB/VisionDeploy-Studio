#!/usr/bin/env python3
"""Minimal DearPyGui Chinese display/input test.

Archived original for reference. To run the original, restore this file
to its original location under temp/.
"""

import dearpygui.dearpygui as dpg
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
fonts_dir = project_root / "resources" / "fonts"

print("project_root:", project_root)
print("fonts_dir:", fonts_dir)
print("fonts_dir.exists:", fonts_dir.exists())

def try_load_additional(font_path):
    add_additional = getattr(dpg, "add_additional_font", None)
    if callable(add_additional):
        try:
            f = add_additional(str(font_path), 18, glyph_ranges='chinese_simplified_common')
            print("add_additional_font ok ->", font_path)
            try:
                dpg.bind_font(f)
                print("bind_font(obj) ok")
            except Exception as e:
                print("bind_font(obj) failed:", e)
            return True
        except Exception as e:
            print("add_additional_font failed:", e)
    else:
        print("add_additional_font not available in this DPG build")
    return False

def try_add_font(font_path):
    try:
        with dpg.font_registry():
            try:
                f = dpg.add_font(str(font_path), 18, tag="default_font")
                print("add_font ok ->", font_path)
            except Exception as e:
                print("add_font failed:", e)
                return None

            for hint_name in ("mvFontRangeHint_Default", "mvFontRangeHint_Chinese_Simplified_Common", "mvFontRangeHint_Chinese_Full"):
                hint = getattr(dpg, hint_name, None)
                if hint is not None:
                    try:
                        dpg.add_font_range_hint(hint, parent=f)
                        print("add_font_range_hint applied:", hint_name)
                    except Exception as e:
                        print("add_font_range_hint failed:", hint_name, e)

            try:
                dpg.add_font_range(0x4e00, 0x9fff, parent=f)
                print("add_font_range 0x4e00-0x9fff applied")
            except Exception as e:
                print("add_font_range failed:", e)

        try:
            dpg.bind_font(f)
            print("bind_font(obj) ok")
        except Exception as e:
            print("bind_font(obj) failed:", e)
            try:
                dpg.bind_font("default_font")
                print("bind_font(tag) ok")
            except Exception as e2:
                print("bind_font(tag) failed:", e2)
        return f
    except Exception as e:
        print("font registry / add_font error:", e)
        return None


def main():
    dpg.create_context()

    font_loaded = False
    candidates = []
    if fonts_dir.exists():
        candidates = list(fonts_dir.glob("*.otf")) + list(fonts_dir.glob("*.ttf"))
    print("candidates:", [p.name for p in candidates])

    if candidates:
        if try_load_additional(candidates[0]):
            font_loaded = True
        else:
            fobj = try_add_font(candidates[0])
            if fobj:
                font_loaded = True

    with dpg.window(label="中文测试", width=480, height=220):
        dpg.add_text("测试中文显示: 你好，世界")
        dpg.add_spacing()
        dpg.add_input_text(label="输入中文", tag="input_text", default_value="")
        dpg.add_separator()
        dpg.add_text("", tag="display_text", wrap=400)

        def on_input(sender, app_data):
            try:
                dpg.set_value("display_text", f"输入: {app_data}")
            except Exception as e:
                print("on_input error:", e)

        dpg.set_item_callback("input_text", on_input)

        def transcode_callback(sender, app_data):
            try:
                val = dpg.get_value("input_text")
                if isinstance(val, str):
                    try:
                        decoded = val.encode('iso-8859-1').decode('gbk')
                        dpg.set_value("display_text", f"转码后: {decoded}")
                    except Exception as e:
                        print("transcode failed:", e)
                        dpg.set_value("display_text", val)
                else:
                    dpg.set_value("display_text", str(val))
            except Exception as e:
                print("transcode_callback error:", e)

        dpg.add_button(label="转码显示(display)", callback=transcode_callback)

    dpg.create_viewport(title="Minimal DPG Chinese", width=600, height=320)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    try:
        from app.font_initializer import rebind_default_font
        try:
            rebind_default_font()
        except Exception:
            pass
    except Exception:
        pass

    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
