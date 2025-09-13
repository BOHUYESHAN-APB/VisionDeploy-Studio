"""Inference handlers shim (DearPyGui archived)

The original implementation depended on DearPyGui for UI dialogs and
widgets. This shim preserves the public API used by the application but
avoids importing dearpygui at module import time. UI interactions are
delegated to the application's UI layer when available, or logged via
the app.logger.
"""

import os
try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

from typing import Dict, List, Any, Optional


def archived_info() -> Dict[str, str]:
    from pathlib import Path
    archived = (Path(__file__).parent / '..' / 'legacy_dearpygui' / 'inference_handlers.py').resolve()
    return {'archived_path': str(archived), 'note': 'DearPyGui inference handlers archived.'}


class InferenceHandlers:
    def __init__(self, app):
        self.app = app
        self.logger = getattr(app, 'logger', None)

    def _notify(self, title: str, message: str):
        # Try to show a tkinter messagebox if UI exists, otherwise log
        try:
            from tkinter import messagebox
            try:
                messagebox.showinfo(title, message)
                return
            except Exception:
                pass
        except Exception:
            pass
        try:
            if self.logger:
                self.logger.info(f"{title}: {message}")
        except Exception:
            pass

    def select_input_source(self, sender, value):
        # Simplified: set input source on inference_engine based on value
        try:
            if value == "摄像头":
                cam_id = None
                try:
                    cam_id = getattr(self.app, 'camera_id', None)
                except Exception:
                    cam_id = None
                try:
                    self.app.inference_engine.set_input_source("camera", cam_id)
                except Exception:
                    pass
            else:
                source_type = "image" if value == "图片文件" else "video"
                try:
                    self.app.inference_engine.set_input_source(source_type, None)
                except Exception:
                    pass
        except Exception:
            pass

    def set_camera_id(self, sender, value):
        try:
            self.app.inference_engine.set_input_source("camera", value)
        except Exception:
            pass

    def select_input_file(self):
        # Best-effort: set example file or rely on app UI to call set_input_source
        try:
            file_path = getattr(self.app, 'last_selected_file', None) or 'example.jpg'
            try:
                self.app.inference_engine.set_input_source('image', file_path)
            except Exception:
                pass
            try:
                if hasattr(self.app, 'ui') and getattr(self.app, 'ui', None):
                    # let UI layer update its displayed selected file if it has method
                    upd = getattr(self.app.ui, 'on_selected_file', None)
                    if callable(upd):
                        upd(file_path)
            except Exception:
                pass
        except Exception:
            pass

    def set_confidence_threshold(self, sender, value):
        try:
            self.app.inference_engine.set_inference_params(confidence_threshold=value)
        except Exception:
            pass

    def set_iou_threshold(self, sender, value):
        try:
            self.app.inference_engine.set_inference_params(iou_threshold=value)
        except Exception:
            pass

    def start_inference(self):
        try:
            if not getattr(self.app.inference_engine, 'current_model', None):
                self._notify('错误', '请先选择一个模型')
                return
        except Exception:
            pass

        try:
            # Output options: rely on app state or defaults
            save_results = getattr(self.app, 'save_results', False)
            output_path = None
            if save_results:
                output_path = os.path.join(getattr(self.app, 'base_dir', '.'), 'output')
                try:
                    os.makedirs(output_path, exist_ok=True)
                except Exception:
                    pass
            try:
                self.app.inference_engine.set_output_options(save_results, output_path)
            except Exception:
                pass

            try:
                success = self.app.inference_engine.start_inference(self._inference_result_callback)
            except Exception:
                success = False

            try:
                if success and hasattr(self.app, 'ui') and getattr(self.app, 'ui', None):
                    upd = getattr(self.app.ui, 'on_inference_started', None)
                    if callable(upd):
                        upd()
            except Exception:
                pass

        except Exception:
            pass

    def stop_inference(self):
        try:
            success = self.app.inference_engine.stop_inference()
            try:
                if success and hasattr(self.app, 'ui') and getattr(self.app, 'ui', None):
                    upd = getattr(self.app.ui, 'on_inference_stopped', None)
                    if callable(upd):
                        upd()
            except Exception:
                pass
        except Exception:
            pass

    def _inference_result_callback(self, frame, results, fps, inference_time, progress=None):
        # Update UI if available, otherwise log
        try:
            if hasattr(self.app, 'ui') and getattr(self.app, 'ui', None):
                upd = getattr(self.app.ui, 'on_inference_result', None)
                if callable(upd):
                    try:
                        upd(frame=frame, results=results, fps=fps, inference_time=inference_time, progress=progress)
                        return
                    except Exception:
                        pass
        except Exception:
            pass

        # fallback: try to log
        try:
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(f"Inference result: fps={fps}, time={inference_time}")
        except Exception:
            pass