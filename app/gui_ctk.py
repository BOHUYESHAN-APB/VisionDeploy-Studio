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

# font initializer fallbacks
try:
    from app.font_initializer import initialize_chinese_font, initialize_chinese_font_debug, rebind_default_font
except Exception:
    initialize_chinese_font = None
    initialize_chinese_font_debug = None
    rebind_default_font = None

# ...existing code...

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
except Exception:
    load_model_device_map = None
    save_model_device_map = None
    get_quantized_options_for_model = None


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
    def __init__(self):
        self.root = None

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
            ctk.set_appearance_mode("System")
            ctk.set_default_color_theme("blue")
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        # 初始化按需环境管理器（可选）
        try:
            self.env_manager = OnDemandEnvironmentManager() if OnDemandEnvironmentManager else None
        except Exception:
            self.env_manager = None

        self.root.title("VisionDeploy Studio - CTk")
        self.root.geometry("1100x720")

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
                mb_about = ctk.CTkButton(menubar, text="关于", command=lambda: messagebox.showinfo("关于","VisionDeploy Studio - CTk"), width=120)
                mb_about.pack(side="right", padx=4, pady=4)
            else:
                menubar = tk.Frame(self.root)
                menubar.pack(side="top", fill="x")
                mb_file = tk.Button(menubar, text="重载字体", command=self._on_reload_fonts, width=12)
                mb_file.pack(side="left", padx=4, pady=4)
                mb_theme = tk.Button(menubar, text="切换主题", command=self._on_toggle_theme, width=12)
                mb_theme.pack(side="left", padx=4, pady=4)
                mb_about = tk.Button(menubar, text="关于", command=lambda: messagebox.showinfo("关于","VisionDeploy Studio - CTk"), width=12)
                mb_about.pack(side="right", padx=4, pady=4)
        except Exception:
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
            self.device_var = ctk.StringVar(value="CPU")
            self.device_menu = ctk.CTkOptionMenu(left, values=['CPU','Auto','GPU - Intel'], variable=self.device_var)
            self.device_menu.pack(padx=6, pady=4)
        else:
            self.device_var = tk.StringVar(value="CPU")
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
            else:
                self.zoom_var = tk.StringVar(value='100%')
                self.zoom_menu = tk.OptionMenu(left, self.zoom_var, *zoom_values)
                self.zoom_menu.pack(padx=6, pady=6)
                self.apply_zoom_btn = tk.Button(left, text="应用缩放", command=self._apply_zoom)
                self.apply_zoom_btn.pack(padx=6, pady=4)
        except Exception:
            pass

        # model manager button
        if ctk:
            btn = ctk.CTkButton(left, text="模型管理", command=self.open_model_manager)
            btn.pack(padx=6, pady=8)
            prep_btn = ctk.CTkButton(left, text="准备环境", command=self._on_prepare_env)
            prep_btn.pack(padx=6, pady=4)
            self.reload_font_btn = ctk.CTkButton(left, text="重载字体", command=self._on_reload_fonts)
            self.reload_font_btn.pack(padx=6, pady=4)
        else:
            btn = tk.Button(left, text="模型管理", command=self.open_model_manager)
            btn.pack(padx=6, pady=8)
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
            self.download_model_btn = ctk.CTkButton(act_frame, text="下载模型", command=self._on_download_selected_model)
            self.download_model_btn.pack(side="left", padx=6)
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
            self.download_model_btn = tk.Button(act_frame, text="下载模型", command=self._on_download_selected_model)
            self.download_model_btn.pack(side="left", padx=6)
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
            try:
                if 'download_model' in globals() and callable(download_model):
                    def progress_cb(msg, pct):
                        try:
                            if ctk:
                                self.status_label.configure(text=f"{msg} ({pct}%)")
                            else:
                                self.status_label.config(text=f"{msg} ({pct}%)")
                        except:
                            pass
                    # resolve mirror from left-side selection if available
                    try:
                        mirror_val = 'auto'
                        if hasattr(self, 'mirror_var') and getattr(self, 'mirror_var') is not None:
                            mirror_val = _resolve_mirror_choice(self.mirror_var.get())
                    except:
                        mirror_val = 'auto'
                    download_model(model_id, mirror=mirror_val, callback=progress_cb)
                    try:
                        if ctk:
                            self.status_label.configure(text='下载完成')
                        else:
                            self.status_label.config(text='下载完成')
                    except:
                        pass
                else:
                    try:
                        if ctk:
                            self.status_label.configure(text='下载接口不可用')
                        else:
                            self.status_label.config(text='下载接口不可用')
                    except:
                        pass
            except Exception as e:
                try:
                    if ctk:
                        self.status_label.configure(text=f'下载异常: {e}')
                    else:
                        self.status_label.config(text=f'下载异常: {e}')
                except:
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
            return
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


def run_app():
    app = MainApp()
    app.setup()
    if ctk:
        app.root.mainloop()
    else:
        app.root.mainloop()


if __name__ == "__main__":
    if ctk is None:
        print("未检测到 customtkinter，请先安装：pip install customtkinter")
    else:
        run_app()