"""Environment handlers shim (DearPyGui archived)

Provides environment-related operations without importing DearPyGui at
module import time. UI rendering is left to the frontend (CTk/Tk/other).
"""

import os
from typing import Dict, List, Any, Optional


def archived_info() -> Dict[str, str]:
    from pathlib import Path
    archived = (Path(__file__).parent / '..' / 'legacy_dearpygui' / 'environment_handlers.py').resolve()
    return {'archived_path': str(archived), 'note': 'DearPyGui environment handlers archived.'}


class EnvironmentHandlers:
    def __init__(self, app):
        self.app = app
        self.logger = getattr(app, 'logger', None)

    def refresh_environments(self):
        try:
            envs = self.app.environment_manager.list_environments()
        except Exception:
            envs = []
        # Let UI layer render envs; if none, just log
        try:
            if self.logger:
                self.logger.info(f"Environments refreshed: {len(envs)}")
        except Exception:
            pass

    def filter_environments(self, sender=None, value=None):
        # Rely on environment_manager to return filtered results if supported
        try:
            if value:
                envs = [e for e in self.app.environment_manager.list_environments() if value.lower() in e['name'].lower()]
            else:
                envs = self.app.environment_manager.list_environments()
            try:
                if self.logger:
                    self.logger.info(f"Filtered environments: {len(envs)}")
            except Exception:
                pass
        except Exception:
            pass

    def select_environment(self, environment):
        try:
            # let UI layer display details via app.ui if available
            if hasattr(self.app, 'ui') and getattr(self.app, 'ui', None):
                disp = getattr(self.app.ui, 'show_environment_details', None)
                if callable(disp):
                    try:
                        disp(environment)
                        return
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            if self.logger:
                self.logger.info(f"Selected environment: {environment.get('name')}")
        except Exception:
            pass

    def create_selected_environment(self):
        try:
            env_name = getattr(self.app, 'pending_environment_name', None)
            if not env_name:
                return
            success = self.app.environment_manager.create_environment(env_name)
            return success
        except Exception:
            return False

    def delete_selected_environment(self):
        try:
            env_name = getattr(self.app, 'selected_environment_name', None)
            if not env_name:
                return False
            return self.app.environment_manager.delete_environment(env_name)
        except Exception:
            return False

    def edit_selected_environment(self):
        # UI should call into environment_manager directly for edits
        return None

    def _add_package_to_environment(self, env_name):
        try:
            package_spec = getattr(self.app, 'pending_package_spec', None)
            if not package_spec:
                return False
            return self.app.environment_manager.add_package(env_name, package_spec)
        except Exception:
            return False

    def _remove_package_from_environment(self, env_name):
        try:
            package_spec = getattr(self.app, 'pending_package_spec', None)
            if not package_spec:
                return False
            return self.app.environment_manager.remove_package(env_name, package_spec)
        except Exception:
            return False

    def _save_environment_changes(self, env_name):
        try:
            new_python_version = getattr(self.app, 'pending_python_version', None)
            return self.app.environment_manager.update_environment(env_name, new_python_version)
        except Exception:
            return False

    def show_add_environment_dialog(self):
        # Frontend should implement this; shim is no-op
        return None

    def _create_new_environment(self):
        try:
            env_name = getattr(self.app, 'new_environment_name', None)
            python_version = getattr(self.app, 'new_environment_python_version', None)
            if not env_name:
                return False
            return self.app.environment_manager.create_environment(env_name, python_version)
        except Exception:
            return False

    def _create_new_environment(self):
        # duplicate safe implementation
        return self._create_new_environment()