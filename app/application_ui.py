"""Application UI shim (DearPyGui archived)

This module provides a minimal ApplicationUI class that avoids importing
DearPyGui at import time. The original DearPyGui-based implementation has
been moved to `legacy_dearpygui/application_ui.py`.
"""

from pathlib import Path
from typing import Dict, Any, Optional


def archived_info() -> Dict[str, str]:
    archived = (Path(__file__).parent / '..' / 'legacy_dearpygui' / 'application_ui.py').resolve()
    return {'archived_path': str(archived), 'note': 'DearPyGui application UI archived.'}


class ApplicationUI:
    """Minimal UI facade used by the rest of the application.

    Methods mirror the original interface but are implemented without
    DearPyGui. The CTk frontend provides full UI behavior.
    """

    def __init__(self, app):
        self.app = app
        self.ui_text: Dict[str, str] = {}

    def reset_layout(self):
        return None

    def setup_ui(self):
        # CTk frontend implements real setup; this is a no-op shim
        return None

    def is_dearpygui_running(self):
        return False

    def render_dearpygui_frame(self):
        return None

    def _load_chinese_font(self):
        try:
            from app.font_initializer import initialize_chinese_font
            project_root = getattr(self.app, 'base_dir', None)
            if not project_root:
                project_root = str(Path(__file__).resolve().parents[1])
            return initialize_chinese_font(project_root)
        except Exception:
            return False

    def _setup_models_tab(self):
        return None

    def _setup_inference_tab(self):
        return None

    def _setup_environments_tab(self):
        return None

    def _setup_settings_tab(self):
        return None

    def update_ui_text(self):
        return None

    def update_hardware_info(self):
        return None

    def update_performance_data(self, performance_data):
        return None