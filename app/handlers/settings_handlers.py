"""Settings handlers shim (DearPyGui archived)

The original implementation used DearPyGui for UI dialogs; that code has
been archived into `legacy_dearpygui/settings_handlers.py`. This module
provides a minimal SettingsHandlers class suitable for the CTk frontend
that avoids importing DearPyGui at import time.
"""

import os
from typing import Optional


def archived_info() -> dict:
    from pathlib import Path
    archived = (Path(__file__).parent / '..' / 'legacy_dearpygui' / 'model_handlers.py').resolve()
    return {'archived_path': str(archived), 'note': 'DearPyGui settings handlers archived.'}


class SettingsHandlers:
    """Minimal settings handler that does not import DearPyGui.

    It preserves the public method names used elsewhere (exit_app,
    toggle_theme, save_settings, reset_settings, show_about) but implements
    UI actions as no-ops. The CTk frontend will provide full dialogs.
    """

    def __init__(self, app):
        self.app = app
        self.logger = getattr(app, 'logger', None)

    def exit_app(self):
        try:
            self.app.save_config()
        except Exception:
            pass
        finally:
            import sys
            sys.exit(0)

    def toggle_theme(self):
        self.app.app_state['dark_mode'] = not self.app.app_state.get('dark_mode', True)
        # CTk frontend will react to this state change

    def toggle_performance_monitoring(self):
        self.app.app_state['performance_monitoring'] = not self.app.app_state.get('performance_monitoring', True)

    def set_network_timeout(self, sender, value):
        self.app.app_state['network_timeout'] = value

    def set_network_retries(self, sender, value):
        self.app.app_state['network_retries'] = value

    def set_models_path(self, sender, value):
        self.app.app_state['models_path'] = value
        if hasattr(self.app, 'model_manager'):
            try:
                self.app.model_manager.models_dir = value
            except Exception:
                pass

    def browse_models_path(self):
        # CTk frontend should implement an actual folder chooser
        return None

    def set_environments_path(self, sender, value):
        self.app.app_state['environments_path'] = value
        if hasattr(self.app, 'environment_manager'):
            try:
                self.app.environment_manager.environments_dir = value
            except Exception:
                pass

    def browse_environments_path(self):
        return None

    def save_settings(self):
        try:
            self.app.save_config()
        except Exception:
            pass

    def reset_settings(self):
        self.app.app_state = {
            'dark_mode': True,
            'performance_monitoring': True,
            'network_timeout': 30,
            'network_retries': 3,
            'models_path': os.path.join(getattr(self.app, 'base_dir', '.'), 'resources', 'models'),
            'environments_path': os.path.join(getattr(self.app, 'base_dir', '.'), 'environments')
        }

    def show_settings(self):
        # CTk frontend will show the settings dialog
        return None

    def open_docs(self):
        # Let the frontend open docs (CTk will implement)
        return None

    def show_about(self):
        # Return a simple about payload; frontend can render it
        return {
            'title': 'VisionDeploy Studio',
            'description': 'Local deployment tool for computer vision models.'
        }