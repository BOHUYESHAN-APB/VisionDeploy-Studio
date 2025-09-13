"""Handlers shim for CTk frontend.

This module provides a small set of helpers used by `app/gui_ctk.py`.
The original DearPyGui-heavy implementation is archived under
`legacy_dearpygui/model_handlers.py`.
"""

from pathlib import Path
from typing import List

def load_model_device_map() -> dict:
    try:
        p = Path("config") / "model_device_map.yaml"
        if not p.exists():
            return {}
        try:
            import yaml
            with p.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            mapping = {}
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    if ':' in line:
                        k, v = line.split(':', 1)
                        mapping[k.strip()] = v.strip()
            return mapping
    except Exception:
        return {}


def save_model_device_map(mapping: dict):
    try:
        p = Path("config")
        p.mkdir(parents=True, exist_ok=True)
        target = p / "model_device_map.yaml"
        try:
            import yaml
            with target.open("w", encoding="utf-8") as f:
                yaml.safe_dump(mapping, f, allow_unicode=True, sort_keys=False)
        except Exception:
            with target.open("w", encoding="utf-8") as f:
                for k, v in mapping.items():
                    f.write(f"{k}: {v}\n")
    except Exception as e:
        raise e


def get_quantized_options_for_model(models_list: List[dict], model_id: str) -> List[str]:
    try:
        items = ["无量化模型"]
        if not models_list or not model_id:
            return items
        for m in models_list:
            mid = m.get("id") or ""
            if mid == model_id or m.get("display_name") == model_id:
                vers = m.get("versions", []) or []
                if vers:
                    q = vers[-1].get("quantized", []) or []
                    if q:
                        items = ["无量化模型"] + [qq.get("name") or qq.get("filename") for qq in q]
                break
        return items
    except Exception:
        return ["无量化模型"]


def on_model_change_ctk(app, sel_value: str, use_ctk: bool = True):
    # Lightweight delegation kept for CTk frontend compatibility; it will
    # attempt to update UI labels and pop a small dialog for device choice.
    try:
        if not sel_value or sel_value == "自动选择":
            try:
                if hasattr(app, "model_label") and app.model_label is not None:
                    try:
                        if use_ctk:
                            app.model_label.configure(text="模型: 自动选择")
                        else:
                            app.model_label.config(text="模型: 自动选择")
                    except:
                        pass
            except:
                pass
            return
        # delegate to existing helper in this module for device mapping UI
        # For full behavior see legacy_dearpygui/model_handlers.py
        mid = sel_value.split('(')[-1].strip(')')
        # no-op: leave detailed behavior to CTk implementation or user handlers
    except Exception:
        pass