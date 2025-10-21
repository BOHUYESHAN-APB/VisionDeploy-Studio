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

def _noop(*a, **k):
    return None

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


class ModelManagerDialog(ctk.CTkToplevel if ctk else tk.Toplevel):
    def __init__(self, parent=None):
        if ctk:
            super().__init__(parent)
            self.geometry("720x420")
        else:
            super().__init__(parent)
            self.geometry("720x420")
        self.title("模型管理")
        self.parent = parent
        # try to capture mirror preference from parent
        try:
            self.preferred_mirror = getattr(parent, 'mirror_var', None)
        except Exception:
            self.preferred_mirror = None

        # UI components
        if ctk:
            self.model_var = ctk.StringVar(value="无可用模型")
            self.model_menu = ctk.CTkOptionMenu(self, values=["无可用模型"], variable=self.model_var)
            self.model_menu.pack(padx=10, pady=8, fill="x")

            btn_frame = ctk.CTkFrame(self)
            btn_frame.pack(fill="x", padx=10, pady=6)
            self.download_btn = ctk.CTkButton(btn_frame, text="下载所选模型", command=self.on_download)
            self.import_btn = ctk.CTkButton(btn_frame, text="导入本地模型", command=self.on_import_local)
            self.close_btn = ctk.CTkButton(btn_frame, text="关闭", command=self.destroy)
            self.download_btn.pack(side="left", padx=6, pady=6)
            self.import_btn.pack(side="left", padx=6, pady=6)
            self.close_btn.pack(side="right", padx=6, pady=6)

            self.local_list = ctk.CTkTextbox(self, width=1, height=10)
            self.local_list.pack(expand=True, fill="both", padx=10, pady=8)
            self.status = ctk.CTkLabel(self, text="")
            self.status.pack(padx=10, pady=6, anchor="w")
        else:
            self.model_var = tk.StringVar(value="无可用模型")
            self.model_menu = tk.OptionMenu(self, self.model_var, "无可用模型")
            self.model_menu.pack(padx=10, pady=8, fill="x")

            btn_frame = tk.Frame(self)
            btn_frame.pack(fill="x", padx=10, pady=6)
            self.download_btn = tk.Button(btn_frame, text="下载所选模型", command=self.on_download)
            self.import_btn = tk.Button(btn_frame, text="导入本地模型", command=self.on_import_local)
            self.close_btn = tk.Button(btn_frame, text="关闭", command=self.destroy)
            self.download_btn.pack(side="left", padx=6, pady=6)
            self.import_btn.pack(side="left", padx=6, pady=6)
            self.close_btn.pack(side="right", padx=6, pady=6)

            self.local_list = tk.Listbox(self)
            self.local_list.pack(expand=True, fill="both", padx=10, pady=8)
            self.status = tk.Label(self, text="")
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
            self.model_menu.configure(values=items)
            if items:
                self.model_var.set(items[0])
        else:
            menu = self.model_menu["menu"]
            menu.delete(0, "end")
            for it in items:
                menu.add_command(label=it, command=lambda v=it: self.model_var.set(v))
            if items:
                self.model_var.set(items[0])

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
                        self._download_progress = ctk.CTkProgressBar(self, width=680)
                        self._download_progress.set(0.0)
                        self._download_progress.pack(padx=10, pady=4, fill="x")
                    except Exception:
                        self._download_progress = None
                if self._download_progress:
                    try:
                        self._download_progress.set(0.2)
                    except:
                        pass
            else:
                self.download_btn.config(state="disabled")
                self.import_btn.config(state="disabled")
                if not hasattr(self, "_download_progress"):
                    try:
                        from tkinter import ttk
                        self._download_progress = ttk.Progressbar(self, orient="horizontal", length=680, mode="indeterminate")
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
                self._download_stop_event = stop_event
            except:
                pass

            def progress_cb(message, percent):
                # message: str, percent: int (0-100) or -1 for error/cancel
                try:
                    text = f"{message} ({percent}%)" if isinstance(percent, (int, float)) and percent >= 0 else str(message)
                    # update dialog status
                    try:
                        self._set_status(text)
                    except:
                        pass
                    # update parent status bar if available
                    try:
                        if hasattr(self, "parent") and getattr(self.parent, "status_label", None) is not None:
                            try:
                                if ctk:
                                    self.parent.status_label.configure(text=text)
                                else:
                                    self.parent.status_label.config(text=text)
                            except:
                                pass
                    except:
                        pass
                    # update progress bar if numeric percent provided
                    try:
                        if hasattr(self, "_download_progress") and self._download_progress:
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
                    except:
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
                                self.open_hf_browser()
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
            # 更新对话框内状态
            
            except:
                pass
            # 尝试更新父窗口的状态栏（若存在）
            try:
                if hasattr(self, "parent") and getattr(self.parent, "status_label", None) is not None:
                    try:
                        if ctk:
                            self.parent.status_label.configure(text=status_msg)
                        else:
                            self.parent.status_label.config(text=status_msg)
                    except:
                        pass
            except:
                pass
            # stop/cleanup progress and re-enable buttons
            try:
                if hasattr(self, "_download_progress") and self._download_progress:
                    try:
                        if ctk:
                            self._download_progress.set(1.0)
                        else:
                            try:
                                self._download_progress.stop()
                            except:
                                pass
                    except:
                        pass
                    try:
                        self._download_progress.destroy()
                    except:
                        pass
                    try:
                        del self._download_progress
                    except:
                        pass
                if ctk:
                    try:
                        self.download_btn.configure(state="normal")
                        self.import_btn.configure(state="normal")
                    except:
                        pass
                else:
                    try:
                        self.download_btn.config(state="normal")
                        self.import_btn.config(state="normal")
                    except:
                        pass
            except:
                pass
            # remove stop event handle if present
            try:
                if hasattr(self, "_download_stop_event"):
                    try:
                        del self._download_stop_event
                    except:
                        pass
            except:
                pass
            # refresh local list
            try:
                self.refresh_local()
            except:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def on_import_local(self):
        root = self
        path = filedialog.askopenfilename(parent=root, title="选择本地模型文件")
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
                    except:
                        pass
                    try:
                        from app.ui_prefs import save_prefs
                        save_prefs(self.start_context)
                    except:
                        pass
                    try:
                        messagebox.showinfo('设置', '已保存')
                    except:
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
                    except:
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
                    except:
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
            if tk:
                try:
                    default_font = tkfont.nametofont("TkDefaultFont")
                    default_font.configure(size=new_size)
                except Exception:
                    try:
                        self.root.option_add("*Font", (default_font.actual('family') if 'default_font' in locals() else 'TkDefaultFont', new_size))
                    except:
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
                    ok = hf_browser.download_repo(model_id, str(dest))
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
                    except:
                        pass
                else:
                    try:
                        if ctk:
                            self.status_label.configure(text='导入失败')
                        else:
                            self.status_label.config(text='导入失败')
                    except:
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
                    except:
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

        env_name = self._map_device_to_env(device_choice)

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
                        rebind_default_font(self.root if hasattr(self, 'root') else None)
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
                dlg._hf_results = results

            def on_result_select(evt=None):
                try:
                    sel = None
                    if ctk:
                        # parse selected line from textbox by cursor
                        try:
                            idx = results_box.index('insert')
                            line = results_box.get(idx + ' linestart', idx + ' lineend')
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
                                                from tkhtmlview import HTMLLabel
                                                pv = tk.Toplevel(dlg)
                                                pv.title(f"README: {repo_id}")
                                                h = HTMLLabel(pv, html=html or ('<pre>' + readme + '</pre>'))
                                                h.pack(fill='both', expand=True)
                                            except Exception:
                                                # fallback: insert plain text excerpt in the meta box
                                                target_widget.insert('end', readme[:20000])
                                        except Exception:
                                            pass
                                    try:
                                        self.root.after(1, _show)
                                    except Exception:
                                        _show()
                                threading.Thread(target=fetch_and_show_readme, daemon=True).start()
                            except:
                                pass
                    except:
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
                    except:
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
                            except:
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
                                # determine api_base/raw base
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

                                # pick first selected file
                                idxs = files_box.curselection()
                                if not idxs:
                                    if files_box.size() == 0:
                                        return
                                    idx = 0
                                else:
                                    idx = idxs[0]
                                val = files_box.get(idx)
                                # extract filename before ' (' if present
                                fname = val.split(' (', 1)[0].strip()

                                # If the file looks like a README or text file, prefer hf_browser's readme getter
                                lower = fname.lower()
                                is_text_like = lower.startswith('readme') or lower.endswith(('.md', '.markdown', '.txt', '.json'))

                                def show_preview_content(content, content_type='text'):
                                    try:
                                        pv = tk.Toplevel(dlg)
                                        pv.title(f'预览: {fname}')
                                        if content_type == 'html':
                                            try:
                                                from tkhtmlview import HTMLLabel
                                                h = HTMLLabel(pv, html=content)
                                                h.pack(fill='both', expand=True)
                                                return
                                            except Exception:
                                                pass
                                        txt = tk.Text(pv, wrap='word')
                                        txt.pack(fill='both', expand=True)
                                        txt.insert('1.0', content[:20000])
                                    except Exception:
                                        pass

                                # fetch and show asynchronously to avoid blocking UI
                                def fetch_and_preview():
                                    r = None
                                    text_content = None
                                    try:
                                        if is_text_like and hf_browser:
                                            try:
                                                text_content = hf_browser.get_model_readme(sel_repo, api_base=api_base)
                                            except Exception:
                                                text_content = None
                                        # fallback to direct GET if we don't have content yet
                                        if not text_content:
                                            raw_base = 'https://huggingface.co'
                                            if api_base and isinstance(api_base, str) and api_base.startswith('http'):
                                                raw_base = api_base.rstrip('/')
                                                if raw_base.endswith('/api'):
                                                    raw_base = raw_base[:-4]
                                            url = f"{raw_base}/{sel_repo}/resolve/main/{fname}"
                                            import requests as _req
                                            try:
                                                r = _req.get(url, timeout=15, allow_redirects=True, headers={
                                                    'User-Agent': 'Mozilla/5.0',
                                                    'Accept': 'text/markdown, text/plain, */*',
                                                    'Referer': f'https://huggingface.co/{sel_repo}',
                                                })
                                            except Exception:
                                                r = None
                                            if r and r.status_code == 200:
                                                ctype = r.headers.get('Content-Type','')
                                                try:
                                                    if 'text' in ctype or 'markdown' in ctype or 'json' in ctype:
                                                        text_content = r.text
                                                except Exception:
                                                    text_content = None
                                    except Exception:
                                        pass

                                    if text_content:
                                        # try render markdown->html then show
                                        try:
                                            from markdown import markdown as _md
                                            html = None
                                            try:
                                                html = _md(text_content)
                                            except Exception:
                                                html = None
                                            if html:
                                                try:
                                                    self.root.after(1, lambda: show_preview_content(html, 'html'))
                                                    return
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                                        try:
                                            self.root.after(1, lambda: show_preview_content(text_content, 'text'))
                                        except Exception:
                                            show_preview_content(text_content, 'text')
                                    else:
                                        # no textual content; show binary/info message
                                        size = None
                                        try:
                                            size = r.headers.get('Content-Length') if r else None
                                        except Exception:
                                            size = None
                                        try:
                                            self.root.after(1, lambda: messagebox.showinfo('二进制文件', f'文件 {fname} 大小: {size or "未知"} 字节（未显示内容）'))
                                        except Exception:
                                            try:
                                                messagebox.showinfo('二进制文件', f'文件 {fname} 大小: {size or "未知"} 字节（未显示内容）')
                                            except:
                                                pass

                                try:
                                    threading.Thread(target=fetch_and_preview, daemon=True).start()
                                except Exception:
                                    pass
                            except:
                                pass

                        pv_btn = tk.Button(sel_frame, text='预览选中文件', command=preview_selected)
                        pv_btn.pack(side='left', padx=4)
                        dl_btn = tk.Button(sel_frame, text='下载到 temp (文件)', command=lambda: download_selected_to_temp(single=True))
                        dl_btn.pack(side='left', padx=4)
                        dl_repo_btn = tk.Button(sel_frame, text='下载到 temp (整仓)', command=lambda: download_selected_to_temp(single=False))
                        dl_repo_btn.pack(side='left', padx=4)

                        def download_selected_to_temp(single=True):
                            sel_repo = getattr(dlg, '_hf_selected', None)
                            if not sel_repo:
                                return
                            idxs = files_box.curselection()
                            chosen = []
                            if not idxs:
                                if files_box.size() == 0:
                                    return
                                chosen = [files_box.get(0).split(' (',1)[0].strip()]
                            else:
                                for i in idxs:
                                    chosen.append(files_box.get(i).split(' (',1)[0].strip())

                            def _worker():
                                td_base = Path('temp') / 'models_downloads'
                                td_base.mkdir(parents=True, exist_ok=True)
                                try:
                                    if single:
                                        fname = chosen[0]
                                        p = None
                                        try:
                                            if hf_browser and hasattr(hf_browser, 'download_file_to_temp'):
                                                p = hf_browser.download_file_to_temp(sel_repo, fname, td_base)
                                        except Exception:
                                            p = None
                                        if p:
                                            try:
                                                self._safe_set_status(f'已下载到: {p}')
                                                messagebox.showinfo('下载完成', f'已下载到: {p}')
                                            except:
                                                pass
                                        else:
                                            try:
                                                show_lfs_clone_dialog(sel_repo)
                                            except:
                                                try:
                                                    messagebox.showwarning('下载提示', '该文件可能由 Git LFS 托管或无法直接通过 HTTP 下载。请使用 git clone + git-lfs pull 获取完整内容。')
                                                except:
                                                    pass
                                    else:
                                        try:
                                            dest = td_base / sel_repo.replace('/', '_')
                                            dest.mkdir(parents=True, exist_ok=True)
                                            ok = None
                                            try:
                                                if hf_browser and hasattr(hf_browser, 'download_repo'):
                                                    ok = hf_browser.download_repo(sel_repo, dest)
                                            except Exception:
                                                ok = None
                                            if ok:
                                                try:
                                                    self._safe_set_status(f'已下载仓库到: {dest}')
                                                    messagebox.showinfo('下载完成', f'已下载仓库到: {dest}')
                                                except:
                                                    pass
                                            else:
                                                try:
                                                    show_lfs_clone_dialog(sel_repo)
                                                except:
                                                    try:
                                                        messagebox.showwarning('下载提示', '仓库下载未能完整获取（可能含 LFS 大文件）。请使用 git clone + git-lfs pull 获取完整模型。')
                                                    except:
                                                        pass
                                        except Exception:
                                            try:
                                                messagebox.showinfo('下载失败', '仓库下载失败')
                                            except:
                                                pass
                                except Exception:
                                    pass

                            try:
                                threading.Thread(target=_worker, daemon=True).start()
                            except Exception:
                                pass

                        def show_lfs_clone_dialog(repo_id: str):
                            """Show a small dialog with git clone + git-lfs commands for the repo."""
                            try:
                                cmds = []
                                clone_cmd = f"git clone https://huggingface.co/{repo_id}"
                                cmds.append(clone_cmd)
                                lfs_note = "# 然后进入目录并运行：\n# git lfs install && git lfs pull"
                                full_text = clone_cmd + "\n\n" + lfs_note

                                w = tk.Toplevel(dlg)
                                w.title('使用 git + git-lfs 获取模型')
                                w.geometry('640x240')
                                lbl = tk.Label(w, text=f'仓库: {repo_id}\n该仓库可能包含大文件(LFS)，请在终端执行以下命令以获取完整权重:')
                                lbl.pack(padx=8, pady=(8,4), anchor='w')
                                txt = tk.Text(w, height=6, wrap='none')
                                txt.pack(fill='both', expand=False, padx=8, pady=4)
                                txt.insert('1.0', full_text)
                                try:
                                    def do_copy():
                                        try:
                                            self.root.clipboard_clear()
                                            self.root.clipboard_append(full_text)
                                            messagebox.showinfo('已复制', '命令已复制到剪贴板')
                                        except:
                                            pass
                                    btn_frame2 = tk.Frame(w)
                                    btn_frame2.pack(fill='x', padx=8, pady=8)
                                    cpbtn = tk.Button(btn_frame2, text='复制命令到剪贴板', command=do_copy)
                                    cpbtn.pack(side='left')
                                except:
                                    pass
                            except Exception:
                                try:
                                    messagebox.showinfo('提示', f'请使用: git clone https://huggingface.co/{repo_id} 然后 git lfs pull')
                                except:
                                    pass
                        # 按钮：查看原始响应（展示 temp/hf_raw_responses 中保存的 HTML 响应）
                        def open_raw_responses_dialog():
                            try:
                                rr_dir = Path('temp') / 'hf_raw_responses'
                                if not rr_dir.exists() or not rr_dir.is_dir():
                                    try:
                                        messagebox.showinfo('原始响应', '未找到 temp/hf_raw_responses 目录或没有原始响应文件')
                                    except:
                                        pass
                                    return
                                files = sorted([p for p in rr_dir.glob('*') if p.is_file()], key=lambda x: x.name)
                                if not files:
                                    try:
                                        messagebox.showinfo('原始响应', '未发现原始响应文件')
                                    except:
                                        pass
                                    return
                                win = tk.Toplevel(dlg)
                                win.title('原始响应 - hf_raw_responses')
                                win.geometry('800x480')
                                # 左侧列表
                                leftf = tk.Frame(win, width=300)
                                leftf.pack(side='left', fill='y', padx=4, pady=4)
                                lb = tk.Listbox(leftf, width=40, height=24, selectmode='extended')
                                lb.pack(side='left', fill='y')
                                sb = tk.Scrollbar(leftf, command=lb.yview)
                                sb.pack(side='right', fill='y')
                                lb.config(yscrollcommand=sb.set)
                                for p in files:
                                    lb.insert('end', p.name)
                                # 右侧信息/预览区域
                                rightf = tk.Frame(win)
                                rightf.pack(side='right', fill='both', expand=True, padx=4, pady=4)
                                info_txt = tk.Text(rightf, wrap='word')
                                info_txt.pack(fill='both', expand=True, padx=4, pady=4)

                                # actions
                                af = tk.Frame(win)
                                af.pack(side='bottom', fill='x', padx=4, pady=6)

                                def refresh_listbox():
                                    try:
                                        files_local = sorted([p for p in rr_dir.glob('*') if p.is_file()], key=lambda x: x.name)
                                        lb.delete(0, 'end')
                                        for p in files_local:
                                            lb.insert('end', p.name)
                                    except:
                                        pass

                                def preview_selected_raw():
                                    seli = lb.curselection()
                                    if not seli:
                                        try:
                                            messagebox.showinfo('预览', '请选择一个文件用于预览')
                                        except:
                                            pass
                                        return
                                    p = rr_dir / lb.get(seli[0])
                                    try:
                                        content = p.read_text(encoding='utf-8', errors='ignore')
                                    except Exception as e:
                                        try:
                                            messagebox.showwarning('读取失败', f'无法读取文件: {e}')
                                        except:
                                            pass
                                        return
                                    # 尝试用 tkhtmlview 渲染 HTML；失败则用默认浏览器打开；最后回退到纯文本
                                    try:
                                        from tkhtmlview import HTMLLabel
                                        pv = tk.Toplevel(win)
                                        pv.title(f'原始响应预览: {p.name}')
                                        h = HTMLLabel(pv, html=content)
                                        h.pack(fill='both', expand=True)
                                        return
                                    except Exception:
                                        pass
                                    try:
                                        import webbrowser
                                        webbrowser.open(p.resolve().as_uri())
                                        return
                                    except Exception:
                                        pass
                                    try:
                                        info_txt.delete('1.0', 'end')
                                        info_txt.insert('1.0', content[:20000])
                                    except:
                                        pass

                                def show_analysis():
                                    seli = lb.curselection()
                                    targets = []
                                    if seli:
                                        targets = [rr_dir / lb.get(seli[0])]
                                    else:
                                        targets = sorted([p for p in rr_dir.glob('*.html') if p.is_file()], key=lambda x: x.name)
                                    if not targets:
                                        try:
                                            messagebox.showinfo('分析', '没有找到要分析的 HTML 文件')
                                        except:
                                            pass
                                        return
                                    import re
                                    out = []
                                    out.append(f'分析 {len(targets)} 个文件:\n')
                                    for f in targets:
                                        try:
                                            t = f.read_text(encoding='utf-8', errors='ignore')
                                            low = t.lower()
                                            title = ''
                                            ts = low.find('<title>')
                                            te = low.find('</title>')
                                            if ts != -1 and te != -1 and te > ts:
                                                title = t[ts+7:te].strip()
                                            body = re.sub('<[^<]+?>', ' ', t)
                                            body = ' '.join(body.split())
                                            has_warn = any(k in body for k in ('警告', 'warning', 'access denied', '403', '404', 'captcha'))
                                            excerpt = body[:800]
                                            out.append(f'--- {f.name} ---')
                                            out.append(f'Title: {title}')
                                            out.append(f'Contains warning-like text: {has_warn}')
                                            out.append(f'Excerpt: {excerpt}\n')
                                        except Exception as e:
                                            out.append(f'--- {f.name} --- parse error: {e}\n')
                                    try:
                                        info_txt.delete('1.0', 'end')
                                        info_txt.insert('1.0', '\n'.join(out))
                                    except Exception:
                                        pass

                                def export_selected_zip():
                                    try:
                                        seli = lb.curselection()
                                        tozip = []
                                        if seli:
                                            tozip = [rr_dir / lb.get(i) for i in seli]
                                        else:
                                            tozip = sorted([p for p in rr_dir.glob('*') if p.is_file()], key=lambda x: x.name)
                                        if not tozip:
                                            try:
                                                messagebox.showinfo('导出', '没有文件可供打包')
                                            except:
                                                pass
                                            return
                                        dst = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('Zip files','*.zip')], title='保存为')
                                        if not dst:
                                            return
                                        import zipfile
                                        try:
                                            with zipfile.ZipFile(dst, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                                                for f in tozip:
                                                    zf.write(f, arcname=f.name)
                                            try:
                                                messagebox.showinfo('导出', f'已保存: {dst}')
                                            except:
                                                pass
                                        except Exception as e:
                                            try:
                                                messagebox.showwarning('导出失败', f'打包失败: {e}')
                                            except:
                                                pass
                                    except Exception:
                                        pass

                                # action 按钮
                                btn_preview = tk.Button(af, text='预览原始文件', command=preview_selected_raw)
                                btn_preview.pack(side='left', padx=6)
                                btn_analyze = tk.Button(af, text='生成/查看分析', command=show_analysis)
                                btn_analyze.pack(side='left', padx=6)
                                btn_export = tk.Button(af, text='导出打包', command=export_selected_zip)
                                btn_export.pack(side='left', padx=6)
                                btn_refresh = tk.Button(af, text='刷新列表', command=refresh_listbox)
                                btn_refresh.pack(side='right', padx=6)
                            except Exception:
                                pass

                        raw_btn = tk.Button(sel_frame, text='查看原始响应', command=open_raw_responses_dialog)
                        raw_btn.pack(side='left', padx=4)
                    except:
                        pass
                    dlg._hf_selected = sel
                except:
                    pass

            try:
                if not ctk:
                    results_box.bind('<<ListboxSelect>>', on_result_select)
            except:
                pass

            def do_download():
                try:
                    sel = getattr(dlg, '_hf_selected', None)
                    if not sel:
                        return
                    sel_files = []
                    try:
                        for idx in files_box.curselection():
                            sel_files.append(files_box.get(idx))
                    except:
                        # if empty, try first file
                        try:
                            if files_box.size() > 0:
                                sel_files.append(files_box.get(0))
                        except:
                            pass
                    mirror_choice_raw = self.mirror_var.get() if hasattr(self, 'mirror_var') else 'auto'
                    mirror_choice = _resolve_mirror_choice(mirror_choice_raw)
                    for fn in sel_files:
                        # run download in background
                        def worker(repo_id=sel, filename=fn, mc=mirror_choice):
                            try:
                                models_dir = Path('models')
                                from threading import Event
                                stop = Event()
                                def cb(msg, pct):
                                    try:
                                        if ctk:
                                            self.status_label.configure(text=f"HF:{msg} {pct}%")
                                        else:
                                            self.status_label.config(text=f"HF:{msg} {pct}%")
                                    except:
                                        pass
                                hf_browser.download_from_hf(repo_id, filename, models_dir, mirror_choice=mc, callback=cb, stop_event=stop)
                                try:
                                    if ctk:
                                        self.status_label.configure(text=f"下载完成: {filename}")
                                    else:
                                        self.status_label.config(text=f"下载完成: {filename}")
                                except:
                                    pass
                            except:
                                pass
                        threading.Thread(target=worker, daemon=True).start()
                except:
                    pass

            # download button
            try:
                if ctk:
                    dbtn = ctk.CTkButton(dlg, text='下载选中文件', command=do_download)
                    dbtn.pack(padx=8, pady=8)
                else:
                    dbtn = tk.Button(dlg, text='下载选中文件', command=do_download)
                    dbtn.pack(padx=8, pady=8)
            except:
                pass
        except Exception:
            pass
        def start_prepare(env_name, progress_lbl, progress_bar=None, state=None):
            if not env_name:
                try:
                    progress_lbl.configure(text="未选择环境")
                except:
                    progress_lbl.config(text="未选择环境")
                return
 
            # prepare log path
            logs_dir = Path("logs") / "environments"
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
            except:
                pass
            log_path = logs_dir / f"{env_name}.log"
            # reset log
            try:
                with log_path.open("w", encoding="utf-8") as lf:
                    lf.write(f"=== Prepare log for {env_name} ===\n")
            except:
                pass
            # create a stop event (best-effort cancellation)
            stop_event = threading.Event()
            if state is not None:
                state["stop_event"] = stop_event
                state["running"] = True
                state["current_env"] = env_name
                state["log_path"] = str(log_path)
 
            def callback(message, progress):
                try:
                    # write to log
                    try:
                        with log_path.open("a", encoding="utf-8") as lf:
                            lf.write(f"{message} | progress={progress}\n")
                    except:
                        pass
                    # 显示在对话框与主状态栏
                    progress_text = f"{message} ({progress}%)" if isinstance(progress, int) else str(message)
                    try:
                        progress_lbl.configure(text=progress_text)
                    except:
                        progress_lbl.config(text=progress_text)
                    # update progress bar if available and progress is numeric
                    try:
                        if progress_bar is not None and isinstance(progress, (int, float)) and progress >= 0:
                            try:
                                progress_bar.set(min(1.0, float(progress) / 100.0))
                            except:
                                try:
                                    progress_bar["value"] = float(progress)
                                except:
                                    pass
                    except:
                        pass
                    try:
                        if ctk:
                            self.status_label.configure(text=progress_text)
                        else:
                            self.status_label.config(text=progress_text)
                    except:
                        pass
                except:
                    pass
 
            def worker():
                try:
                    # best-effort: if env_manager supports an explicit cancel mechanism, pass stop_event
                    try:
                        # detect signature - try calling with cancel_event if supported
                        import inspect
                        sig = inspect.signature(self.env_manager.prepare_environment)
                        if "cancel_event" in sig.parameters:
                            success = self.env_manager.prepare_environment(env_name, callback=callback, cancel_event=stop_event)
                        else:
                            success = self.env_manager.prepare_environment(env_name, callback=callback)
                    except Exception:
                        # fallback call
                        success = self.env_manager.prepare_environment(env_name, callback=callback)
                    final = "环境准备完成" if success else "环境准备失败"
                    callback(final, 100 if success else -1)
                except Exception as e:
                    callback(f"异常: {e}", -1)
                finally:
                    if state is not None:
                        state["running"] = False
                        state["stop_event"] = None
                        state["current_env"] = None
 
            threading.Thread(target=worker, daemon=True).start()
 
        def request_cancel(state):
            """请求取消当前准备（仅发送请求，后端需支持真正取消）"""
            try:
                if not state or not state.get("running"):
                    try:
                        if ctk:
                            messagebox.showinfo("取消", "当前没有正在进行的准备任务")
                        else:
                            messagebox.showinfo("取消", "当前没有正在进行的准备任务")
                    except:
                        pass
                    return
                # try to call backend cancel if provided
                try:
                    if hasattr(self.env_manager, "cancel_prepare"):
                        self.env_manager.cancel_prepare(state.get("current_env"))
                    else:
                        ev = state.get("stop_event")
                        if ev:
                            ev.set()
                    # update UI
                    try:
                        if ctk:
                            self.status_label.configure(text="已请求取消准备（仅请求）")
                        else:
                            self.status_label.config(text="已请求取消准备（仅请求）")
                    except:
                        pass
                except Exception as e:
                    try:
                        if ctk:
                            messagebox.showwarning("取消失败", f"取消请求失败: {e}")
                        else:
                            messagebox.showwarning("取消失败", f"取消请求失败: {e}")
                    except:
                        pass
            except:
                pass
 
        def export_log(state):
            """导出当前环境的日志到用户选择位置"""
            try:
                path = state.get("log_path") if state else None
                if not path or not Path(path).exists():
                    try:
                        if ctk:
                            messagebox.showinfo("导出日志", "未找到日志文件")
                        else:
                            messagebox.showinfo("导出日志", "未找到日志文件")
                    except:
                        pass
                    return
                dst = filedialog.asksaveasfilename(parent=self.root, title="导出日志为", defaultextension=".log",
                                                   filetypes=[("Log files","*.log"),("All files","*.*")])
                if not dst:
                    return
                try:
                    with open(path, "rb") as srcf, open(dst, "wb") as dstf:
                        dstf.write(srcf.read())
                    try:
                        if ctk:
                            messagebox.showinfo("导出日志", f"已导出到 {dst}")
                        else:
                            messagebox.showinfo("导出日志", f"已导出到 {dst}")
                    except:
                        pass
                except Exception as e:
                    try:
                        if ctk:
                            messagebox.showwarning("导出失败", f"导出失败: {e}")
                        else:
                            messagebox.showwarning("导出失败", f"导出失败: {e}")
                    except:
                        pass
            except:
                pass

        def open_dialog():
            dlg = ctk.CTkToplevel(self.root) if ctk else tk.Toplevel(self.root)
            dlg.title("准备环境")
            dlg.geometry("520x260")
            state = {"stop_event": None, "running": False, "current_env": None, "log_path": None}
            try:
                envs = [e['name'] for e in self.env_manager.list_available_environments()]
            except Exception:
                envs = []

            if ctk:
                lbl = ctk.CTkLabel(dlg, text="请选择环境并开始准备：")
                lbl.pack(padx=8, pady=8, anchor="w")
                env_var = ctk.StringVar(value=envs[0] if envs else "")
                env_menu = ctk.CTkOptionMenu(dlg, values=envs, variable=env_var)
                env_menu.pack(padx=8, pady=4, fill="x")
                progress_lbl = ctk.CTkLabel(dlg, text="就绪")
                progress_lbl.pack(padx=8, pady=4, anchor="w")
                try:
                    progress_bar = ctk.CTkProgressBar(dlg, width=480)
                    progress_bar.set(0)
                    progress_bar.pack(padx=8, pady=4)
                except Exception:
                    progress_bar = None
                btn_frame = ctk.CTkFrame(dlg)
                btn_frame.pack(fill="x", padx=8, pady=6)
                start_btn = ctk.CTkButton(btn_frame, text="开始准备", command=lambda: start_prepare(env_var.get(), progress_lbl, progress_bar, state))
                start_btn.pack(side="left", padx=6)
                cancel_btn = ctk.CTkButton(btn_frame, text="取消(仅请求)", command=lambda: request_cancel(state))
                cancel_btn.pack(side="left", padx=6)
                export_btn = ctk.CTkButton(btn_frame, text="导出日志", command=lambda: export_log(state))
                export_btn.pack(side="right", padx=6)
            else:
                lbl = tk.Label(dlg, text="请选择环境并开始准备：")
                lbl.pack(padx=8, pady=8, anchor="w")
                env_var = tk.StringVar(value=envs[0] if envs else "")
                env_menu = tk.OptionMenu(dlg, env_var, *(envs or [""]))
                env_menu.pack(padx=8, pady=4, fill="x")
                progress_lbl = tk.Label(dlg, text="就绪")
                progress_lbl.pack(padx=8, pady=4, anchor="w")
                try:
                    from tkinter import ttk
                    progress_bar = ttk.Progressbar(dlg, orient="horizontal", length=480, mode="determinate")
                    progress_bar["value"] = 0
                    progress_bar.pack(padx=8, pady=4)
                except Exception:
                    progress_bar = None
                btn_frame = tk.Frame(dlg)
                btn_frame.pack(fill="x", padx=8, pady=6)
                start_btn = tk.Button(btn_frame, text="开始准备", command=lambda: start_prepare(env_var.get(), progress_lbl, progress_bar, state))
                start_btn.pack(side="left", padx=6)
                cancel_btn = tk.Button(btn_frame, text="取消(仅请求)", command=lambda: request_cancel(state))
                cancel_btn.pack(side="left", padx=6)
                export_btn = tk.Button(btn_frame, text="导出日志", command=lambda: export_log(state))
                export_btn.pack(side="right", padx=6)

        # 在主线程打开对话框
        try:
            self.root.after(0, open_dialog)
        except Exception:
            open_dialog()

    def _on_model_change(self):
        """在模型选择改变时委派到 handlers 中的实现（若可用），否则执行简化回退逻辑并填充右侧详情区域。"""
        sel = self.model_var.get() if hasattr(self, "model_var") else None

        # 先尝试调用外部 handler（若存在）
        try:
            from app.handlers.model_handlers import on_model_change_ctk
        except Exception:
            on_model_change_ctk = None

        if on_model_change_ctk:
            try:
                on_model_change_ctk(self, sel, use_ctk=(ctk is not None))
                return
            except Exception:
                # 回退到内联实现
                pass

        # 回退实现：更新标签与右侧详情
        try:
            if not sel or sel == "自动选择":
                if hasattr(self, "model_label"):
                    if ctk:
                        self.model_label.configure(text="模型: 自动选择")
                    else:
                        self.model_label.config(text="模型: 自动选择")
                # 清除详情
                if hasattr(self, 'md_name'):
                    try:
                        if ctk:
                            self.md_name.configure(text="名称: -")
                            self.md_category.configure(text="分类: -")
                            self.md_task.configure(text="任务: -")
                            self.md_version.configure(text="版本: -")
                            self.md_size.configure(text="大小: -")
                            self.md_status.configure(text="状态: -")
                        else:
                            self.md_name.config(text="名称: -")
                            self.md_category.config(text="分类: -")
                            self.md_task.config(text="任务: -")
                            self.md_version.config(text="版本: -")
                            self.md_size.config(text="大小: -")
                            self.md_status.config(text="状态: -")
                    except Exception:
                        pass
                return

            model_id = sel.split('(')[-1].strip(')')
            if hasattr(self, "model_label"):
                lbl_text = f"模型: {model_id}"
                if ctk:
                    self.model_label.configure(text=lbl_text)
                else:
                    self.model_label.config(text=lbl_text)

            # 尝试从后端获取模型详情
            info = None
            try:
                if 'get_model_entry' in globals() and callable(get_model_entry):
                    info = get_model_entry(model_id)
            except Exception:
                info = None

            if info:
                name = info.get('display_name') or info.get('id') or model_id
                category = info.get('category') or info.get('type') or '-'
                task = info.get('task') or info.get('description') or '-'
                # 版本优先字段
                version = '-'
                try:
                    if info.get('version'):
                        version = info.get('version')
                    elif info.get('versions') and isinstance(info.get('versions'), list) and info.get('versions')[-1].get('name'):
                        version = info.get('versions')[-1].get('name')
                except Exception:
                    pass
                size = info.get('size') or info.get('file_size') or '-'
                status = info.get('status') or '-'
            else:
                name = model_id
                category = '-'
                task = '-'
                version = '-'
                size = '-'
                status = '-'

            # 填充到 UI
            try:
                if ctk:
                    self.md_name.configure(text=f"名称: {name}")
                    self.md_category.configure(text=f"分类: {category}")
                    self.md_task.configure(text=f"任务: {task}")
                    self.md_version.configure(text=f"版本: {version}")
                    self.md_size.configure(text=f"大小: {size}")
                    self.md_status.configure(text=f"状态: {status}")
                else:
                    self.md_name.config(text=f"名称: {name}")
                    self.md_category.config(text=f"分类: {category}")
                    self.md_task.config(text=f"任务: {task}")
                    self.md_version.config(text=f"版本: {version}")
                    self.md_size.config(text=f"大小: {size}")
                    self.md_status.config(text=f"状态: {status}")
            except Exception:
                pass

        except Exception:
            # 不让 UI 因数据错误崩溃
            pass

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
 
    def refresh_model_list(self):
        """
        使用 app.ui_components.refresh_model_controls 统一刷新模型/镜像/量化/设备控件。
        保持向后兼容：若 ui_components 不可用则回退到原始实现。
        """
        try:
            from app.ui_components import refresh_model_controls
        except Exception:
            refresh_model_controls = None

        try:
            controls = {
                "model_var": getattr(self, "model_var", None),
                "model_menu": getattr(self, "model_menu", None),
                "mirror_var": getattr(self, "mirror_var", None),
                "mirror_menu": getattr(self, "mirror_menu", None),
                "quant_var": getattr(self, "quant_var", None),
                "quant_menu": getattr(self, "quant_menu", None),
                "device_var": getattr(self, "device_var", None),
                "device_menu": getattr(self, "device_menu", None),
            }
            if refresh_model_controls:
                try:
                    refresh_model_controls(controls, list_models, hardware_detector=hardware_detector if 'hardware_detector' in globals() else None)
                    return
                except Exception:
                    # fallback to inline behavior below
                    pass

            # Fallback: inline simple refresh (keeps previous behavior)
            models = list_models() or []
            items = [ "自动选择" ] + [ f"{m.get('display_name') or m.get('id')} ({m.get('id')})" for m in models ]
            # 尝试保持当前选择
            try:
                current = self.model_var.get()
            except:
                current = None
            if ctk:
                self.model_menu.configure(values=items)
                if current in items:
                    self.model_var.set(current)
                else:
                    self.model_var.set(items[0])
            else:
                menu = self.model_menu["menu"]
                menu.delete(0, "end")
                for it in items:
                    menu.add_command(label=it, command=lambda v=it: self.model_var.set(v))
                if current in items:
                    self.model_var.set(current)
                else:
                    self.model_var.set(items[0])
            # 尝试动态填充设备选项（基于 hardware_detector）
            try:
                devs = ['CPU', 'Auto']
                if 'hardware_detector' in globals() and hardware_detector:
                    summary = {}
                    try:
                        summary = hardware_detector.get_device_summary() or {}
                    except:
                        summary = {}
                    gpus = summary.get('gpu', []) if isinstance(summary.get('gpu', []), list) else []
                    seen = set()
                    for g in gpus:
                        brand = (g.get('brand') if isinstance(g, dict) else str(g)) or ""
                        b_lower = brand.lower()
                        if 'nvidia' in b_lower or 'nv' in b_lower:
                            label = 'GPU - Nvidia'
                        elif 'amd' in b_lower or 'radeon' in b_lower:
                            label = 'GPU - AMD'
                        elif 'intel' in b_lower:
                            label = 'GPU - Intel'
                        else:
                            # take a short brand token if available
                            try:
                                label = f"GPU - {brand.split()[0]}" if brand else None
                            except:
                                label = None
                        if label and label not in seen:
                            devs.insert(0, label)
                            seen.add(label)
                # Apply device options
                if ctk:
                    try:
                        self.device_menu.configure(values=devs)
                        try:
                            # keep current if available
                            curd = self.device_var.get()
                            if curd not in devs:
                                self.device_var.set(devs[0])
                        except:
                            pass
                    except:
                        pass
                        # After refreshing controls, update details for current selection
                        try:
                            self._on_model_change()
                        except:
                            pass
                else:
                    try:
                        menu = self.device_menu["menu"]
                        menu.delete(0, "end")
                        for it in devs:
                            menu.add_command(label=it, command=lambda v=it: self.device_var.set(v))
                        try:
                            if self.device_var.get() not in devs:
                                self.device_var.set(devs[0])
                        except:
                            pass
                    except:
                        pass
            except:
                pass
        except Exception:
            # fallback static
            items = ["自动选择","yolov5s","yolov8n"]
            try:
                if ctk:
                    try:
                        self.model_menu.configure(values=items)
                        if current in items:
                            self._safe_set_var(self.model_var, current)
                        else:
                            self._safe_set_var(self.model_var, items[0])
                    except:
                        pass
                else:
                    try:
                        menu = self.model_menu["menu"]
                        menu.delete(0, "end")
                        for it in items:
                            menu.add_command(label=it, command=lambda v=it: self.model_var.set(v))
                        if current in items:
                            self._safe_set_var(self.model_var, current)
                        else:
                            self._safe_set_var(self.model_var, items[0])
                    except:
                        pass
            except:
                pass

    def open_model_manager(self):
        ModelManagerDialog(self.root)
        # After dialog, refresh model and local lists
        self.refresh_model_list()


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

    if ctk:
        app.root.mainloop()
    else:
        app.root.mainloop()


if __name__ == "__main__":
    if ctk is None:
        print("未检测到 customtkinter，请先安装：pip install customtkinter")
    else:
        run_app()