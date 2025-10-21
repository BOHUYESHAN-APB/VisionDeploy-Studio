import os
import json
from pathlib import Path
import tempfile

from app.ui_prefs import load_prefs, save_prefs


def test_save_and_load_prefs(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config"
    monkeypatch.chdir(tmp_path)
    data = {"mirror": "cn", "zoom": "125%"}
    ok = save_prefs(data)
    assert ok
    assert (cfg_dir / 'ui_prefs.json').exists()
    loaded = load_prefs()
    assert loaded.get('mirror') == 'cn'
    assert loaded.get('zoom') == '125%'
