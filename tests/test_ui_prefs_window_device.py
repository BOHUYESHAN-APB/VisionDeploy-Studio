import json
import sys
from pathlib import Path
import tempfile
import os

# Ensure the project root is on sys.path so `app` can be imported
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import ui_prefs


def test_save_and_load_window_geometry_and_device(tmp_path, monkeypatch):
    # Use a temporary config path to avoid touching real config
    temp_config_dir = tmp_path / "config"
    temp_config_dir.mkdir()
    temp_prefs = temp_config_dir / "ui_prefs.json"

    # Monkeypatch the PREFS_PATH used by app.ui_prefs
    monkeypatch.setattr(ui_prefs, 'PREFS_PATH', temp_prefs)

    data = {
        'window_geometry': '1024x768+10+20',
        'device': 'GPU - Nvidia',
        'mirror': 'cn',
        'zoom': '110%'
    }

    ok = ui_prefs.save_prefs(data)
    assert ok is True

    loaded = ui_prefs.load_prefs()
    assert isinstance(loaded, dict)
    assert loaded.get('window_geometry') == '1024x768+10+20'
    assert loaded.get('device') == 'GPU - Nvidia'
    assert loaded.get('mirror') == 'cn'
    assert loaded.get('zoom') == '110%'
