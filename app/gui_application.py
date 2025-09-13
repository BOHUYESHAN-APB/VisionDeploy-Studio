"""Archived DearPyGui frontend stub.

The original DearPyGui implementation was moved to
`legacy_dearpygui/gui_application.py`. This module is a small, safe stub
that provides metadata and a minimal shim so importing `app.gui_application`
does not pull in DearPyGui or cause runtime errors.
"""

from pathlib import Path
from typing import Dict


def archived_info() -> Dict[str, str]:
    """Return metadata pointing to the archived DearPyGui implementation."""
    archived = (Path(__file__).parent / '..' / 'legacy_dearpygui' / 'gui_application.py').resolve()
    return {
        'note': 'DearPyGui frontend archived. Use app/gui_ctk.py instead.',
        'archived_path': str(archived)
    }


class YOLODeployAppStub:
    """A minimal placeholder for the original YOLODeployApp.

    This class intentionally does not import or reference DearPyGui. It
    provides the small surface area needed by other modules that may import
    the original class for inspection or tests.
    """

    def __init__(self):
        self._archived = True

    def info(self) -> Dict[str, str]:
        return archived_info()


__all__ = ["archived_info", "YOLODeployAppStub"]