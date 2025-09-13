#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal Kivy prototype for model management UI
"""

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.spinner import Spinner
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.popup import Popup
    from kivy.uix.filechooser import FileChooserListView
except Exception as e:
    print("Kivy not installed:", e)
    raise

import json
import sys
from pathlib import Path

def load_model_ids():
    try:
        db_path = Path(__file__).parent.parent / "resources" / "models.json"
        if db_path.exists():
            db = json.loads(db_path.read_text(encoding='utf-8'))
            return [m.get('id') for m in db.get('models', []) if m.get('id')]
    except Exception:
        pass
    return ["yolov5s", "yolov8n"]

class ProtoLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        top = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        top.add_widget(Label(text="模型:", size_hint_x=None, width=80))
        self.model_spinner = Spinner(text=load_model_ids()[0] if load_model_ids() else "none",
                                    values=load_model_ids())
        top.add_widget(self.model_spinner)
        top.add_widget(Label(text="镜像:", size_hint_x=None, width=80))
        self.mirror_spinner = Spinner(text='auto', values=['auto','cn','global','official','huggingface'])
        top.add_widget(self.mirror_spinner)
        self.add_widget(top)

        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        dl = Button(text="下载所选模型")
        dl.bind(on_release=self.on_download)
        btn_row.add_widget(dl)
        imp = Button(text="导入本地模型")
        imp.bind(on_release=self.on_import)
        btn_row.add_widget(imp)
        self.add_widget(btn_row)

        self.status = Label(text="状态: 就绪")
        self.add_widget(self.status)

    def on_download(self, instance):
        model_id = self.model_spinner.text
        mirror = self.mirror_spinner.text
        self.status.text = f"开始下载 {model_id} via {mirror} (模拟)"
        print("DOWNLOAD:", model_id, mirror)

    def on_import(self, instance):
        chooser = FileChooserListView(path=str(Path.home()))
        popup = Popup(title="选择模型文件", content=chooser, size_hint=(0.9,0.9))
        def _select(*args):
            selection = chooser.selection
            if selection:
                path = selection[0]
                self.status.text = f"已导入: {Path(path).name}"
                print("IMPORT:", path)
                popup.dismiss()
        chooser.bind(on_submit=lambda *a: _select())
        popup.open()

class ProtoKivyApp(App):
    def build(self):
        return ProtoLayout()

if __name__ == "__main__":
    ProtoKivyApp().run()