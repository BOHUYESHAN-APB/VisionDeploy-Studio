#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型管理后端：加载 resources/models.json，列出模型，选择镜像，下载，校验和导入
"""

import json
import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import requests
except Exception:
    requests = None

MODELS_DB_PATH = Path("resources") / "models.json"
DEFAULT_MODELS_DIR = Path("models")


def load_models_db(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else MODELS_DB_PATH
    if not p.exists():
        raise FileNotFoundError(f"models.json 未找到: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_models(db: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if db is None:
        db = load_models_db()
    return db.get("models", [])


def get_model_entry(model_id: str, db: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if db is None:
        db = load_models_db()
    for m in db.get("models", []):
        if m.get("id") == model_id:
            return m
    return None


def _choose_version(entry: Dict[str, Any], version: Optional[str]) -> Dict[str, Any]:
    versions = entry.get("versions", [])
    if not versions:
        raise ValueError("模型条目无版本信息")
    if version is None:
        return versions[-1]
    for v in versions:
        if v.get("version") == version or v.get("filename") == version:
            return v
    for v in versions:
        if v.get("version", "").startswith(version):
            return v
    # fallback to last
    return versions[-1]


def _select_url_for_version(version_entry: Dict[str, Any], mirror_preference: str, db: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    mirror_preference: one of 'cn','global','official','huggingface','auto'
    """
    urls = version_entry.get("urls", {}) or {}
    if mirror_preference == "official":
        return urls.get("official") or urls.get("huggingface")
    if mirror_preference == "huggingface":
        return urls.get("huggingface") or urls.get("official")
    if mirror_preference == "cn":
        return urls.get("mirror_cn") or urls.get("official") or urls.get("huggingface")
    if mirror_preference == "global":
        return urls.get("huggingface") or urls.get("official") or urls.get("mirror_cn")
    # auto: prefer mirror_cn if present, else huggingface/official
    if mirror_preference == "auto":
        if urls.get("mirror_cn"):
            return urls.get("mirror_cn")
        return urls.get("huggingface") or urls.get("official") or urls.get("mirror_cn")
    return None


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest_path: Path, expected_sha256: Optional[str] = None, show_progress: bool = True, callback=None, stop_event=None) -> bool:
    """
    下载单文件，增加 callback(progress) 与 stop_event 用于 UI 回调与取消请求（best-effort）。
    callback: callable(message, percent) - message: str, percent: int (-1 表示不可用/错误)
    stop_event: threading.Event 可选，若 set() 则尝试中断下载并返回 False
    """
    if requests is None:
        print("requests 未安装，无法下载。请运行 pip install requests")
        if callback:
            try:
                callback("requests_missing", -1)
            except:
                pass
        return False
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0) or 0)
            _ensure_dir(dest_path.parent)
            with dest_path.open("wb") as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    # 支持 best-effort 取消
                    try:
                        if stop_event and stop_event.is_set():
                            print("下载已被取消")
                            if callback:
                                try:
                                    callback("cancelled", -1)
                                except:
                                    pass
                            return False
                    except:
                        pass
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if show_progress and total:
                            pct = int(downloaded * 100 // total)
                            print(f"下载 {dest_path.name}: {downloaded}/{total} bytes ({pct}%)", end="\r")
                            if callback:
                                try:
                                    callback("downloading", pct)
                                except:
                                    pass
        if show_progress:
            print()
        if expected_sha256:
            actual = _sha256_of_file(dest_path)
            if actual != expected_sha256:
                print(f"校验失败: sha256 不匹配，期望 {expected_sha256} 实际 {actual}")
                if callback:
                    try:
                        callback("checksum_failed", -1)
                    except:
                        pass
                return False
        print(f"下载完成: {dest_path}")
        if callback:
            try:
                callback("completed", 100)
            except:
                pass
        return True
    except Exception as e:
        print(f"下载失败 {url} -> {dest_path}: {e}")
        if callback:
            try:
                callback("error", -1)
            except:
                pass
        return False


def download_model(model_id: str, version: Optional[str] = None, dest_dir: Optional[Path] = None, mirror: str = "auto") -> Optional[Path]:
    db = load_models_db()
    entry = get_model_entry(model_id, db)
    if entry is None:
        print(f"未找到模型 id: {model_id}")
        return None
    ver = _choose_version(entry, version)
    url = _select_url_for_version(ver, mirror, db)
    if not url:
        print("未能为该版本选择下载 URL")
        return None
    dest = Path(dest_dir) if dest_dir else DEFAULT_MODELS_DIR
    _ensure_dir(dest)
    filename = ver.get("filename") or ver.get("version")
    dest_path = dest / filename
    expected_sha256 = ver.get("checksums", {}).get("sha256") or None
    print(f"开始下载模型 {entry.get('display_name')} ({model_id}) 版本 {ver.get('version')} -> {dest_path}")
    ok = download_file(url, dest_path, expected_sha256)
    if not ok:
        print("尝试使用备用链接...")
        # try other urls in urls dict
        urls = ver.get("urls", {}) or {}
        for k, u in urls.items():
            if u and u != url:
                print(f"尝试 {k} -> {u}")
                if download_file(u, dest_path, expected_sha256):
                    ok = True
                    break
    if not ok:
        print("下载所有链接失败")
        return None
    return dest_path


def import_local_model(src_path: str, dest_dir: Optional[Path] = None) -> Path:
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(src_path)
    dest = Path(dest_dir) if dest_dir else DEFAULT_MODELS_DIR
    _ensure_dir(dest)
    dst = dest / src.name
    shutil.copy2(src, dst)
    print(f"已导入模型到 {dst}")
    return dst


def find_local_models(models_dir: Optional[Path] = None) -> List[Path]:
    d = Path(models_dir) if models_dir else DEFAULT_MODELS_DIR
    if not d.exists():
        return []
    return [p for p in d.iterdir() if p.is_file() and p.suffix in (".pt", ".pth", ".onnx", ".tflite")]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="模型管理器命令行")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("list", help="列出可用模型")
    dl = sub.add_parser("download", help="下载模型")
    dl.add_argument("model_id")
    dl.add_argument("--version", default=None)
    dl.add_argument("--mirror", default="auto", choices=["auto", "cn", "global", "official", "huggingface"])
    dl.add_argument("--dest", default=str(DEFAULT_MODELS_DIR))
    imp = sub.add_parser("import", help="导入本地模型")
    imp.add_argument("path")
    imp.add_argument("--dest", default=str(DEFAULT_MODELS_DIR))

    args = parser.parse_args()
    if args.cmd == "list":
        for m in list_models():
            print(f"{m.get('id')} - {m.get('display_name')} ({m.get('family')})")
            for v in m.get("versions", []):
                print(f"  - {v.get('version')} -> {v.get('filename')}")
    elif args.cmd == "download":
        p = download_model(args.model_id, version=args.version, dest_dir=Path(args.dest), mirror=args.mirror)
        if p:
            print(f"下载完成: {p}")
    elif args.cmd == "import":
        p = import_local_model(args.path, dest_dir=Path(args.dest))
        print(f"导入完成: {p}")
    else:
        parser.print_help()