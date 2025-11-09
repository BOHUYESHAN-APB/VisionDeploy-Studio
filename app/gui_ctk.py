#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CustomTkinter GUI migration for VisionDeploy Studio

Provides a lightweight CustomTkinter-based frontend implementing:
- 模型选择（动态从 resources/models.json 加载）
- 镜像切换、量化模型下拉、设备选择
- 模型管理对话：下载 / 导入 / 列出本地模型
Designed as a pragmatic replacement用于快速迭代与打包。
"""

from pathlib import Path

try:
    import customtkinter as ctk
except Exception:
    ctk = None
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import platform
import subprocess
import inspect
import shutil

from tkinter import filedialog, messagebox

# YAML 用于保存模型->设备映射
try:
    import yaml
except Exception:
    yaml = None

# --- Unified safe fallbacks for backends used by the CTk UI -----------------
# These ensure the module can be imported even when optional backend
# components (model_manager, font_initializer, etc.) are not available.
project_root = Path(__file__).parent.parent

# model manager fallbacks
try:
    from app.model_manager import list_models, get_model_entry, download_model, find_local_models, import_local_model
except Exception:
    list_models = lambda *a, **k: []
    get_model_entry = lambda *a, **k: None
    download_model = lambda *a, **k: None
    find_local_models = lambda *a, **k: []
    import_local_model = lambda *a, **k: None
try:
    import app.model_manager as _model_manager_mod
except Exception:
    _model_manager_mod = None

# font initializer fallbacks
try:
    from app.font_initializer import initialize_chinese_font, initialize_chinese_font_debug, rebind_default_font
except Exception:
    initialize_chinese_font = None
    initialize_chinese_font_debug = None
    rebind_default_font = None

# 尝试导入按需环境管理器（容错）
try:
    from core.on_demand_environment_manager import OnDemandEnvironmentManager
except Exception:
    OnDemandEnvironmentManager = None

# 尝试导入模型调用器（容错）
try:
    from core.model_invoker import model_invoker
    from core.hardware_detector import hardware_detector
except Exception:
    model_invoker = None
    hardware_detector = None

# 尝试导入 GUI <-> 处理器 辅助函数（兼容 app/handlers）
try:
    from app.handlers.model_handlers import load_model_device_map, save_model_device_map, get_quantized_options_for_model
    from app import hf_browser
except Exception:
    load_model_device_map = None
    save_model_device_map = None
    get_quantized_options_for_model = None
    try:
        # best-effort import hf_browser even if other handlers fail
        from app import hf_browser
    except Exception:
        hf_browser = None


# Helper: resolve the user-visible mirror choice to a backend mirror param/URL
def _resolve_mirror_choice(mirror_choice: str) -> str:
    """Map mirror dropdown value to download_model's mirror parameter.

    Supported choices:
      - 'cn' -> 'https://hf-mirror.com/'
      - 'huggingface' -> 'https://huggingface.co/'
      - 'auto' or others -> 'auto' (let backend decide)
    """
    if not mirror_choice:
        return "auto"
    key = str(mirror_choice).lower().strip()
    if key in ("cn", "hf-mirror", "hf-mirror.com", "hf-mirror.com/"):
        return "https://hf-mirror.com/"
    if key in ("huggingface", "hf", "huggingface.co", "huggingface.co/"):
        return "https://huggingface.co/"
    # accept explicit URLs unchanged
    if key.startswith("http://") or key.startswith("https://"):
        return mirror_choice
    # default: let backend auto-select
    return "auto"


# Simple approach to avoid type checking issues with conditional inheritance
class ModelManagerDialog:
    def __init__(self, parent=None):
        if ctk:
            self.dialog = ctk.CTkToplevel(parent)
            self.dialog.geometry("720x420")
            self.dialog.title("模型管理")
        else:
            self.dialog = tk.Toplevel(parent)
            self.dialog.geometry("720x420")
            self.dialog.title("模型管理")
        self.parent = parent
        # Title is set in __init__
        self.parent = parent
        # try to capture mirror preference from parent
        try:
            self.preferred_mirror = getattr(parent, 'mirror_var', None)
        except Exception:
            self.preferred_mirror = None

        # UI components
        if ctk:
            self.model_var = ctk.StringVar(value="无可用模型")
            self.model_menu = ctk.CTkOptionMenu(self.dialog, values=["无可用模型"], variable=self.model_var)
            self.model_menu.pack(padx=10, pady=8, fill="x")

            btn_frame = ctk.CTkFrame(self.dialog)
            btn_frame.pack(fill="x", padx=10, pady=6)
            self.download_btn = ctk.CTkButton(btn_frame, text="下载所选模型", command=self.on_download)
            self.import_btn = ctk.CTkButton(btn_frame, text="导入本地模型", command=self.on_import_local)
            self.close_btn = ctk.CTkButton(btn_frame, text="关闭", command=self.dialog.destroy)
            self.download_btn.pack(side="left", padx=6, pady=6)
            self.import_btn.pack(side="left", padx=6, pady=6)
            self.close_btn.pack(side="right", padx=6, pady=6)

            self.local_list = ctk.CTkTextbox(self.dialog, width=1, height=10)
            self.local_list.pack(expand=True, fill="both", padx=10, pady=8)
            self.status = ctk.CTkLabel(self.dialog, text="")
            self.status.pack(padx=10, pady=6, anchor="w")
        else:
            self.model_var = tk.StringVar(value="无可用模型")
            self.model_menu = tk.OptionMenu(self.dialog, self.model_var, "无可用模型")
            self.model_menu.pack(padx=10, pady=8, fill="x")

            btn_frame = tk.Frame(self.dialog)
            btn_frame.pack(fill="x", padx=10, pady=6)
            self.download_btn = tk.Button(btn_frame, text="下载所选模型", command=self.on_download)
            self.import_btn = tk.Button(btn_frame, text="导入本地模型", command=self.on_import_local)
            self.close_btn = tk.Button(btn_frame, text="关闭", command=self.dialog.destroy)
            self.download_btn.pack(side="left", padx=6, pady=6)
            self.import_btn.pack(side="left", padx=6, pady=6)
            self.close_btn.pack(side="right", padx=6, pady=6)

            self.local_list = tk.Listbox(self.dialog)
            self.local_list.pack(expand=True, fill="both", padx=10, pady=8)
            self.status = tk.Label(self.dialog, text="")
            self.status.pack(padx=10, pady=6, anchor="w")

        self.refresh_models()
        self.refresh_local()

    def refresh_models(self):
        try:
            models = list_models() or []
            items = [f"{m.get('display_name') or m.get('id')} ({m.get('id')})" for m in models]
            if not items:
                items = ["无可用模型"]
        except Exception:
            items = ["无可用模型"]
        # update option menu
        if ctk:
            try:
                if isinstance(items, list):
                    # Type cast to satisfy type checker
                    values_list = [str(item) for item in items]
                    self.model_menu.configure(values=values_list)  # type: ignore
                else:
                    self.model_menu.configure(values=[str(items)])  # type: ignore
                if items:
                    self.model_var.set(items[0] if isinstance(items, list) else str(items))
            except Exception:
                pass
        else:
            try:
                menu = self.model_menu["menu"]
                menu.delete(0, "end")
                item_list = items if isinstance(items, list) else [str(items)]
                for it in item_list:
                    menu.add_command(label=it, command=lambda v=it: self.model_var.set(v))
                if item_list:
                    self.model_var.set(item_list[0])
            except Exception:
                pass

    def refresh_local(self):
        try:
            local = find_local_models() or []
        except Exception:
            local = []
        if ctk:
            self.local_list.delete("1.0", "end")
            if local:
                for p in local:
                    self.local_list.insert("end", str(p.name) + "\n")
            else:
                self.local_list.insert("end", "没有本地模型\n")
        else:
            self.local_list.delete(0, "end")
            if local:
                for p in local:
                    self.local_list.insert("end", str(p.name))
            else:
                self.local_list.insert("end", "没有本地模型")

    def on_download(self):
        sel = self.model_var.get()
        if not sel or sel == "无可用模型":
            self._set_status("未选择模型")
            return
        model_id = sel.split('(')[-1].strip(')')
        self._set_status(f"开始下载 {model_id} ...")
        # UI: disable buttons and start progress indicator
        try:
            if ctk:
                self.download_btn.configure(state="disabled")
                self.import_btn.configure(state="disabled")
                # create progress bar if not exists
                if not hasattr(self, "_download_progress"):
                    try:
                        self._download_progress = ctk.CTkProgressBar(self.dialog, width=680)
                        if hasattr(self._download_progress, 'set'):
                            self._download_progress.set(0.0)
                        self._download_progress.pack(padx=10, pady=4, fill="x")
                    except Exception:
                        self._download_progress = None
                if self._download_progress and hasattr(self._download_progress, 'set'):
                    try:
                        if ctk:
                            self._download_progress.set(0.2)
                        else:
                            self._download_progress["value"] = 0.2
                    except Exception:
                        pass
            else:
                self.download_btn.config(state="disabled")
                self.import_btn.config(state="disabled")
                if not hasattr(self, "_download_progress"):
                    try:
                        from tkinter import ttk
                        self._download_progress = ttk.Progressbar(self.dialog, orient="horizontal", length=680, mode="indeterminate")
                        self._download_progress.pack(padx=10, pady=4, fill="x")
                        try:
                            self._download_progress.start(10)
                        except:
                            pass
                    except Exception:
                        self._download_progress = None
        except:
            pass

        def worker():
            status_msg = ""
            # create a best-effort stop event and attach to dialog for potential external cancel
            stop_event = threading.Event()
            try:
                self._download_stop_event = stop_event  # type: ignore
            except:
                pass

            def progress_cb(message, percent):
                # message: str, percent: int (0-100) or -1 for error/cancel
                try:
                    text = f"{message} ({percent}%)" if isinstance(percent, (int, float)) and percent >= 0 else str(message)
                    # update dialog status
                    try:
                        self._set_status(text)
                    except Exception:
                        pass
                    # update parent status bar if available
                    try:
                        if (hasattr(self, "parent") and self.parent is not None and 
                            hasattr(self.parent, "status_label") and self.parent.status_label is not None):
                            try:
                                if ctk and hasattr(self.parent.status_label, 'configure'):
                                    self.parent.status_label.configure(text=text)
                                elif not ctk and hasattr(self.parent.status_label, 'config'):
                                    self.parent.status_label.config(text=text)
                            except:
                                pass
                    except Exception:
                        pass
                    # update progress bar if numeric percent provided
                    try:
                        if (hasattr(self, "_download_progress") and self._download_progress and hasattr(self._download_progress, 'set')):
                            if isinstance(percent, (int, float)) and percent >= 0:
                                if ctk:
                                    try:
                                        self._download_progress.set(min(1.0, float(percent) / 100.0))
                                    except:
                                        pass
                                else:
                                    try:
                                        self._download_progress["value"] = float(percent)
                                    except:
                                        pass
                    except Exception:
                        pass
                except:
                    pass

            try:
                # determine mirror: prefer dialog parent's mirror selection if available
                mirror_choice = 'auto'
                try:
                    if self.preferred_mirror is not None:
                        raw = (self.preferred_mirror.get() if hasattr(self.preferred_mirror, 'get') else str(self.preferred_mirror)) or 'auto'
                        mirror_choice = _resolve_mirror_choice(raw)
                except:
                    mirror_choice = 'auto'
                # If built-in models DB is disabled, open HF browser for the user to download via HF UI
                try:
                    use_local_db = getattr(_model_manager_mod, 'USE_LOCAL_MODELS_DB', False) if _model_manager_mod else False
                except:
                    use_local_db = False
                if not use_local_db:
                    # open HF browser to let user pick and download (safe fallback)
                    try:
                        parent_app = getattr(self, 'parent', None)
                        if parent_app and hasattr(parent_app, 'open_hf_browser'):
                            parent_app.open_hf_browser()
                        else:
                            try:
                                # self.open_hf_browser()  # type: ignore
                                pass
                            except:
                                pass
                        status_msg = '已切换到 HF 浏览（请使用浏览器下载到本地 temp/）'
                        p = None
                    except Exception:
                        p = None
                else:
                    p = download_model(model_id, mirror=mirror_choice, callback=progress_cb, stop_event=stop_event)
                if p:
                    status_msg = f"下载完成: {Path(p).name}"
                else:
                    # if stop_event was set, interpret as cancelled
                    if getattr(stop_event, "is_set", lambda: False)() if stop_event else False:
                        status_msg = "下载已取消"
                    else:
                        status_msg = "下载失败"
            except Exception as e:
                status_msg = f"下载异常: {e}"
            # 更新对话框内状态
            try:
                self._set_status(status_msg)
            except:
                pass
            # 尝试更新父窗口的状态栏（若存在）
            try:
                if (hasattr(self, "parent") and self.parent is not None and 
                    hasattr(self.parent, "status_label") and self.parent.status_label is not None):
                    try:
                        if ctk and hasattr(self.parent.status_label, 'configure'):
                            self.parent.status_label.configure(text=status_msg)
                        elif not ctk and hasattr(self.parent.status_label, 'config'):
                            self.parent.status_label.config(text=status_msg)
                    except Exception:
                        pass
            except:
                pass
            # stop/cleanup progress and re-enable buttons
            try:
                if (hasattr(self, "_download_progress") and self._download_progress and 
                    hasattr(self._download_progress, 'set')):
                    try:
                        if ctk:
                            self._download_progress.set(1.0)
                        else:
                            try:
                                self._download_progress.stop()
                            except:
                                pass
                    except Exception:
                        pass
                    try:
                        self._download_progress.destroy()
                    except Exception:
                        pass
                    try:
                        del self._download_progress
                    except Exception:
                        pass
            except:
                pass
                if ctk:
                    try:
                        self.download_btn.configure(state="normal")
                        self.import_btn.configure(state="normal")
                    except Exception:
                        pass
                else:
                    try:
                        self.download_btn.config(state="normal")
                        self.import_btn.config(state="normal")
                    except Exception:
                        pass
            except Exception:
                pass
            # remove stop event handle if present
            try:
                if hasattr(self, "_download_stop_event"):
                    try:
                        delattr(self, "_download_stop_event")
                    except Exception:
                        pass
            except Exception:
                pass
            # refresh local list
            try:
                self.refresh_local()
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def on_import_local(self):
        path = filedialog.askopenfilename(parent=self.dialog, title="选择本地模型文件")
        if not path:
            return
        self._set_status(f"导入 {path} ...")
        def worker():
            try:
                p = import_local_model(path)
                if p:
                    self._set_status(f"已导入: {Path(p).name}")
                else:
                    self._set_status("导入失败")
            except Exception as e:
                self._set_status(f"导入异常: {e}")
            self.refresh_local()
        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, text):
        try:
            if ctk:
                self.status.configure(text=text)
            else:
                self.status.config(text=text)
        except:
            pass





def run_app(context=None):
    """Run the CTk frontend. Accepts optional context dict passed from launcher.

    Context keys (optional):
      - project_root: str
      - resources_dir: str
      - mirror: str
    """
    app = MainApp(start_context=context)
    app.setup()
    # apply any start_context settings to UI controls (best-effort)
    try:
        if context and isinstance(context, dict):
            try:
                if 'mirror' in context and getattr(app, 'mirror_var', None) is not None:
                    app._safe_set_var(app.mirror_var, context.get('mirror'))
            except Exception:
                pass
    except Exception:
        pass

    # Check if root was properly initialized
    if app.root is not None:
        if ctk:
            app.root.mainloop()
        else:
            app.root.mainloop()
    else:
        print("Error: Failed to initialize UI root window")


if __name__ == "__main__":
    if ctk is None:
        print("未检测到 customtkinter，请先安装：pip install customtkinter")
    else:
        run_app()

    def on_import_local(self):
        path = filedialog.askopenfilename(parent=self.dialog, title="选择本地模型文件")
        if not path:
            return
        self._set_status(f"导入 {path} ...")
        def worker():
            try:
                p = import_local_model(path)
                if p:
                    self._set_status(f"已导入: {Path(p).name}")
                else:
                    self._set_status("导入失败")
            except Exception as e:
                self._set_status(f"导入异常: {e}")
            self.refresh_local()
        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, text):
        try:
            if ctk:
                self.status.configure(text=text)
            else:
                self.status.config(text=text)
        except:
            pass


class MainApp:
    def __init__(self, start_context=None):
        # start_context: optional dict passed from launcher (project_root, resources_dir, mirror)
        self.root = None
        # load persisted prefs and merge with start_context (start_context overrides saved prefs)
        try:
            from app.ui_prefs import load_prefs
            saved = load_prefs() or {}
        except Exception:
            saved = {}
        self.start_context = {}
        self.start_context.update(saved)
        if isinstance(start_context, dict):
            self.start_context.update(start_context)

    # --- 小型 UI helper，统一处理 CTk vs Tk 的 text/config 更新 ---
    def _safe_set(self, widget, text):
        try:
            if not widget:
                return
            if ctk:
                try:
                    widget.configure(text=text)
                except:
                    widget.configure(text=text)
            else:
                try:
                    widget.config(text=text)
                except:
                    widget.configure(text=text)
        except:
            pass

    def _safe_set_status(self, text):
        try:
            if hasattr(self, 'status_label') and self.status_label is not None:
                self._safe_set(self.status_label, text)
        except:
            pass

    def _safe_set_var(self, var, value):
        try:
            if var is None:
                return
            try:
                var.set(value)
            except:
                # some vars might be special; ignore errors
                pass
        except:
            pass

    def setup(self):
        if ctk:
            # prefer user-configured theme from config.yaml when available
            try:
                import yaml as _yaml
                cfg = None
                try:
                    with open(project_root.parent / 'config.yaml', 'r', encoding='utf-8') as _f:
                        cfg = _yaml.safe_load(_f) or {}
                except Exception:
                    try:
                        with open('config.yaml', 'r', encoding='utf-8') as _f:
                            cfg = _yaml.safe_load(_f) or {}
                    except Exception:
                        cfg = {}
                theme = cfg.get('theme', 'System')
            except Exception:
                theme = 'System'
            try:
                ctk.set_appearance_mode(theme)
            except Exception:
                try:
                    ctk.set_appearance_mode('System')
                except Exception:
                    pass
            try:
                ctk.set_default_color_theme("blue")
            except Exception:
                pass
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        # 初始化按需环境管理器（可选）
        try:
            self.env_manager = OnDemandEnvironmentManager() if OnDemandEnvironmentManager else None
        except Exception:
            self.env_manager = None

        self.root.title("VisionDeploy Studio - CTk")
        # restore window geometry from prefs if present
        try:
            geom = None
            if isinstance(self.start_context, dict):
                geom = self.start_context.get('window_geometry')
            if geom:
                try:
                    self.root.geometry(geom)
                except:
                    self.root.geometry("1100x720")
            else:
                self.root.geometry("1100x720")
        except:
            try:
                self.root.geometry("1100x720")
            except:
                pass

        # Menubar: 文件/视图/帮助（兼容 ctk 与 tk）
        try:
            if ctk:
                menubar = ctk.CTkFrame(self.root)
                menubar.pack(side="top", fill="x")
                # simple buttons as menu
                mb_file = ctk.CTkButton(menubar, text="重载字体", command=self._on_reload_fonts, width=120)
                mb_file.pack(side="left", padx=4, pady=4)
                mb_theme = ctk.CTkButton(menubar, text="切换主题", command=self._on_toggle_theme, width=120)
                mb_theme.pack(side="left", padx=4, pady=4)
                mb_settings = ctk.CTkButton(menubar, text="设置", command=self.open_settings_dialog, width=120)
                mb_settings.pack(side="right", padx=4, pady=4)
                mb_about = ctk.CTkButton(menubar, text="关于", command=lambda: messagebox.showinfo("关于","VisionDeploy Studio - CTk"), width=120)
                mb_about.pack(side="right", padx=4, pady=4)
            else:
                menubar = tk.Frame(self.root)
                menubar.pack(side="top", fill="x")
                mb_file = tk.Button(menubar, text="重载字体", command=self._on_reload_fonts, width=12)
                mb_file.pack(side="left", padx=4, pady=4)
                mb_theme = tk.Button(menubar, text="切换主题", command=self._on_toggle_theme, width=12)
                mb_theme.pack(side="left", padx=4, pady=4)
                mb_settings = tk.Button(menubar, text="设置", command=self.open_settings_dialog, width=12)
                mb_settings.pack(side="right", padx=4, pady=4)
                mb_about = tk.Button(menubar, text="关于", command=lambda: messagebox.showinfo("关于","VisionDeploy Studio - CTk"), width=12)
                mb_about.pack(side="right", padx=4, pady=4)
        except Exception as e:
            try:
                import traceback
                traceback.print_exc()
            except:
                pass
            try:
                if hasattr(self, 'status_label') and self.status_label is not None:
                    self._safe_set(self.status_label, f"HF 浏览器打开失败: {e}")
            except:
                pass



        # Layout frames
        if ctk:
            left = ctk.CTkFrame(self.root, width=320)
            left.pack(side="left", fill="y", padx=8, pady=8)
            right = ctk.CTkFrame(self.root)
            right.pack(side="right", expand=True, fill="both", padx=8, pady=8)
        else:
            left = tk.Frame(self.root, width=320)
            left.pack(side="left", fill="y", padx=8, pady=8)
            right = tk.Frame(self.root)
            right.pack(side="right", expand=True, fill="both", padx=8, pady=8)

        # Status and header info
        try:
            py_ver = sys.version.split()[0]
        except:
            py_ver = "unknown"
        header_text = f"就绪 — Python {py_ver}"
        if ctk:
            self.status_label = ctk.CTkLabel(left, text=header_text)
            self.status_label.pack(padx=6, pady=6, anchor="w")
            self.device_label = ctk.CTkLabel(left, text="设备: CPU")
            self.device_label.pack(padx=6, pady=2, anchor="w")
            self.model_label = ctk.CTkLabel(left, text="模型: 未选择")
            self.model_label.pack(padx=6, pady=2, anchor="w")
        else:
            self.status_label = tk.Label(left, text=header_text)
            self.status_label.pack(padx=6, pady=6, anchor="w")
            self.device_label = tk.Label(left, text="设备: CPU")
            self.device_label.pack(padx=6, pady=2, anchor="w")
            self.model_label = tk.Label(left, text="模型: 未选择")
            self.model_label.pack(padx=6, pady=2, anchor="w")

        # Model controls
        if ctk:
            self.model_var = ctk.StringVar(value="自动选择")
            self.model_menu = ctk.CTkOptionMenu(left, values=["自动选择"], variable=self.model_var, width=250)
            self.model_menu.pack(padx=6, pady=4)
            # 绑定选择变更回调
            try:
                self.model_var.trace_add("write", lambda *a: self._on_model_change())
            except Exception:
                pass
        else:
            self.model_var = tk.StringVar(value="自动选择")
            self.model_menu = tk.OptionMenu(left, self.model_var, "自动选择")
            self.model_menu.pack(padx=6, pady=4)
            try:
                # tkinter 旧 API
                self.model_var.trace("w", lambda *a: self._on_model_change())
            except Exception:
                pass

        # mirror and quantized
        if ctk:
            self.mirror_var = ctk.StringVar(value="auto")
            self.mirror_menu = ctk.CTkOptionMenu(left, values=['auto','cn','global','official','huggingface'], variable=self.mirror_var)
            self.mirror_menu.pack(padx=6, pady=4)
            try:
                # react to mirror changes immediately
                self.mirror_var.trace_add("write", lambda *a: self._on_mirror_change())
            except Exception:
                try:
                    self.mirror_var.trace("w", lambda *a: self._on_mirror_change())
                except Exception:
                    pass

            self.quant_var = ctk.StringVar(value="无量化模型")
            self.quant_menu = ctk.CTkOptionMenu(left, values=['无量化模型'], variable=self.quant_var)
            self.quant_menu.pack(padx=6, pady=4)
        else:
            self.mirror_var = tk.StringVar(value="auto")
            self.mirror_menu = tk.OptionMenu(left, self.mirror_var, 'auto','cn','global','official','huggingface')
            self.mirror_menu.pack(padx=6, pady=4)
            self.quant_var = tk.StringVar(value="无量化模型")
            self.quant_menu = tk.OptionMenu(left, self.quant_var, '无量化模型')
            self.quant_menu.pack(padx=6, pady=4)

        # device combo
        if ctk:
            self.device_var = ctk.StringVar(value=self.start_context.get('device','CPU'))
            self.device_menu = ctk.CTkOptionMenu(left, values=['CPU','Auto','GPU - Intel'], variable=self.device_var)
            self.device_menu.pack(padx=6, pady=4)
        else:
            self.device_var = tk.StringVar(value=self.start_context.get('device','CPU'))
            self.device_menu = tk.OptionMenu(left, self.device_var, 'CPU','Auto','GPU - Intel')
            self.device_menu.pack(padx=6, pady=4)

        # Zoom presets (VSCode-style)
        try:
            zoom_values = ['80%','90%','100%','110%','125%','150%','175%','200%']
            if ctk:
                self.zoom_var = ctk.StringVar(value='100%')
                self.zoom_menu = ctk.CTkOptionMenu(left, values=zoom_values, variable=self.zoom_var, width=120)
                self.zoom_menu.pack(padx=6, pady=6)
                self.apply_zoom_btn = ctk.CTkButton(left, text="应用缩放", command=self._apply_zoom, width=120)
                self.apply_zoom_btn.pack(padx=6, pady=4)
                try:
                    # auto-apply when zoom selection changes
                    self.zoom_var.trace_add("write", lambda *a: self._on_zoom_change())
                except Exception:
                    try:
                        self.zoom_var.trace("w", lambda *a: self._on_zoom_change())
                    except Exception:
                        pass
            else:
                self.zoom_var = tk.StringVar(value='100%')
                self.zoom_menu = tk.OptionMenu(left, self.zoom_var, *zoom_values)
                self.zoom_menu.pack(padx=6, pady=6)
                self.apply_zoom_btn = tk.Button(left, text="应用缩放", command=self._apply_zoom)
                self.apply_zoom_btn.pack(padx=6, pady=4)
                try:
                    # tkinter trace (older API)
                    try:
                        self.zoom_var.trace_add("write", lambda *a: self._on_zoom_change())
                    except Exception:
                        self.zoom_var.trace("w", lambda *a: self._on_zoom_change())
                except Exception:
                    pass
        except Exception:
            pass

        # model manager button
        if ctk:
            btn = ctk.CTkButton(left, text="模型管理", command=self.open_model_manager)
            btn.pack(padx=6, pady=8)
            hf_btn = ctk.CTkButton(left, text="HF 浏览", command=self.open_hf_browser)
            hf_btn.pack(padx=6, pady=4)
            prep_btn = ctk.CTkButton(left, text="准备环境", command=self._on_prepare_env)
            prep_btn.pack(padx=6, pady=4)
            self.reload_font_btn = ctk.CTkButton(left, text="重载字体", command=self._on_reload_fonts)
            self.reload_font_btn.pack(padx=6, pady=4)
        else:
            btn = tk.Button(left, text="模型管理", command=self.open_model_manager)
            btn.pack(padx=6, pady=8)
            hf_btn = tk.Button(left, text="HF 浏览", command=self.open_hf_browser)
            hf_btn.pack(padx=6, pady=4)
            prep_btn = tk.Button(left, text="准备环境", command=self._on_prepare_env)
            prep_btn.pack(padx=6, pady=4)
            self.reload_font_btn = tk.Button(left, text="重载字体", command=self._on_reload_fonts)
            self.reload_font_btn.pack(padx=6, pady=4)

        # Refresh models button
        try:
            if ctk:
                self.refresh_models_btn = ctk.CTkButton(left, text="刷新模型", command=self.refresh_model_list)
                self.refresh_models_btn.pack(padx=6, pady=6)
            else:
                self.refresh_models_btn = tk.Button(left, text="刷新模型", command=self.refresh_model_list)
                self.refresh_models_btn.pack(padx=6, pady=6)
        except Exception:
            pass

        # right display
        if ctk:
            self.details = ctk.CTkLabel(right, text="选择文件开始推理...", wraplength=800, justify="left")
            self.details.pack(padx=6, pady=6, anchor="nw")
            btn_frame_r = ctk.CTkFrame(right)
            btn_frame_r.pack(padx=6, pady=6, anchor="nw")
            self.select_file_btn = ctk.CTkButton(btn_frame_r, text="选择文件", command=self._select_input_file)
            self.select_file_btn.pack(side="left", padx=6)
            self.start_infer_btn = ctk.CTkButton(btn_frame_r, text="开始推理", command=self._start_inference)
            self.start_infer_btn.pack(side="left", padx=6)
            # model details area (populate when model changes)
            self.model_details_frame = ctk.CTkFrame(right)
            self.model_details_frame.pack(fill="x", expand=False, padx=6, pady=6, anchor="nw")
            self.md_name = ctk.CTkLabel(self.model_details_frame, text="名称: -", anchor="w")
            self.md_name.pack(fill="x", padx=4, pady=2)
            self.md_category = ctk.CTkLabel(self.model_details_frame, text="分类: -", anchor="w")
            self.md_category.pack(fill="x", padx=4, pady=2)
            self.md_task = ctk.CTkLabel(self.model_details_frame, text="任务: -", anchor="w")
            self.md_task.pack(fill="x", padx=4, pady=2)
            self.md_version = ctk.CTkLabel(self.model_details_frame, text="版本: -", anchor="w")
            self.md_version.pack(fill="x", padx=4, pady=2)
            self.md_size = ctk.CTkLabel(self.model_details_frame, text="大小: -", anchor="w")
            self.md_size.pack(fill="x", padx=4, pady=2)
            self.md_status = ctk.CTkLabel(self.model_details_frame, text="状态: -", anchor="w")
            self.md_status.pack(fill="x", padx=4, pady=2)
            # action buttons and quant options
            act_frame = ctk.CTkFrame(right)
            act_frame.pack(padx=6, pady=4, anchor="nw")
            self.download_model_btn = ctk.CTkButton(act_frame, text="下载到 temp", command=self._on_download_selected_model)
            self.download_model_btn.pack(side="left", padx=6)
            # import downloaded models from temp
            self.import_downloaded_btn = ctk.CTkButton(act_frame, text="导入已下载模型", command=self._on_import_downloaded_model)
            self.import_downloaded_btn.pack(side="left", padx=6)
            self.use_model_btn = ctk.CTkButton(act_frame, text="使用此模型", command=self._on_use_selected_model)
            self.use_model_btn.pack(side="left", padx=6)
            self.open_folder_btn = ctk.CTkButton(act_frame, text="打开模型目录", command=self._on_open_model_folder)
            self.open_folder_btn.pack(side="left", padx=6)
            self.quant_options_var = ctk.StringVar(value="无量化模型")
            self.quant_options_menu = ctk.CTkOptionMenu(act_frame, values=["无量化模型"], variable=self.quant_options_var)
            self.quant_options_menu.pack(side="left", padx=6)
        else:
            self.details = tk.Label(right, text="选择文件开始推理...", wraplength=800, justify="left")
            self.details.pack(padx=6, pady=6, anchor="nw")
            btn_frame_r = tk.Frame(right)
            btn_frame_r.pack(padx=6, pady=6, anchor="nw")
            self.select_file_btn = tk.Button(btn_frame_r, text="选择文件", command=self._select_input_file)
            self.select_file_btn.pack(side="left", padx=6)
            self.start_infer_btn = tk.Button(btn_frame_r, text="开始推理", command=self._start_inference)
            self.start_infer_btn.pack(side="left", padx=6)
            # model details area for tkinter
            self.model_details_frame = tk.Frame(right)
            self.model_details_frame.pack(fill="x", expand=False, padx=6, pady=6, anchor="nw")
            self.md_name = tk.Label(self.model_details_frame, text="名称: -", anchor="w")
            self.md_name.pack(fill="x", padx=4, pady=2)
            self.md_category = tk.Label(self.model_details_frame, text="分类: -", anchor="w")
            self.md_category.pack(fill="x", padx=4, pady=2)
            self.md_task = tk.Label(self.model_details_frame, text="任务: -", anchor="w")
            self.md_task.pack(fill="x", padx=4, pady=2)
            self.md_version = tk.Label(self.model_details_frame, text="版本: -", anchor="w")
            self.md_version.pack(fill="x", padx=4, pady=2)
            self.md_size = tk.Label(self.model_details_frame, text="大小: -", anchor="w")
            self.md_size.pack(fill="x", padx=4, pady=2)
            self.md_status = tk.Label(self.model_details_frame, text="状态: -", anchor="w")
            self.md_status.pack(fill="x", padx=4, pady=2)
            # action buttons and quant options for tkinter
            act_frame = tk.Frame(right)
            act_frame.pack(padx=6, pady=4, anchor="nw")
            self.download_model_btn = tk.Button(act_frame, text="下载到 temp", command=self._on_download_selected_model)
            self.download_model_btn.pack(side="left", padx=6)
            try:
                self.import_downloaded_btn = tk.Button(act_frame, text="导入已下载模型", command=self._on_import_downloaded_model)
                self.import_downloaded_btn.pack(side="left", padx=6)
            except Exception:
                pass
            self.use_model_btn = tk.Button(act_frame, text="使用此模型", command=self._on_use_selected_model)
            self.use_model_btn.pack(side="left", padx=6)
            self.open_folder_btn = tk.Button(act_frame, text="打开模型目录", command=self._on_open_model_folder)
            self.open_folder_btn.pack(side="left", padx=6)
            self.quant_options_var = tk.StringVar(value="无量化模型")
            try:
                self.quant_options_menu = tk.OptionMenu(act_frame, self.quant_options_var, "无量化模型")
                self.quant_options_menu.pack(side="left", padx=6)
            except Exception:
                pass

        # 推理用临时变量
        self.selected_file = None

        # startup: refresh model list once
        try:
            self.root.after(100, self.refresh_model_list)
        except Exception:
            try:
                self.refresh_model_list()
            except:
                pass

        # 显示 context 信息到状态栏
        try:
            info = []
            ctx = getattr(self, 'start_context', {})
            if ctx.get('resources_dir'):
                info.append(f"res:{Path(ctx['resources_dir']).name}")
            if ctx.get('mirror'):
                info.append(f"mirror:{ctx['mirror']}")
            if info and hasattr(self, 'status_label') and self.status_label:
                self._safe_set(self.status_label, self.status_label.cget('text') + ' | ' + ' | '.join(info))
        except Exception:
            pass

    def _on_toggle_theme(self):
        """Toggle CTk appearance mode (System -> Dark -> Light cycles)"""
        try:
            if not ctk:
                return
            cur = ctk.get_appearance_mode()
            nxt = 'Dark' if cur == 'System' or cur == 'Light' else 'Light' if cur == 'Dark' else 'System'
            ctk.set_appearance_mode(nxt)
            try:
                self.status_label.configure(text=f"主题: {nxt}")
            except:
                self.status_label.config(text=f"主题: {nxt}")
        except Exception:
            pass

    def refresh_model_list(self):
        """Refresh model list"""
        # Implementation goes here
        pass

    def open_model_manager(self):
        """Open model manager dialog"""
        ModelManagerDialog(self.root)

    def _on_model_change(self):
        """Handle model selection change"""
        # Implementation goes here
        pass

    def open_settings_dialog(self):
        try:
            dlg = ctk.CTkToplevel(self.root) if ctk else tk.Toplevel(self.root)
            dlg.title("设置")
            dlg.geometry("420x220")

            # mirror field
            try:
                lbl = ctk.CTkLabel(dlg, text="镜像选择:") if ctk else tk.Label(dlg, text="镜像选择:")
                lbl.pack(padx=8, pady=(12,4), anchor="w")
            except:
                pass
            mirror_val = getattr(self, 'mirror_var', None)
            if mirror_val is None:
                mirror_val = ctk.StringVar(value=self.start_context.get('mirror','auto')) if ctk else tk.StringVar(value=self.start_context.get('mirror','auto'))
            try:
                if ctk:
                    menu = ctk.CTkOptionMenu(dlg, values=['auto','cn','global','official','huggingface'], variable=mirror_val)
                    menu.pack(padx=8, pady=4, fill='x')
                else:
                    menu = tk.OptionMenu(dlg, mirror_val, 'auto','cn','global','official','huggingface')
                    menu.pack(padx=8, pady=4, fill='x')
            except Exception:
                pass

            # zoom field
            try:
                lbl2 = ctk.CTkLabel(dlg, text="缩放:") if ctk else tk.Label(dlg, text="缩放:")
                lbl2.pack(padx=8, pady=(12,4), anchor="w")
            except:
                pass
            zoom_val = getattr(self, 'zoom_var', None)
            if zoom_val is None:
                zoom_val = ctk.StringVar(value=self.start_context.get('zoom','100%')) if ctk else tk.StringVar(value=self.start_context.get('zoom','100%'))
            try:
                zoom_values = ['80%','90%','100%','110%','125%','150%']
                if ctk:
                    zm = ctk.CTkOptionMenu(dlg, values=zoom_values, variable=zoom_val)
                    zm.pack(padx=8, pady=4, fill='x')
                else:
                    zm = tk.OptionMenu(dlg, zoom_val, *zoom_values)
                    zm.pack(padx=8, pady=4, fill='x')
            except Exception:
                pass

            # device field
            try:
                lbl3 = ctk.CTkLabel(dlg, text="默认设备:") if ctk else tk.Label(dlg, text="默认设备:")
                lbl3.pack(padx=8, pady=(12,4), anchor="w")
            except:
                pass
            device_val = getattr(self, 'device_var', None)
            if device_val is None:
                device_val = ctk.StringVar(value=self.start_context.get('device','CPU')) if ctk else tk.StringVar(value=self.start_context.get('device','CPU'))
            try:
                devs = ['CPU','Auto','GPU - Intel','GPU - Nvidia','GPU - AMD']
                if ctk:
                    dv = ctk.CTkOptionMenu(dlg, values=devs, variable=device_val)
                    dv.pack(padx=8, pady=4, fill='x')
                else:
                    dv = tk.OptionMenu(dlg, device_val, *devs)
                    dv.pack(padx=8, pady=4, fill='x')
            except Exception:
                pass

            # window geometry
            try:
                lbl4 = ctk.CTkLabel(dlg, text="窗口大小 (WxH 或 geometry):") if ctk else tk.Label(dlg, text="窗口大小 (WxH 或 geometry):")
                lbl4.pack(padx=8, pady=(12,4), anchor="w")
            except:
                pass
            geom_var = tk.StringVar(value=self.start_context.get('window_geometry',''))
            try:
                if ctk:
                    entry = ctk.CTkEntry(dlg, textvariable=geom_var)
                    entry.pack(padx=8, pady=4, fill='x')
                else:
                    entry = tk.Entry(dlg, textvariable=geom_var)
                    entry.pack(padx=8, pady=4, fill='x')
            except Exception:
                pass

            # HF 镜像基址
            try:
                lbl5 = ctk.CTkLabel(dlg, text="HF 镜像基址 (可选):") if ctk else tk.Label(dlg, text="HF 镜像基址 (可选):")
                lbl5.pack(padx=8, pady=(12,4), anchor='w')
            except:
                pass
            hf_base_var = tk.StringVar(value=self.start_context.get('hf_api_base',''))
            try:
                if ctk:
                    hf_entry = ctk.CTkEntry(dlg, textvariable=hf_base_var)
                    hf_entry.pack(padx=8, pady=4, fill='x')
                else:
                    hf_entry = tk.Entry(dlg, textvariable=hf_base_var)
                    hf_entry.pack(padx=8, pady=4, fill='x')
            except:
                pass

            # 快速预设：使用推荐的中国镜像（包含 /api 路径）
            try:
                def use_recommended_mirror():
                    try:
                        hf_base_var.set('https://hf-mirror.com/api')
                    except Exception:
                        pass
                if ctk:
                    preset_btn = ctk.CTkButton(dlg, text="使用推荐中国镜像", command=use_recommended_mirror)
                    preset_btn.pack(padx=8, pady=4, fill='x')
                else:
                    preset_btn = tk.Button(dlg, text="使用推荐中国镜像", command=use_recommended_mirror)
                    preset_btn.pack(padx=8, pady=4, fill='x')
            except Exception:
                pass

            def use_current_geometry():
                try:
                    geom = self.root.geometry() if hasattr(self, 'root') and self.root else None
                    if geom:
                        geom_var.set(geom)
                except:
                    pass
            try:
                if ctk:
                    cur_geom_btn = ctk.CTkButton(dlg, text="使用当前窗口大小", command=use_current_geometry)
                    cur_geom_btn.pack(padx=8, pady=4, fill='x')
                else:
                    cur_geom_btn = tk.Button(dlg, text="使用当前窗口大小", command=use_current_geometry)
                    cur_geom_btn.pack(padx=8, pady=4, fill='x')
            except Exception:
                pass

            def do_save():
                try:
                    m = mirror_val.get()
                    z = zoom_val.get()
                    d = device_val.get() if device_val is not None else self.start_context.get('device','CPU')
                    wg = geom_var.get()
                    try:
                        if hasattr(self, 'mirror_var'):
                            self._safe_set_var(self.mirror_var, m)
                        else:
                            self.start_context['mirror'] = m
                        if hasattr(self, 'zoom_var'):
                            self._safe_set_var(self.zoom_var, z)
                        else:
                            self.start_context['zoom'] = z
                        try:
                            if hasattr(self, 'device_var'):
                                self._safe_set_var(self.device_var, d)
                                if hasattr(self, 'device_label') and self.device_label:
                                    self._safe_set(self.device_label, f"设备: {d}")
                            else:
                                self.start_context['device'] = d
                        except:
                            pass
                        try:
                            # persist HF api base if provided
                            if hf_base_var and hf_base_var.get():
                                self.start_context['hf_api_base'] = hf_base_var.get().strip()
                            else:
                                # remove if empty
                                if 'hf_api_base' in self.start_context:
                                    del self.start_context['hf_api_base']
                        except:
                            pass
                        try:
                            if wg:
                                self.start_context['window_geometry'] = wg
                                if hasattr(self, 'root') and self.root and wg:
                                    try:
                                        self.root.geometry(wg)
                                    except:
                                        pass
                        except:
                            pass
                    except Exception:
                        pass
                    try:
                        from app.ui_prefs import save_prefs
                        save_prefs(self.start_context)
                    except Exception:
                        pass
                    try:
                        messagebox.showinfo('设置', '已保存')
                    except Exception:
                        pass
                except:
                    pass

            def do_restore():
                try:
                    if hasattr(self, 'mirror_var'):
                        self._safe_set_var(self.mirror_var, 'auto')
                    else:
                        self.start_context['mirror'] = 'auto'
                    if hasattr(self, 'zoom_var'):
                        self._safe_set_var(self.zoom_var, '100%')
                    else:
                        self.start_context['zoom'] = '100%'
                    try:
                        from app.ui_prefs import save_prefs
                        save_prefs(self.start_context)
                    except Exception:
                        pass
                except:
                    pass

            btn_frame = ctk.CTkFrame(dlg) if ctk else tk.Frame(dlg)
            btn_frame.pack(padx=8, pady=12, fill='x')
            if ctk:
                sbtn = ctk.CTkButton(btn_frame, text='保存', command=do_save)
                sbtn.pack(side='left', padx=6)
                rbtn = ctk.CTkButton(btn_frame, text='恢复默认', command=do_restore)
                rbtn.pack(side='left', padx=6)
                cbtn = ctk.CTkButton(btn_frame, text='关闭', command=dlg.destroy)
                cbtn.pack(side='right', padx=6)
            else:
                sbtn = tk.Button(btn_frame, text='保存', command=do_save)
                sbtn.pack(side='left', padx=6)
                rbtn = tk.Button(btn_frame, text='恢复默认', command=do_restore)
                rbtn.pack(side='left', padx=6)
                cbtn = tk.Button(btn_frame, text='关闭', command=dlg.destroy)
                cbtn.pack(side='right', padx=6)
        except Exception:
            pass

    def _on_mirror_change(self):
        try:
            val = self.mirror_var.get() if hasattr(self, 'mirror_var') else None
            # update status and persist to start_context
            if val:
                try:
                    self._safe_set(self.status_label, f"镜像: {val}")
                except:
                    try:
                        self.status_label.config(text=f"镜像: {val}")
                    except Exception:
                        pass
                try:
                    if isinstance(self.start_context, dict):
                        self.start_context['mirror'] = val
                        try:
                            from app.ui_prefs import save_prefs
                            save_prefs(self.start_context)
                        except Exception:
                            pass
                except:
                    pass
        except:
            pass

    def _on_zoom_change(self):
        try:
            # apply zoom immediately
            self._apply_zoom()
            try:
                cur = self.zoom_var.get() if hasattr(self, 'zoom_var') else '100%'
                self._safe_set(self.status_label, f"缩放: {cur}")
                try:
                    if isinstance(self.start_context, dict):
                        self.start_context['zoom'] = cur
                        from app.ui_prefs import save_prefs
                        save_prefs(self.start_context)
                except Exception:
                    pass
            except:
                pass
        except:
            pass

    def _apply_zoom(self):
        """Apply zoom preset by adjusting Tk default font or CTk scaling where possible."""
        try:
            z = self.zoom_var.get() if hasattr(self, 'zoom_var') else '100%'
            pct = int(str(z).strip('%'))
        except:
            pct = 100
        # compute scale factor relative to 100
        scale = pct / 100.0
        # For CTk: there's no global font API; attempt to scale common widgets via option_add on underlying tk root
        try:
            base_size = 10
            new_size = max(8, int(base_size * scale))
            if tk and self.root is not None:
                try:
                    default_font = tkfont.nametofont("TkDefaultFont")
                    default_font.configure(size=new_size)
                except Exception:
                    try:
                        font_family = 'TkDefaultFont'
                        if 'default_font' in locals():
                            try:
                                try:
                                    font_family = default_font.actual('family')  # type: ignore
                                except:
                                    font_family = 'TkDefaultFont'
                            except:
                                pass
                        self.root.option_add("*Font", (font_family, new_size))
                    except Exception:
                        pass
            # update status
            try:
                if ctk:
                    self.status_label.configure(text=f"缩放: {pct}% (字体大小 {new_size})")
                else:
                    self.status_label.config(text=f"缩放: {pct}% (字体大小 {new_size})")
            except:
                pass
        except Exception as e:
            try:
                if ctk:
                    self.status_label.configure(text=f"应用缩放失败: {e}")
                else:
                    self.status_label.config(text=f"应用缩放失败: {e}")
            except:
                pass

    def _select_input_file(self):
        """选择推理输入文件（图片）"""
        path = filedialog.askopenfilename(parent=self.root, title="选择图片文件",
                                          filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All", "*.*")])
        if path:
            self.selected_file = path
            try:
                if ctk:
                    self.details.configure(text=f"已选择: {Path(path).name}")
                    self.status_label.configure(text=f"已选择文件: {Path(path).name}")
                else:
                    self.details.config(text=f"已选择: {Path(path).name}")
                    self.status_label.config(text=f"已选择文件: {Path(path).name}")
            except:
                pass

    def _map_device_to_env(self, device_choice: str):
        """将设备选择映射到 model_invoker 中的环境名；返回 None 表示使用自动选择逻辑"""
        if not device_choice:
            return None
        dc = device_choice.lower()
        if "nvidia" in dc or "cuda" in dc:
            return "yolov5-cuda"
        if "rocm" in dc:
            return "yolov8-rocm"
        if "intel" in dc or "integrated" in dc:
            return "ppyolo-xpu"
        if dc.strip() == "cpu":
            return "ppyolo-xpu"
        if dc.strip() == "auto":
            return None
        return None

    def _on_download_selected_model(self):
        sel = self.model_var.get() if hasattr(self, 'model_var') else None
        if not sel or sel == '自动选择':
            try:
                messagebox.showinfo('下载模型', '未选择模型')
            except:
                pass
            return
        model_id = sel.split('(')[-1].strip(')')

        def worker():
            td = Path('temp') / 'models_downloads'
            td.mkdir(parents=True, exist_ok=True)
            saved_path = None

            # 1) 尝试使用 hf_browser.download_repo
            try:
                if hf_browser and hasattr(hf_browser, 'download_repo'):
                    dest = td / model_id.replace('/', '_')
                    dest.mkdir(parents=True, exist_ok=True)
                    ok = hf_browser.download_repo(model_id, dest)
                    if ok:
                        saved_path = str(dest)
            except Exception:
                saved_path = None

            # 2) 回退到 download_model
            if not saved_path:
                try:
                    if 'download_model' in globals() and callable(download_model):
                        p = download_model(model_id, mirror=_resolve_mirror_choice(self.mirror_var.get() if hasattr(self, 'mirror_var') else 'auto'))
                        # download_model may return a path or None
                        if p:
                            try:
                                src = Path(p)
                                dest = td / src.name
                                if src.exists():
                                    try:
                                        shutil.move(str(src), str(dest))
                                        saved_path = str(dest)
                                    except Exception:
                                        saved_path = str(src)
                                else:
                                    saved_path = str(p)
                            except Exception:
                                saved_path = str(p)
                except Exception:
                    saved_path = None

            # update UI status
            try:
                if saved_path:
                    if ctk:
                        self.status_label.configure(text=f'已下载到: {saved_path}')
                    else:
                        self.status_label.config(text=f'已下载到: {saved_path}')
                else:
                    if ctk:
                        self.status_label.configure(text='下载失败（请打开 HF 浏览器 手动下载）')
                    else:
                        self.status_label.config(text='下载失败（请打开 HF 浏览器 手动下载）')
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_use_selected_model(self):
        sel = self.model_var.get() if hasattr(self, 'model_var') else None
        if not sel or sel == '自动选择':
            try:
                messagebox.showinfo('使用模型', '未选择模型')
            except:
                pass
            return
        model_id = sel.split('(')[-1].strip(')')
        # save mapping to current device selection
        try:
            mapping = self._load_model_device_map()
            mapping[model_id] = self.device_var.get() if hasattr(self, 'device_var') else 'CPU'
            self._save_model_device_map(mapping)
            try:
                if ctk:
                    self.status_label.configure(text=f'已设置模型 {model_id} 的设备映射')
                else:
                    self.status_label.config(text=f'已设置模型 {model_id} 的设备映射')
            except:
                pass
        except:
            pass

    def _on_import_downloaded_model(self):
        """导入已下载到 temp/models_downloads 中的模型文件或目录（用户选择）"""
        root = self.root if hasattr(self, 'root') else None
        base = Path('temp') / 'models_downloads'
        if not base.exists():
            try:
                messagebox.showinfo('导入', '没有找到已下载的模型目录 (temp/models_downloads)')
            except:
                pass
            return
        # Let user select a file inside the downloads folder
        path = filedialog.askopenfilename(initialdir=str(base), parent=root, title='选择要导入的模型文件或仓库内文件')
        if not path:
            return

        def worker():
            try:
                res = import_local_model(path)
                if res:
                    try:
                        if ctk:
                            self.status_label.configure(text=f'已导入: {Path(res).name}')
                        else:
                            self.status_label.config(text=f'已导入: {Path(res).name}')
                    except Exception:
                        pass
                else:
                    try:
                        if ctk:
                            self.status_label.configure(text='导入失败')
                        else:
                            self.status_label.config(text='导入失败')
                    except Exception:
                        pass
            except Exception as e:
                try:
                    if ctk:
                        self.status_label.configure(text=f'导入异常: {e}')
                    else:
                        self.status_label.config(text=f'导入异常: {e}')
                except:
                    pass
            try:
                self.refresh_local()
            except:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_open_model_folder(self):
        # Attempt to open models resource folder or local model path
        try:
            models_dir = Path('resources') / 'models'
            if not models_dir.exists():
                models_dir = Path('models')
            if models_dir.exists():
                try:
                    # open folder using platform-appropriate command
                    if platform.system().lower().startswith('win'):
                        subprocess.Popen(['explorer', str(models_dir)])
                    elif platform.system().lower().startswith('darwin'):
                        subprocess.Popen(['open', str(models_dir)])
                    else:
                        subprocess.Popen(['xdg-open', str(models_dir)])
                except Exception:
                    try:
                        messagebox.showinfo('打开目录', f'模型目录: {models_dir}')
                    except Exception:
                        pass
            else:
                try:
                    messagebox.showinfo('打开目录', '未找到模型目录')
                except:
                    pass
        except:
            pass

    def _start_inference(self):
        """开始推理：根据模型->设备映射选择环境或使用自动选择"""
        if model_invoker is None:
            msg = "模型调用器不可用（core.model_invoker 未加载）"
            try:
                if ctk:
                    self.status_label.configure(text=msg)
                else:
                    self.status_label.config(text=msg)
            except:
                pass
            return

        if not self.selected_file:
            try:
                if ctk:
                    messagebox.showwarning("未选择文件", "请先选择输入图片文件")
                else:
                    messagebox.showwarning("未选择文件", "请先选择输入图片文件")
            except:
                pass
            return

        sel = self.model_var.get()
        model_id = None
        if sel and sel != "自动选择":
            model_id = sel.split('(')[-1].strip(')')

        # 从映射配置获取设备选择
        mapping = self._load_model_device_map()
        device_choice = None
        if model_id:
            device_choice = mapping.get(model_id)
        if not device_choice:
            device_choice = self.device_var.get() if hasattr(self, "device_var") else None

        env_name = self._map_device_to_env(device_choice if device_choice is not None else 'CPU')

        # 回调用于接收异步结果
        def cb(result, err):
            try:
                if err:
                    text = f"推理失败: {err}"
                else:
                    # 简化显示：若为 dict，显示摘要
                    summary = result if not isinstance(result, dict) else f"objects={len(result.get('detections', []))}"
                    text = f"推理完成: {summary}"
                if ctk:
                    self.status_label.configure(text=text)
                    self.details.configure(text=text)
                else:
                    self.status_label.config(text=text)
                    self.details.config(text=text)
                try:
                    if err:
                        messagebox.showerror("推理错误", str(err))
                    else:
                        messagebox.showinfo("推理完成", "推理已完成，结果已显示到界面（详情见控制台或日志）")
                except:
                    pass
            except:
                pass

        try:
            if env_name:
                try:
                    if ctk:
                        self.status_label.configure(text=f"使用环境 {env_name} 进行推理...")
                    else:
                        self.status_label.config(text=f"使用环境 {env_name} 进行推理...")
                except:
                    pass
                model_invoker.invoke_model_async(env_name, self.selected_file, callback=cb)
            else:
                try:
                    if ctk:
                        self.status_label.configure(text="自动选择最佳环境并推理...")
                    else:
                        self.status_label.config(text="自动选择最佳环境并推理...")
                except:
                    pass
                # model_invoker 支持 invoke_best_model 但 not async wrapper; call invoke_model_async with None -> use invoke_best_model
                try:
                    model_invoker.invoke_model_async("auto", self.selected_file, callback=cb)
                    # 如果 invoke_model_async doesn't support "auto", invoke_best_model in a thread
                except Exception:
                    def wrapper():
                        try:
                            if model_invoker is not None:
                                res, used = model_invoker.invoke_best_model(self.selected_file)
                                cb(res, None)
                        except Exception as e:
                            cb(None, str(e))
                    threading.Thread(target=wrapper, daemon=True).start()
        except Exception as e:
            try:
                if ctk:
                    self.status_label.configure(text=f"启动推理失败: {e}")
                else:
                    self.status_label.config(text=f"启动推理失败: {e}")
            except:
                pass

        # populate models
        self.refresh_model_list()

    def _load_model_device_map(self):
        """加载 config/model_device_map.yaml 并返回 dict"""
        try:
            p = Path("config") / "model_device_map.yaml"
            if not p.exists():
                return {}
            if yaml:
                with p.open("r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            else:
                # 简单解析：每行 key: value
                mapping = {}
                with p.open("r", encoding="utf-8") as f:
                    for line in f:
                        if ':' in line:
                            k, v = line.split(':', 1)
                            mapping[k.strip()] = v.strip()
                return mapping
        except Exception:
            return {}

    def _save_model_device_map(self, mapping: dict):
        """将模型->设备映射保存到 config/model_device_map.yaml"""
        try:
            p = Path("config")
            p.mkdir(parents=True, exist_ok=True)
            target = p / "model_device_map.yaml"
            if yaml:
                with target.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(mapping, f, allow_unicode=True, sort_keys=False)
            else:
                with target.open("w", encoding="utf-8") as f:
                    for k, v in mapping.items():
                        f.write(f"{k}: {v}\n")
        except Exception as e:
            try:
                if ctk:
                    self.status_label.configure(text=f"保存映射失败: {e}")
                else:
                    self.status_label.config(text=f"保存映射失败: {e}")
            except:
                pass

    def refresh_local(self):
        """Refresh local models"""
        # Implementation goes here
        pass

    def _on_reload_fonts(self):
        """在后台调用字体初始化并更新状态标签，尝试在 Tk/CTk 环境中应用找到的字体文件"""
        def worker():
            status = ""
            try:
                if initialize_chinese_font:
                    ok = initialize_chinese_font(project_root)
                    status = "字体加载成功" if ok else "字体加载失败"
                else:
                    status = "字体初始化不可用（可能缺少 dearpygui）"
            except Exception as e:
                status = f"字体初始化异常: {e}"

            # 尝试使用 debug 接口获取选中的 font_path，并在 Tk 中应用（作为回退）
            try:
                if initialize_chinese_font_debug:
                    info = initialize_chinese_font_debug(project_root)
                    fp = info.get("font_path")
                    if fp and tk:
                        try:
                            family = Path(fp).stem
                            # 1) 尝试配置 TkDefaultFont（更改现有默认字体对象）
                            try:
                                default_font = tkfont.nametofont("TkDefaultFont")
                                default_font.configure(family=family)
                                status += "；尝试在 TkDefaultFont 中应用字体"
                            except Exception:
                                # 2) 回退：使用 option_add 设置全局字体样式
                                try:
                                    if self.root is not None:
                                        self.root.option_add("*Font", (family, 10))
                                    status += "；已通过 option_add 设置字体"
                                except Exception as e2:
                                    status += f"；设置 Tk 字体失败: {e2}"
                        except Exception as e:
                            status += f"；解析字体路径失败: {e}"
            except Exception:
                # 忽略任何 debug 获取或应用过程中的错误
                pass

            try:
                if ctk:
                    self.status_label.configure(text=status)
                else:
                    self.status_label.config(text=status)
            except:
                pass
            # Best-effort: if a rebind helper exists, call it to apply fonts to the running UI
            try:
                if rebind_default_font:
                    try:
                        if hasattr(self, 'root') and self.root is not None:
                            rebind_default_font(self.root)  # type: ignore
                        else:
                            # fallback: attempt a no-arg call
                            rebind_default_font()
                    except:
                        try:
                            # fallback: attempt a no-arg call
                            rebind_default_font()
                        except:
                            pass
            except:
                pass

        # ensure the worker thread is started regardless of prior try/except
        threading.Thread(target=worker, daemon=True).start()

    def _on_prepare_env(self):
        """打开准备环境对话并异步执行 prepare_environment，显示回调进度"""
        if OnDemandEnvironmentManager is None:
            message = "按需环境管理不可用（缺少 core.on_demand_environment_manager）"
            try:
                if ctk:
                    self.status_label.configure(text=message)
                else:
                    self.status_label.config(text=message)
            except:
                pass

            # settings dialog moved to class-level open_settings_dialog
            pass
        except Exception:
            pass
        
    def open_hf_browser(self):
        try:
            dlg = ctk.CTkToplevel(self.root) if ctk else tk.Toplevel(self.root)
            dlg.title("HuggingFace 浏览器")
            dlg.geometry("720x480")

            # search area
            try:
                if ctk:
                    s_frame = ctk.CTkFrame(dlg)
                    s_frame.pack(fill='x', padx=8, pady=8)
                    query_var = ctk.StringVar(value='')
                    s_entry = ctk.CTkEntry(s_frame, textvariable=query_var)
                    s_entry.pack(side='left', expand=True, fill='x', padx=(0,8))
                    s_btn = ctk.CTkButton(s_frame, text='搜索', command=lambda: do_search())
                    s_btn.pack(side='right')
                else:
                    s_frame = tk.Frame(dlg)
                    s_frame.pack(fill='x', padx=8, pady=8)
                    query_var = tk.StringVar(value='')
                    s_entry = tk.Entry(s_frame, textvariable=query_var)
                    s_entry.pack(side='left', expand=True, fill='x', padx=(0,8))
                    s_btn = tk.Button(s_frame, text='搜索', command=lambda: do_search())
                    s_btn.pack(side='right')
            except:
                query_var = tk.StringVar(value='')

            # layout: left=results, right=details+files
            try:
                main_frame = tk.Frame(dlg)
                main_frame.pack(fill='both', expand=True, padx=8, pady=4)

                results_frame = tk.Frame(main_frame)
                results_frame.pack(side='left', fill='both', expand=True)
                results_box = tk.Listbox(results_frame)
                results_box.pack(side='left', fill='both', expand=True)
                scrollbar = tk.Scrollbar(results_frame, command=results_box.yview)
                scrollbar.pack(side='right', fill='y')
                results_box.config(yscrollcommand=scrollbar.set)

                # right pane for metadata and files
                details_frame = tk.Frame(main_frame, width=380)
                details_frame.pack(side='right', fill='y')

                # metadata display (title/description + README)
                meta_text = tk.Text(details_frame, height=8, wrap='word')
                meta_text.pack(fill='x', padx=4, pady=4)

                # files box with multi-select and scrollbar
                files_label = tk.Label(details_frame, text='文件:')
                files_label.pack(anchor='w', padx=4)
                files_box = tk.Listbox(details_frame, selectmode='multiple', height=10)
                files_box.pack(fill='both', expand=False, padx=4, pady=4)
                files_scroll = tk.Scrollbar(details_frame, command=files_box.yview)
                files_scroll.pack(side='right', fill='y')
                files_box.config(yscrollcommand=files_scroll.set)
            except Exception:
                # fallback to simple single-column layout
                results_frame = tk.Frame(dlg)
                results_frame.pack(fill='both', expand=True, padx=8, pady=4)
                results_box = tk.Listbox(results_frame)
                results_box.pack(side='left', fill='both', expand=True)
                scrollbar = tk.Scrollbar(results_frame, command=results_box.yview)
                scrollbar.pack(side='right', fill='y')
                results_box.config(yscrollcommand=scrollbar.set)
                files_box = tk.Listbox(dlg)
                files_box.pack(fill='both', expand=False, padx=8, pady=4)
                meta_text = None

            def do_search():
                q = query_var.get() if hasattr(query_var, 'get') else ''
                if not q:
                    return
                try:
                    # prefer explicit hf_api_base from prefs
                    api_base = None
                    try:
                        explicit = self.start_context.get('hf_api_base') if isinstance(self.start_context, dict) else None
                        if explicit:
                            api_base = explicit.rstrip('/')
                        else:
                            mirror_choice_raw = self.mirror_var.get() if hasattr(self, 'mirror_var') else 'auto'
                            mc = _resolve_mirror_choice(mirror_choice_raw)
                            if isinstance(mc, str) and mc.startswith('http'):
                                api_base = mc.rstrip('/') + '/api'
                    except:
                        api_base = None
                    results = hf_browser.search_models(q, limit=30, api_base=api_base) if hf_browser else []
                except:
                    results = []
                try:
                    import logging
                    logging.getLogger().debug(f"HF search got {len(results)} results for query '{q}'")
                    if results_box is not None:
                        results_box.delete(0, 'end')
                        for r in results:
                            display = f"{r.get('modelId')} - {r.get('pipeline_tag') or r.get('task') or ''}"
                            results_box.insert('end', display)
                except Exception:
                    import traceback
                    traceback.print_exc()

                # attach result metadata
                setattr(dlg, '_hf_results', results)

            def on_result_select(evt=None):
                try:
                    sel = None
                    if ctk:
                        # parse selected line from textbox by cursor
                        try:
                            idx = results_box.index('insert')
                            line = results_box.get(str(idx) + ' linestart', str(idx) + ' lineend')
                            sel = line.split('-')[0].strip()
                        except:
                            sel = None
                    else:
                        s = results_box.curselection()
                        if s:
                            sel = results_box.get(s[0])
                    if not sel:
                        return
                    results = getattr(dlg, '_hf_results', []) or []
                    repo = None
                    for r in results:
                        if r.get('modelId') == sel:
                            repo = r
                            break
                    if not repo:
                        return
                    api_base = None
                    try:
                        explicit = self.start_context.get('hf_api_base') if isinstance(self.start_context, dict) else None
                        if explicit:
                            api_base = explicit.rstrip('/')
                        else:
                            mirror_choice_raw = self.mirror_var.get() if hasattr(self, 'mirror_var') else 'auto'
                            mc = _resolve_mirror_choice(mirror_choice_raw)
                            if isinstance(mc, str) and mc.startswith('http'):
                                api_base = mc.rstrip('/') + '/api'
                    except:
                        api_base = None
                    # fetch metadata and files with sizes
                    meta = hf_browser.get_model_metadata(sel, api_base=api_base) if hf_browser else {}
                    files = hf_browser.list_model_files(sel, api_base=api_base) if hf_browser else []
                    # show metadata and README
                    try:
                        if meta_text is not None:
                            meta_text.delete('1.0', 'end')
                            title = meta.get('modelId') or sel
                            desc = meta.get('pipeline_tag') or meta.get('task') or meta.get('description') or ''
                            meta_text.insert('1.0', f"{title}\n\n{desc}\n\n")
                            # try to fetch README if available (do this asynchronously to avoid UI freeze)
                            try:
                                def fetch_and_show_readme(repo_id=sel, api_base_local=api_base, target_widget=meta_text):
                                    try:
                                        readme = hf_browser.get_model_readme(repo_id, api_base=api_base_local) if hf_browser else ''
                                    except Exception:
                                        readme = ''
                                    if not readme:
                                        return
                                    def _show():
                                        try:
                                            target_widget.insert('end', "--- README (preview) ---\n")
                                            # try to render markdown to HTML when possible
                                            html = None
                                            try:
                                                from markdown import markdown as _md
                                                html = _md(readme)
                                            except Exception:
                                                html = None
                                            try:
                                                # prefer HTML rendering if tkhtmlview present
                                                try:
                                                    from tkhtmlview import HTMLLabel
                                                    pv = tk.Toplevel(dlg)
                                                    pv.title(f"README: {repo_id}")
                                                    h = HTMLLabel(pv, html=html or ('<pre>' + readme + '</pre>'))
                                                    h.pack(fill='both', expand=True)
                                                except ImportError:
                                                    # tkhtmlview not available, use plain text
                                                    target_widget.insert('end', readme[:20000])
                                            except Exception:
                                                # fallback: insert plain text excerpt in the meta box
                                                target_widget.insert('end', readme[:20000])
                                        except Exception:
                                            pass
                                    try:
                                        if self.root is not None:
                                            self.root.after(1, _show)
                                        else:
                                            _show()
                                    except Exception:
                                        _show()
                                threading.Thread(target=fetch_and_show_readme, daemon=True).start()
                            except:
                                pass
                    except Exception:
                        pass
                    files_box.delete(0, 'end')
                    # recommended patterns
                    recommended = ['README', 'README.md', 'config.json', 'pytorch_model.bin', 'model_index.json', 'adapter_config.json']
                    for f in files:
                        name = f.get('name') if isinstance(f, dict) else str(f)
                        size = f.get('size') if isinstance(f, dict) else None
                        size_str = f" ({size} bytes)" if size else ''
                        display = f"{name}{size_str}"
                        files_box.insert('end', display)
                    # auto-select recommended files
                    try:
                        for idx in range(files_box.size()):
                            val = files_box.get(idx)
                            for pat in recommended:
                                if pat.lower() in val.lower():
                                    files_box.select_set(idx)
                                    break
                    except Exception:
                        pass

                    # add quick action buttons below files: select recommended / clear
                    try:
                        def select_recommended():
                            try:
                                for idx in range(files_box.size()):
                                    val = files_box.get(idx)
                                    for pat in recommended:
                                        if pat.lower() in val.lower():
                                            files_box.select_set(idx)
                                            break
                            except Exception:
                                pass

                        def clear_selection():
                            try:
                                files_box.selection_clear(0, 'end')
                            except:
                                pass

                        sel_frame = tk.Frame(details_frame)
                        sel_frame.pack(fill='x', padx=4, pady=(2,8))
                        sel_btn = tk.Button(sel_frame, text='选择推荐', command=select_recommended)
                        sel_btn.pack(side='left', padx=4)
                        clr_btn = tk.Button(sel_frame, text='清除选择', command=clear_selection)
                        clr_btn.pack(side='left', padx=4)

                        def preview_selected():
                            try:
                                sel_repo = getattr(dlg, '_hf_selected', None)
                                if not sel_repo:
                                    return
                                # Add your code here


# Make sure the file ends with a newline
