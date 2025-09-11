"""
字体初始化模块 - VisionDeploy Studio
专门处理中文字体的加载和初始化
"""

import os
import dearpygui.dearpygui as dpg
from pathlib import Path

# 添加一个全局变量来跟踪字体是否已加载
_font_loaded = False

def initialize_chinese_font(project_root):
    """初始化中文字体（更鲁棒的查找与绑定，支持 .ttf 可变字体）.
    
    优先顺序：
    1. 精确匹配 MiSans VF 或 MiSans *.ttf（用户已放入 MiSans VF.ttf）
    2. MiSans-*.otf
    3. NotoSansCJKsc-Regular.otf
    4. 任何 .ttf / .otf 文件（降级尝试）
    
    Args:
        project_root: 项目根目录路径
        
    Returns:
        bool: 是否成功加载字体
    """
    global _font_loaded

    if _font_loaded:
        return True

    font_path = None
    fonts_dir = Path(project_root) / "resources" / "fonts"

    try:
        # 确保 DearPyGui 上下文存在（创建不会重复）
        try:
            dpg.create_context()
        except:
            pass

        # 确保字体注册表存在
        try:
            if not dpg.does_item_exist("font_registry"):
                with dpg.font_registry(tag="font_registry"):
                    pass
        except:
            pass

        # 优先使用仓库内的 TTF（例如 MiSans VF.ttf 或 MiSans*.ttf），回退到 OTF，再回退到 Noto，最后任意 ttf/otf 兜底
        candidates = []
        try:
            # 优先精确匹配 MiSans VF（可变字体）或其他 MiSans *.ttf
            vf = fonts_dir / "MiSans VF.ttf"
            if vf.exists():
                candidates.append(vf)
            candidates += sorted(fonts_dir.glob("MiSans*.ttf"))
            # 若仍无 ttf，再尝试 OTF 的 MiSans-*.otf
            if not candidates:
                candidates = sorted(fonts_dir.glob("MiSans-*.otf"))
            # 若仍未找到，尝试 Noto 字体
            if not candidates:
                noto = fonts_dir / "NotoSansCJKsc-Regular.otf"
                if noto.exists():
                    candidates = [noto]
            # 最后宽泛匹配任意 ttf/otf 作为兜底（优先 ttf 列表再 otf 列表）
            if not candidates:
                candidates = sorted(fonts_dir.glob("*.ttf")) + sorted(fonts_dir.glob("*.ttc")) + sorted(fonts_dir.glob("*.otf"))
        except Exception:
            # 出错时回退到宽泛匹配以避免阻塞初始化
            candidates = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf"))

        if candidates:
            # 按优先级排序（保留 glob 本身顺序即可），选择第一个存在的文件
            font_path = str(candidates[0])
        else:
            print("⚠️ 未在 resources/fonts 中找到字体文件")
            return False

        # 先移除已存在的 default_font（如果存在）
        try:
            if dpg.does_item_exist("default_font"):
                try:
                    dpg.delete_item("default_font")
                except:
                    pass
        except:
            pass

        # 尝试使用 DearPyGui 的 add_additional_font（若存在），这在某些版本对中文支持更好
        try:
            add_additional = getattr(dpg, "add_additional_font", None)
            if callable(add_additional):
                try:
                    font_obj = add_additional(font_path, 18, glyph_ranges='chinese_full')
                    try:
                        dpg.bind_font(font_obj)
                    except:
                        try:
                            dpg.bind_font("default_font")
                        except:
                            pass
                    print(f"✅ 成功通过 add_additional_font 加载中文字体: {font_path}")
                    _font_loaded = True
                    return True
                except Exception:
                    # 如果 add_additional_font 失败，继续走后续回退流程
                    pass
        except Exception:
            pass

        # 尝试在字体注册表中添加并绑定字体，尽量兼容不同 DearPyGui 版本的绑定方式
        try:
            # 首选：在 font_registry 中使用 with dpg.font(...)（若支持），并添加 range hints（若可用）
            try:
                with dpg.font_registry():
                    try:
                        with dpg.font(font_path, 18, tag="default_font") as default_font:
                            # 增加默认与中文范围提示，减少问号显示
                            for hint in (
                                getattr(dpg, "mvFontRangeHint_Default", None),
                                getattr(dpg, "mvFontRangeHint_Chinese_Simplified_Common", None),
                                getattr(dpg, "mvFontRangeHint_Chinese_Full", None),
                            ):
                                if hint is not None:
                                    try:
                                        dpg.add_font_range_hint(hint, parent=default_font)
                                    except:
                                        pass
                    except Exception:
                        # 回退：使用 add_font API（某些版本不支持 dpg.font 上下文管理）
                        default_font = dpg.add_font(font_path, 18, tag="default_font")
                        for hint in (
                            getattr(dpg, "mvFontRangeHint_Default", None),
                            getattr(dpg, "mvFontRangeHint_Chinese_Simplified_Common", None),
                            getattr(dpg, "mvFontRangeHint_Chinese_Full", None),
                        ):
                            if hint is not None:
                                try:
                                    dpg.add_font_range_hint(hint, parent=default_font)
                                except:
                                    pass
            except Exception:
                # 回退最小流程：font_registry + add_font
                with dpg.font_registry():
                    default_font = dpg.add_font(font_path, 18, tag="default_font")
                    for hint in (
                        getattr(dpg, "mvFontRangeHint_Default", None),
                        getattr(dpg, "mvFontRangeHint_Chinese_Simplified_Common", None),
                        getattr(dpg, "mvFontRangeHint_Chinese_Full", None),
                    ):
                        if hint is not None:
                            try:
                                dpg.add_font_range_hint(hint, parent=default_font)
                            except:
                                pass

            # 兜底：显式添加常用汉字 Unicode 范围（部分版本需要）
            try:
                dpg.add_font_range(0x4e00, 0x9fff, parent=default_font)
            except:
                pass

            # 绑定字体，优先对象，回退到 tag
            try:
                dpg.bind_font(default_font)
            except Exception:
                try:
                    dpg.bind_font("default_font")
                except Exception as e:
                    print(f"⚠️ 绑定字体失败: {e}")
                    return False

            print(f"✅ 成功加载中文字体: {font_path}")
            _font_loaded = True
            return True

        except Exception as e:
            print(f"⚠️ 字体注册或绑定过程中出错: {e}")
            # 尝试更简单的加载方式（不使用 range hints）
            try:
                with dpg.font_registry():
                    default_font = dpg.add_font(font_path, 18, tag="default_font")
                try:
                    dpg.bind_font(default_font)
                except:
                    dpg.bind_font("default_font")
                print(f"✅ 成功加载中文字体（简化方式）: {font_path}")
                _font_loaded = True
                return True
            except Exception as e2:
                print(f"⚠️ 简化字体加载也失败: {e2}")
                return False

    except Exception as e:
        print(f"⚠️ 初始化中文字体发生错误: {e}")
        return False

