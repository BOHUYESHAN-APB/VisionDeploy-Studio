#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型管理后端：加载 resources/models.json，列出模型，选择镜像，下载，校验和导入
"""

import json
import os
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import requests
except Exception:
    requests = None

# 设置日志
logger = logging.getLogger(__name__)

MODELS_DB_PATH = Path("resources") / "models.json"
DEFAULT_MODELS_DIR = Path("models")

# By default, built-in models DB is disabled to enforce selecting models from HF.
# Set USE_LOCAL_MODELS_DB=1 in environment or pass an explicit path to enable.
USE_LOCAL_MODELS_DB = bool(os.environ.get('USE_LOCAL_MODELS_DB'))


def load_models_db(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else MODELS_DB_PATH
    # if the built-in models DB is disabled, return empty structure
    if not USE_LOCAL_MODELS_DB:
        logger.info("本地内置模型数据库被禁用（USE_LOCAL_MODELS_DB 未设置），返回空模型列表")
        return {"models": []}
    if not p.exists():
        logger.warning(f"models.json 未找到: {p}")
        # 返回默认结构
        return {"models": []}
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"成功加载模型数据库，包含 {len(data.get('models', []))} 个模型")
            return data
    except Exception as e:
        logger.error(f"加载模型数据库失败: {e}")
        return {"models": []}


def list_models(db: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if db is None:
        db = load_models_db()
    models = db.get("models", [])
    logger.info(f"列出 {len(models)} 个模型")
    return models


def get_model_entry(model_id: str, db: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if db is None:
        db = load_models_db()
    for m in db.get("models", []):
        if m.get("id") == model_id:
            logger.info(f"找到模型: {model_id}")
            return m
    logger.warning(f"未找到模型: {model_id}")
    return None


def _choose_version(entry: Dict[str, Any], version: Optional[str]) -> Dict[str, Any]:
    versions = entry.get("versions", [])
    if not versions:
        logger.warning("模型条目无版本信息")
        raise ValueError("模型条目无版本信息")
    
    if version is None:
        selected = versions[-1]
        logger.info(f"选择默认版本: {selected.get('version', 'unknown')}")
        return selected
    
    # 精确匹配
    for v in versions:
        if v.get("version") == version or v.get("filename") == version:
            logger.info(f"找到精确匹配版本: {version}")
            return v
    
    # 前缀匹配
    for v in versions:
        if v.get("version", "").startswith(version):
            logger.info(f"找到前缀匹配版本: {version} -> {v.get('version', 'unknown')}")
            return v
    
    # 回退到最后一个版本
    selected = versions[-1]
    logger.warning(f"未找到匹配版本 {version}，回退到默认版本: {selected.get('version', 'unknown')}")
    return selected


def _select_url_for_version(version_entry: Dict[str, Any], mirror_preference: str, db: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    mirror_preference: one of 'cn','global','official','huggingface','auto'
    """
    urls = version_entry.get("urls", {}) or {}
    logger.info(f"选择镜像: {mirror_preference}")
    
    if mirror_preference == "official":
        url = urls.get("official") or urls.get("huggingface")
        logger.info(f"选择官方镜像: {url}")
        return url
    if mirror_preference == "huggingface":
        url = urls.get("huggingface") or urls.get("official")
        logger.info(f"选择HuggingFace镜像: {url}")
        return url
    if mirror_preference == "cn":
        url = urls.get("mirror_cn") or urls.get("official") or urls.get("huggingface")
        logger.info(f"选择国内镜像: {url}")
        return url
    if mirror_preference == "global":
        url = urls.get("huggingface") or urls.get("official") or urls.get("mirror_cn")
        logger.info(f"选择全球镜像: {url}")
        return url
    # auto: prefer mirror_cn if present, else huggingface/official
    if mirror_preference == "auto":
        if urls.get("mirror_cn"):
            url = urls.get("mirror_cn")
            logger.info(f"自动选择国内镜像: {url}")
            return url
        url = urls.get("huggingface") or urls.get("official") or urls.get("mirror_cn")
        logger.info(f"自动选择镜像: {url}")
        return url
    
    # 默认情况
    url = urls.get("huggingface") or urls.get("official") or urls.get("mirror_cn")
    logger.info(f"默认选择镜像: {url}")
    return url


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
        error_msg = "requests 未安装，无法下载。请运行 pip install requests"
        logger.error(error_msg)
        print(error_msg)
        if callback:
            try:
                callback("requests_missing", -1)
            except:
                pass
        return False
    
    try:
        logger.info(f"开始下载: {url} -> {dest_path}")
        if callback:
            callback(f"开始下载 {dest_path.name}", 0)
        
        with requests.get(url, stream=True, timeout=30, verify=False) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0) or 0)
            _ensure_dir(dest_path.parent)
            
            if callback:
                callback(f"连接成功，开始下载 {dest_path.name}", 5)
            
            with dest_path.open("wb") as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    # 支持 best-effort 取消
                    try:
                        if stop_event and stop_event.is_set():
                            cancel_msg = "下载已被取消"
                            logger.info(cancel_msg)
                            print(cancel_msg)
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
                            # 避免频繁更新进度
                            if pct % 5 == 0 or pct == 100:
                                progress_msg = f"下载 {dest_path.name}: {downloaded}/{total} bytes ({pct}%)"
                                print(progress_msg, end="\r")
                                if callback:
                                    try:
                                        callback(progress_msg, pct)
                                    except:
                                        pass
        if show_progress:
            print()
        
        # 校验文件
        if expected_sha256:
            if callback:
                callback(f"正在校验 {dest_path.name}", 95)
            
            actual = _sha256_of_file(dest_path)
            if actual != expected_sha256:
                error_msg = f"校验失败: sha256 不匹配，期望 {expected_sha256} 实际 {actual}"
                logger.error(error_msg)
                print(error_msg)
                if callback:
                    try:
                        callback("checksum_failed", -1)
                    except:
                        pass
                return False
        
        success_msg = f"下载完成: {dest_path}"
        logger.info(success_msg)
        print(success_msg)
        if callback:
            try:
                callback(f"下载完成: {dest_path.name}", 100)
            except:
                pass
        return True
    except Exception as e:
        error_msg = f"下载失败 {url} -> {dest_path}: {e}"
        logger.error(error_msg)
        print(error_msg)
        if callback:
            try:
                callback(f"下载失败: {e}", -1)
            except:
                pass
        return False


