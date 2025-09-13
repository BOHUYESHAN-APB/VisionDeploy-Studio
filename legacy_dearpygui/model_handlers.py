"""Archived DearPyGui model_handlers.

This file contains the original DearPyGui-heavy implementation and is
kept for historical reference. The active, lightweight CTk-compatible
helpers live in `app/handlers/model_handlers.py`.

If you need to restore the original behavior, copy relevant functions
from here back into `app/handlers/model_handlers.py` or import this
module directly.
"""

# Original implementation archived. Restore from git history if needed.
ARCHIVE_NOTE = (
    "This file stores the original DearPyGui-based model handlers.\n"
    "It has been archived to avoid pulling DearPyGui into the main app.\n"
    "Restore from source control if required."
)

def archived_info():
    return ARCHIVE_NOTE
"""Archived DearPyGui model handlers.

Contains the original DearPyGui-centric model handler classes and helpers.
Archived for reference.
"""

def archived_note():
    return "Model handlers archived. Use app/handlers/model_handlers.py (shim) or app/gui_ctk.py"