def rebind_default_font():
    """
    尝试在 setup_dearpygui() 之后重新绑定 default_font（某些 DearPyGui 版本需要在视口创建后绑定）。
    返回 True 若绑定成功，失败时返回 False 并打印调试信息。
    """
    try:
        # 优先尝试使用对象或 tag 绑定（兼容多种 DPG 版本）
        try:
            dpg.bind_font("default_font")
            return True
        except Exception:
            pass

        # 如果有 default_font item id，则再次尝试绑定该对象
        try:
            if dpg.does_item_exist("default_font"):
                try:
                    dpg.bind_font("default_font")
                    return True
                except:
                    pass
        except:
            pass

        print("⚠️ rebind_default_font: 无法绑定 default_font")
        return False
    except Exception as e:
        print(f"⚠️ rebind_default_font 异常: {e}")
        return False

# Debug helper: 提供更详细的诊断信息以便在 temp/test_font_init.py 中记录和分析
def initialize_chinese_font_debug(project_root):
    """
    对 initialize_chinese_font 的诊断封装。
    返回字典，包含 fonts 目录、候选字体列表、选中的 font_path、执行结果与错误信息（若有）。
    该函数不会改变 initialize_chinese_font 的行为，仅用于调试与日志记录。
    """
    from pathlib import Path
    info = {
        "project_root": str(project_root),
        "fonts_dir": str(Path(project_root) / "resources" / "fonts"),
        "fonts_exist": False,
        "candidates": [],
        "font_path": None,
        "success": False,
        "error": None
    }

    try:
        fonts_dir = Path(project_root) / "resources" / "fonts"
        info["fonts_exist"] = fonts_dir.exists()

        # 重用相同的候选查找策略以便与 initialize_chinese_font 保持一致
        candidates = []
        if fonts_dir.exists():
            candidates = list(fonts_dir.glob("MiSans-*.otf"))
            if not candidates:
                candidates = list(fonts_dir.glob("MiSans*.ttf"))
            if not candidates:
                noto = fonts_dir / "NotoSansCJKsc-Regular.otf"
                if noto.exists():
                    candidates = [noto]
            if not candidates:
                candidates = list(fonts_dir.glob("*.otf")) + list(fonts_dir.glob("*.ttf"))

        info["candidates"] = [str(p) for p in candidates]
        if candidates:
            info["font_path"] = str(candidates[0])

        # 调用现有初始化逻辑并记录结果（保持向后兼容）
        try:
            success = initialize_chinese_font(project_root)
            info["success"] = bool(success)
        except Exception as e:
            info["error"] = f"initialize_chinese_font raised: {e}"
            info["success"] = False

    except Exception as e:
        info["error"] = str(e)
        info["success"] = False

    return info