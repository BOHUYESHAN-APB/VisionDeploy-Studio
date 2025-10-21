#!/usr/bin/env python3
# Lightweight CTk-compatible UI skeleton for VisionDeploy Studio
# Provides a safe run_app(context) entry and a MainApp class with setup/run

from pathlib import Path
import sys

try:
    import customtkinter as ctk
    from customtkinter import CTk, CTkFrame, CTkLabel, CTkButton
    HAS_CTK = True
except Exception:
    import tkinter as tk
    from tkinter import Frame as CTkFrame, Label as CTkLabel, Button as CTkButton
    HAS_CTK = False

class MainApp:
    def __init__(self, context=None):
        self.context = context or {}
        self.root = None
        self.status_label = None
        # parse context into instance attributes
        self.project_root = self.context.get('project_root') if isinstance(self.context, dict) else None
        self.resources_dir = self.context.get('resources_dir') if isinstance(self.context, dict) else None
        self.mirror = self.context.get('mirror') if isinstance(self.context, dict) else None

    def setup(self):
        # Create main window
        if HAS_CTK:
            self.root = CTk()
            self.root.geometry('1100x720')
            self.root.title('VisionDeploy Studio')
        else:
            self.root = tk.Tk()
            self.root.geometry('1100x720')
            self.root.title('VisionDeploy Studio (Tk)')

        # layout: left nav, main area, right community panel, bottom status
        self.left_nav = CTkFrame(self.root, width=220)
        self.left_nav.pack(side='left', fill='y')

        self.main_area = CTkFrame(self.root)
        self.main_area.pack(side='left', fill='both', expand=True)

        self.right_panel = CTkFrame(self.root, width=320)
        self.right_panel.pack(side='right', fill='y')

        # status bar
        self.status_bar = CTkFrame(self.root, height=28)
        self.status_bar.pack(side='bottom', fill='x')
        self.status_label = CTkLabel(self.status_bar, text='Ready')
        self.status_label.pack(side='left', padx=8)
        # show context info in status if available
        info = []
        try:
            if self.resources_dir:
                info.append(f"res:{Path(self.resources_dir).name}")
            if self.mirror:
                info.append(f"mirror:{self.mirror}")
            if info:
                self.status_label.configure(text=' | '.join(info))
        except Exception:
            # defensive: ignore any path/mode errors when building status
            pass

        # Populate nav
        nav_items = ['模型库', '本地模型', '推理工作室', '社区', '设置']
        for it in nav_items:
            b = CTkButton(self.left_nav, text=it, width=200)
            b.pack(pady=6, padx=8)

        # Top search placeholder
        self.search_label = CTkLabel(self.main_area, text='Search / Filter Placeholder')
        self.search_label.pack(pady=8)

        # model list placeholder (as simple labels)
        for i in range(8):
            lbl = CTkLabel(self.main_area, text=f'Model Card Placeholder {i+1}', anchor='w')
            lbl.pack(fill='x', padx=10, pady=4)

        # community placeholder
        comm = CTkLabel(self.right_panel, text='Community Feed Placeholder')
        comm.pack(padx=8, pady=8)

    def run(self):
        if not self.root:
            self.setup()
        # enter mainloop
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass

def run_app(context=None):
    app = MainApp(context=context)
    app.setup()
    app.run()

def get_context_info(context=None):
    """Helper for non-GUI verification: return parsed context info dict."""
    app = MainApp(context=context)
    return {
        'project_root': app.project_root,
        'resources_dir': app.resources_dir,
        'mirror': app.mirror,
    }

# For interactive import tests
if __name__ == '__main__':
    run_app()
