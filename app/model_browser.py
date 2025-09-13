"""Model browser shim (DearPyGui archived)

The original DearPyGui implementation has been archived into
`legacy_dearpygui/model_browser.py`. This file provides a minimal,
import-safe shim that avoids importing DearPyGui at module import time.

If the full DearPyGui UI is needed, open the archived file.
"""
from pathlib import Path
from typing import List, Dict, Optional


def archived_info() -> Dict[str, str]:
    archived = (Path(__file__).parent / '..' / 'legacy_dearpygui' / 'model_browser.py').resolve()
    return {
        'archived_path': str(archived),
        'note': 'DearPyGui ModelBrowser archived. Use app/gui_ctk.py for the CTk UI.'
    }


class ModelBrowser:
    """Minimal runtime-friendly shim for the model browser.

    This class intentionally avoids importing dearpygui. It exposes a
    small API used by other parts of the app: refresh_models(),
    download_selected(), and run_model(). Implementations are no-ops or
    call into core.model_manager when available.
    """

    def __init__(self, model_manager=None):
        self.selected_model = None
        self.available_models: List[Dict] = []
        self.downloaded_models: List[Dict] = []
        self.model_manager = model_manager

    def refresh_models(self):
        if self.model_manager:
            try:
                self.available_models = self.model_manager.discover_models()
                self.downloaded_models = self.model_manager.list_downloaded_models()
            except Exception:
                # best-effort; keep lists empty on error
                self.available_models = []
                self.downloaded_models = []

    def download_selected(self):
        if not self.selected_model or not self.model_manager:
            return False
        try:
            self.model_manager.download_model(self.selected_model)
            return True
        except Exception:
            return False

    def run_model(self):
        if not self.selected_model or not self.model_manager:
            return False
        try:
            path = self.model_manager.get_model_path(self.selected_model.get('name'))
            if path:
                # real runner lives elsewhere; here we only indicate success
                return True
            return False
        except Exception:
            return False


# convenience global used by older code paths
model_browser = ModelBrowser()