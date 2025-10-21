import json
from pathlib import Path

PREFS_PATH = Path('config') / 'ui_prefs.json'


def load_prefs():
    try:
        if PREFS_PATH.exists():
            return json.loads(PREFS_PATH.read_text(encoding='utf-8')) or {}
    except Exception:
        pass
    return {}


def save_prefs(data: dict):
    try:
        PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        PREFS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return True
    except Exception:
        return False