def download_model(model_id: str, version: Optional[str] = None, dest_dir: Optional[Path] = None, mirror: str = "auto", callback=None, stop_event=None) -> Optional[Path]:
    logger.info(f"开始下载模型: {model_id}, 版本: {version}, 镜像: {mirror}")
    
    # 通知开始
    if callback:
        callback(f"正在查找模型: {model_id}", 0)
    
    db = load_models_db()
    entry = get_model_entry(model_id, db)
    if entry is None:
        error_msg = f"未找到模型 id: {model_id}"
        logger.error(error_msg)
        print(error_msg)
        if callback:
            callback(error_msg, -1)
        return None
    
    # 通知找到模型
    if callback:
        callback(f"找到模型: {entry.get('display_name', model_id)}", 10)
    
    ver = _choose_version(entry, version)
    url = _select_url_for_version(ver, mirror, db)
    if not url:
        error_msg = f"未能为该版本选择下载 URL: {model_id} v{ver.get('version', 'unknown')}"
        logger.error(error_msg)
        print(error_msg)
        if callback:
            callback(error_msg, -1)
        return None
    
    # 通知选择URL
    if callback:
        callback(f"选择下载链接: {url}", 20)
    
    dest = Path(dest_dir) if dest_dir else DEFAULT_MODELS_DIR
    _ensure_dir(dest)
    filename = ver.get("filename") or ver.get("version") or "unknown_model"
    dest_path = dest / filename
    expected_sha256 = ver.get("checksums", {}).get("sha256") or None
    
    start_msg = f"开始下载模型 {entry.get('display_name', model_id)} ({model_id}) 版本 {ver.get('version', 'unknown')} -> {dest_path}"
    logger.info(start_msg)
    print(start_msg)
    
    ok = download_file(url, dest_path, expected_sha256, callback=callback, stop_event=stop_event)
    if not ok and (not stop_event or not stop_event.is_set()):
        warning_msg = "尝试使用备用链接..."
        logger.warning(warning_msg)
        print(warning_msg)
        if callback:
            callback("尝试使用备用链接...", 80)
        
        # try other urls in urls dict
        urls = ver.get("urls", {}) or {}
        for k, u in urls.items():
            if u and u != url:
                if stop_event and stop_event.is_set():
                    break
                print(f"尝试 {k} -> {u}")
                if callback:
                    callback(f"尝试备用链接: {k}", 85)
                if download_file(u, dest_path, expected_sha256, callback=callback, stop_event=stop_event):
                    ok = True
                    break
    
    if not ok:
        error_msg = "下载所有链接失败"
        logger.error(error_msg)
        print(error_msg)
        if callback:
            callback(error_msg, -1)
        return None
    
    logger.info(f"模型下载完成: {dest_path}")
    return dest_path


def import_local_model(src_path: str, dest_dir: Optional[Path] = None) -> Path:
    logger.info(f"开始导入本地模型: {src_path}")
    src = Path(src_path)
    if not src.exists():
        error_msg = f"文件不存在: {src_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    dest = Path(dest_dir) if dest_dir else DEFAULT_MODELS_DIR
    _ensure_dir(dest)
    dst = dest / src.name
    shutil.copy2(src, dst)
    success_msg = f"已导入模型到 {dst}"
    logger.info(success_msg)
    print(success_msg)
    return dst


def find_local_models(models_dir: Optional[Path] = None) -> List[Path]:
    d = Path(models_dir) if models_dir else DEFAULT_MODELS_DIR
    logger.info(f"查找本地模型: {d}")
    
    if not d.exists():
        logger.warning(f"模型目录不存在: {d}")
        return []
    
    try:
        models = [p for p in d.iterdir() if p.is_file() and p.suffix in (".pt", ".pth", ".onnx", ".tflite", ".bin", ".safetensors")]
        logger.info(f"找到 {len(models)} 个本地模型")
        return models
    except Exception as e:
        logger.error(f"查找本地模型失败: {e}")
        return []


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