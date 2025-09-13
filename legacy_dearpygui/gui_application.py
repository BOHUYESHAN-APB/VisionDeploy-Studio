"""Archived DearPyGui frontend for VisionDeploy Studio.

This file is a legacy copy of the original DearPyGui-based UI and has been
moved to the `legacy_dearpygui/` folder because the project now uses a
CustomTkinter (CTk) frontend (`app/gui_ctk.py`).

If you need to inspect the original DearPyGui implementation, open this file.
Do not import it from the main code path; it is kept for reference and possible
future porting only.
"""

from pathlib import Path

# The original DearPyGui implementation was large and has been archived here.
# To view the original implementation, open the file in this path. This stub
# intentionally does not import or execute DearPyGui.

__all__ = ["archived"]

def archived():
    return {
        "note": "This DearPyGui frontend has been archived. Use app/gui_ctk.py instead.",
        "path": str(Path(__file__).resolve())
    }
