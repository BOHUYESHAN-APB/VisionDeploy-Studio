#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySide6 GUI migration for VisionDeploy Studio (minimal replacement for DearPyGui)
Provides model selection and model manager dialogs using PySide6.
"""

from pathlib import Path
import sys
import threading
from typing import Optional

from PySide6 import QtWidgets, QtCore

project_root = Path(__file__).parent.parent

try:
    from app.model_manager import list_models, get_model_entry, download_model, find_local_models, import_local_model
except Exception:
    def list_models(): return []
    def get_model_entry(*a, **k): return None
    def download_model(*a, **k): return None
    def find_local_models(*a, **k): return []
    def import_local_model(*a, **k): return None

class ModelManagerDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型管理")
        self.resize(700, 400)
        layout = QtWidgets.QVBoxLayout(self)

        self.model_combo = QtWidgets.QComboBox()
        self.refresh_models()
        layout.addWidget(QtWidgets.QLabel("可用模型："))
        layout.addWidget(self.model_combo)

        btn_layout = QtWidgets.QHBoxLayout()
        self.download_btn = QtWidgets.QPushButton("下载所选模型")
        self.import_btn = QtWidgets.QPushButton("导入本地模型")
        self.close_btn = QtWidgets.QPushButton("关闭")
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        layout.addWidget(QtWidgets.QLabel("本地模型："))
        self.local_list = QtWidgets.QListWidget()
        layout.addWidget(self.local_list)

        self.status = QtWidgets.QLabel("")
        layout.addWidget(self.status)

        self.download_btn.clicked.connect(self.on_download)
        self.import_btn.clicked.connect(self.on_import_local)
        self.close_btn.clicked.connect(self.close)

        self.refresh_local()

    def refresh_models(self):
        self.model_combo.clear()
        try:
            for m in list_models():
                display = f"{m.get('display_name') or m.get('id')} ({m.get('id')})"
                self.model_combo.addItem(display)
        except Exception:
            self.model_combo.addItem("无可用模型")

    def refresh_local(self):
        self.local_list.clear()
        try:
            for p in find_local_models():
                self.local_list.addItem(str(p.name))
        except Exception:
            self.local_list.addItem("无法读取本地模型")

    def on_download(self):
        sel = self.model_combo.currentText()
        if not sel or sel == "无可用模型":
            self.status.setText("未选择模型")
            return
        model_id = sel.split('(')[-1].strip(')')
        self.status.setText(f"开始下载 {model_id} ...")
        def worker():
            try:
                p = download_model(model_id, mirror='auto')
                if p:
                    self.status.setText(f"下载完成: {Path(p).name}")
                else:
                    self.status.setText("下载失败")
            except Exception as e:
                self.status.setText(f"下载异常: {e}")
            self.refresh_local()
        threading.Thread(target=worker, daemon=True).start()

    def on_import_local(self):
        dlg = QtWidgets.QFileDialog(self)
        dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        if dlg.exec():
            files = dlg.selectedFiles()
            if files:
                src = files[0]
                self.status.setText(f"导入 {src} ...")
                def worker():
                    try:
                        p = import_local_model(src)
                        if p:
                            self.status.setText(f"已导入: {Path(p).name}")
                        else:
                            self.status.setText("导入失败")
                    except Exception as e:
                        self.status.setText(f"导入异常: {e}")
                    self.refresh_local()
                threading.Thread(target=worker, daemon=True).start()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisionDeploy Studio - PySide6")
        self.resize(1000, 700)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        layout.addWidget(left, 0)

        # Status
        self.status_label = QtWidgets.QLabel("就绪")
        left_layout.addWidget(self.status_label)

        left_layout.addWidget(QtWidgets.QLabel("模型设置"))
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.addItem("自动选择")
        self.refresh_model_list()
        self.model_combo.currentIndexChanged.connect(self.on_model_change)
        left_layout.addWidget(self.model_combo)

        self.mirror_combo = QtWidgets.QComboBox()
        for it in ['auto', 'cn', 'global', 'official', 'huggingface']:
            self.mirror_combo.addItem(it)
        self.mirror_combo.currentIndexChanged.connect(self.on_mirror_change)
        left_layout.addWidget(QtWidgets.QLabel("镜像"))
        left_layout.addWidget(self.mirror_combo)

        self.quantized_combo = QtWidgets.QComboBox()
        self.quantized_combo.addItem("无量化模型")
        left_layout.addWidget(QtWidgets.QLabel("量化模型"))
        left_layout.addWidget(self.quantized_combo)

        self.device_combo = QtWidgets.QComboBox()
        self.device_combo.addItems(["CPU", "Auto", "GPU - Intel"])
        left_layout.addWidget(QtWidgets.QLabel("选择设备"))
        left_layout.addWidget(self.device_combo)

        btn = QtWidgets.QPushButton("模型管理")
        btn.clicked.connect(self.open_model_manager)
        left_layout.addWidget(btn)

        left_layout.addStretch()

        # Right display stub
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        layout.addWidget(right, 1)

        right_layout.addWidget(QtWidgets.QLabel("实时显示"))
        self.details = QtWidgets.QLabel("选择文件开始推理...")
        self.details.setWordWrap(True)
        right_layout.addWidget(self.details)

    def refresh_model_list(self):
        self.model_combo.blockSignals(True)
        try:
            self.model_combo.clear()
            self.model_combo.addItem("自动选择")
            for m in list_models():
                display = f"{m.get('display_name') or m.get('id')} ({m.get('id')})"
                self.model_combo.addItem(display)
        except Exception:
            # fallback static
            self.model_combo.clear()
            for it in ['自动选择', 'yolov5s', 'yolov8n']:
                self.model_combo.addItem(it)
        finally:
            self.model_combo.blockSignals(False)

    def on_model_change(self, index):
        sel = self.model_combo.currentText()
        if sel == "自动选择":
            self.status_label.setText("自动选择模型")
            return
        model_id = sel.split('(')[-1].strip(')')
        self.status_label.setText(f"已选择: {model_id}")
        # refresh quantized options
        QtCore.QTimer.singleShot(10, lambda: self.refresh_quantized(model_id))
        # check local
        try:
            entry = get_model_entry(model_id)
        except:
            entry = None
        expected = set()
        if entry:
            for v in entry.get('versions', []):
                fn = v.get('filename')
                if fn:
                    expected.add(fn)
                for q in v.get('quantized', []) or []:
                    qfn = q.get('filename') or q.get('name')
                    if qfn:
                        expected.add(qfn)
        local = find_local_models()
        found = False
        for p in local:
            for ef in expected:
                if ef and ef in p.name:
                    found = True
                    break
            if found:
                break
        if not found and not expected and not local:
            found = False
        if not found:
            # open manager
            self.open_model_manager()

    def refresh_quantized(self, model_id):
        self.quantized_combo.clear()
        try:
            entry = get_model_entry(model_id) or {}
            versions = entry.get('versions', []) or []
            if not versions:
                self.quantized_combo.addItem("无量化模型")
                return
            ver = versions[-1]
            quant = ver.get('quantized', []) or []
            if not quant:
                self.quantized_combo.addItem("无量化模型")
            else:
                for q in quant:
                    name = q.get('name') or q.get('filename') or str(q)
                    self.quantized_combo.addItem(name)
        except Exception:
            self.quantized_combo.addItem("无量化模型")

    def on_mirror_change(self, index):
        mirror = self.mirror_combo.currentText()
        self.status_label.setText(f"镜像切换: {mirror}")
        sel = self.model_combo.currentText()
        if sel and sel != "自动选择":
            model_id = sel.split('(')[-1].strip(')')
            QtCore.QTimer.singleShot(10, lambda: self.refresh_quantized(model_id))

    def open_model_manager(self):
        dlg = ModelManagerDialog(self)
        dlg.exec()
        # after close, refresh local list and model combo
        self.refresh_model_list()

def run_app():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()