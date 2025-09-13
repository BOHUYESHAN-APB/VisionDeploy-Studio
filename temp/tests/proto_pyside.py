#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal PySide6 prototype for model management UI
"""

try:
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QFileDialog
except Exception as e:
    print("PySide6 not installed:", e)
    raise

import sys
import json
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

class ProtoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proto PySide6 - Model Manager")
        self.resize(600, 200)
        layout = QVBoxLayout()
        self.setLayout(layout)

        h = QHBoxLayout()
        h.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(load_model_ids())
        h.addWidget(self.model_combo)

        h.addWidget(QLabel("镜像:"))
        self.mirror_combo = QComboBox()
        self.mirror_combo.addItems(["auto", "cn", "global", "official", "huggingface"])
        h.addWidget(self.mirror_combo)

        layout.addLayout(h)

        btn_layout = QHBoxLayout()
        self.download_btn = QPushButton("下载所选模型")
        self.download_btn.clicked.connect(self.on_download)
        btn_layout.addWidget(self.download_btn)

        self.import_btn = QPushButton("导入本地模型")
        self.import_btn.clicked.connect(self.on_import)
        btn_layout.addWidget(self.import_btn)

        layout.addLayout(btn_layout)

        self.status = QLabel("状态: 就绪")
        layout.addWidget(self.status)

    def on_download(self):
        model_id = self.model_combo.currentText()
        mirror = self.mirror_combo.currentText()
        self.status.setText(f"开始下载 {model_id} via {mirror} (模拟)")
        print(f"DOWNLOAD: model={model_id} mirror={mirror}")

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模型文件", str(Path.home()))
        if path:
            self.status.setText(f"已导入: {Path(path).name}")
            print("IMPORT:", path)

def main():
    app = QApplication(sys.argv)
    w = ProtoWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()