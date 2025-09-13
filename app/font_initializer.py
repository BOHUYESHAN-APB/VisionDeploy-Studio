"""Font initializer shim (DearPyGui archived)

The original module relied on DearPyGui APIs at import/runtime. To
avoid importing DearPyGui during module import, this shim exposes the
same function names but implements them in a deferred, import-safe way.
If DearPyGui is available at runtime, the CTk frontend or other code may
call into the legacy implementation from `legacy_dearpygui`.
"""

from pathlib import Path
from typing import Dict


def archived_info() -> Dict[str, str]:
    archived = (Path(__file__).parent / '..' / 'legacy_dearpygui' / 'font_initializer.py').resolve()
    return {'archived_path': str(archived), 'note': 'DearPyGui font_initializer archived.'}


def initialize_chinese_font(project_root) -> bool:
    """Deferred font initializer: try to call legacy impl if available.

    This function intentionally avoids importing dearpygui at module
    import time. It tries to import and call the archived implementation
    on demand.
    """
    try:
        from legacy_dearpygui import font_initializer as legacy
        return legacy.initialize_chinese_font(project_root)
    except Exception:
        # Best-effort: inspect resources/fonts and return False if nothing
        # obviously available.
        fonts_dir = Path(project_root) / 'resources' / 'fonts'
        if fonts_dir.exists() and any(fonts_dir.glob('*.ttf')):
            return False
        return False


def rebind_default_font() -> bool:
    try:
        from legacy_dearpygui import font_initializer as legacy
        return legacy.rebind_default_font()
    except Exception:
        return False


def initialize_chinese_font_debug(project_root) -> Dict:
    try:
        from legacy_dearpygui import font_initializer as legacy
        return legacy.initialize_chinese_font_debug(project_root)
    except Exception:
        return {'project_root': str(project_root), 'success': False, 'error': 'legacy not available'}