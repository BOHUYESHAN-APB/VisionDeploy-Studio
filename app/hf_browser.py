#!/usr/bin/env python3
"""
Simple Hugging Face browser helper.

Provides search, list files and download helpers with best-effort mirror support.
This is intentionally lightweight and uses the public HF API endpoints.
"""
from pathlib import Path
from typing import List, Dict, Optional
import requests

HF_API_BASE = "https://huggingface.co/api"


def search_models(query: str, limit: int = 20, api_base: Optional[str] = None) -> List[Dict]:
    """Search models. api_base can override the HF API base (e.g. a mirror).

    api_base should point to the base URL that exposes the same /api/models endpoint.
    """
    try:
        base = api_base.rstrip('/') if api_base else HF_API_BASE
        params = {'search': query, 'limit': limit}
        r = requests.get(f"{base}/models", params=params, timeout=15)
        r.raise_for_status()
        return r.json() or []
    except Exception:
        return []


def list_model_files(repo_id: str, api_base: Optional[str] = None) -> List[Dict]:
    """List files in a model repo.

    Returns list of dicts: {"name": str, "size": int|None, "type": str|None}
    """
    try:
        base = api_base.rstrip('/') if api_base else HF_API_BASE
        r = requests.get(f"{base}/models/{repo_id}/files", timeout=15)
        # if endpoint not found (some mirrors may not implement), fall through to probing
        if r.status_code == 404:
            raise FileNotFoundError()
        r.raise_for_status()
        data = r.json() or []
        files = []
        for it in data:
            # the HF files endpoint sometimes returns plain filenames or dicts
            if isinstance(it, dict):
                name = it.get('name') or it.get('path') or ''
                size = it.get('size') if 'size' in it else None
                ftype = it.get('type') if 'type' in it else None
            else:
                name = str(it)
                size = None
                ftype = None
            files.append({"name": name, "size": size, "type": ftype})
        return files
    except FileNotFoundError:
        # fallback: attempt to probe a list of common filenames via HEAD/GET
        common = [
            'README.md', 'README', 'config.json', 'model_index.json', 'pytorch_model.bin',
            'tf_model.h5', 'flax_model.msgpack', 'adapter_config.json'
        ]
        found = []
        # determine download base for raw file access
        raw_base = "https://huggingface.co"
        if api_base and isinstance(api_base, str) and api_base.startswith('http'):
            # if api_base is a mirror and ends with /api, remove the /api part to form raw base
            raw_base = api_base.rstrip('/')
            if raw_base.endswith('/api'):
                raw_base = raw_base[:-4]
        # browser-like headers to avoid mirror warnings and redirects
        repo_referer = f"https://huggingface.co/{repo_id}"
        probe_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/markdown, text/plain, */*',
            'Referer': repo_referer,
            'Origin': 'https://huggingface.co',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin'
        }

        for fname in common:
            url = f"{raw_base}/{repo_id}/resolve/main/{fname}"
            try:
                # try HEAD without following redirects to detect Location
                try:
                    h = requests.head(url, timeout=8, allow_redirects=False, headers=probe_headers)
                except Exception:
                    h = None
                loc = h.headers.get('Location') if h is not None else None
                if loc:
                    try:
                        # follow redirect with updated Referer
                        rh = probe_headers.copy()
                        rh['Referer'] = loc
                        r2 = requests.get(loc, timeout=12, allow_redirects=True, headers=rh)
                        if r2.status_code == 200:
                            ctype = r2.headers.get('Content-Type','')
                            # skip obvious HTML warning pages
                            body = r2.text or ''
                            if 'text/html' in ctype and ('警告' in body or 'Warning' in body):
                                continue
                            size = int(r2.headers.get('Content-Length') or 0) or None
                            found.append({"name": fname, "size": size, "type": None})
                            continue
                    except Exception:
                        pass

                # fallback: try GET directly with probe headers
                try:
                    g = requests.get(url, stream=True, timeout=12, headers=probe_headers)
                    if g.status_code == 200:
                        ctype = g.headers.get('Content-Type','')
                        body = None
                        try:
                            body = g.text
                        except Exception:
                            body = None
                        if 'text/html' in (g.headers.get('Content-Type','')) and body and ('警告' in body or 'Warning' in body):
                            # mirror returned a warning page, skip
                            continue
                        size = int(g.headers.get('Content-Length') or 0) or None
                        found.append({"name": fname, "size": size, "type": None})
                except Exception:
                    pass
            except Exception:
                pass
        return found
    except Exception:
        return []


def get_model_metadata(repo_id: str, api_base: Optional[str] = None) -> Dict:
    """Fetch model metadata / model card info from the API.

    Tries {base}/models/{repo_id} which typically contains model card info.
    Returns a dict with keys like description, modelId, pipeline_tag, tags, etc.
    """
    try:
        base = api_base.rstrip('/') if api_base else HF_API_BASE
        r = requests.get(f"{base}/models/{repo_id}", timeout=15)
        r.raise_for_status()
        return r.json() or {}
    except Exception:
        return {}


def get_model_readme(repo_id: str, api_base: Optional[str] = None) -> str:
    """Attempt to fetch a model README as text.

    Order of attempts:
      1. {api_base}/models/{repo_id}/readme
      2. model metadata description
      3. several resolve/raw paths on the api/mirror base (HEAD -> follow Location -> GET)
      4. official huggingface.co raw paths
    """
    base = api_base.rstrip('/') if api_base else HF_API_BASE
    # include a fuller browser-like User-Agent and repo-specific Referer/Origin to improve mirror behavior
    repo_page = f"https://huggingface.co/{repo_id}"
    repo_referer = f"https://huggingface.co/{repo_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/markdown, text/plain, */*',
        'Referer': repo_referer,
        'Origin': 'https://huggingface.co',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        # additional browser-like headers to mimic real browser requests
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        # simulate a basic cookie (adjust if real cookies are available)
        'Cookie': 'session_id=abc123; user_pref=1'
    }

    # 1) try explicit readme endpoint
    try:
        r = requests.get(f"{base}/models/{repo_id}/readme", timeout=12, headers=headers)
        if r.status_code == 200 and r.text:
            return r.text
    except Exception:
        pass

    # 2) try metadata description
    try:
        meta = get_model_metadata(repo_id, api_base=api_base)
        if meta and meta.get('description'):
            return meta.get('description')
    except Exception:
        pass

    # 3) probe various raw/resolve paths on the mirror/base
    raw_base = 'https://huggingface.co'
    if api_base and isinstance(api_base, str) and api_base.startswith('http'):
        raw_base = api_base.rstrip('/')
        if raw_base.endswith('/api'):
            raw_base = raw_base[:-4]

    candidate_paths = [
        f"{raw_base}/{repo_id}/resolve/main/README.md",
        f"{raw_base}/{repo_id}/resolve/main/README",
        f"{raw_base}/{repo_id}/raw/main/README.md",
        f"{raw_base}/{repo_id}/raw/master/README.md",
        f"{raw_base}/{repo_id}/raw/main/README",
        f"{raw_base}/{repo_id}/raw/master/README",
    ]

    for url in candidate_paths:
        try:
            # HEAD first to detect redirect Location
            try:
                h = requests.head(url, timeout=8, allow_redirects=False, headers=headers)
            except Exception:
                h = None
            loc = h.headers.get('Location') if h is not None else None
            if loc:
                # update Referer to the redirect target for better mirror behavior
                updated_headers = headers.copy()
                updated_headers['Referer'] = loc
                try:
                    # follow the redirect with updated headers
                    r2 = requests.get(loc, timeout=12, allow_redirects=True, headers=updated_headers)
                    if r2.status_code == 200 and r2.text:
                        ctype = r2.headers.get('Content-Type','')
                        body = r2.text or ''
                        # detect mirror warning HTML and save to temp for inspection
                        if 'text/html' in ctype and ('警告' in body or 'Warning' in body):
                            try:
                                out_dir = Path('temp') / 'hf_raw_responses'
                                out_dir.mkdir(parents=True, exist_ok=True)
                                fname = repo_id.replace('/','_') + '_warning_loc.html'
                                with (out_dir / fname).open('w', encoding='utf-8') as fw:
                                    fw.write(body)
                            except Exception:
                                pass
                            # skip this candidate
                        else:
                            return r2.text
                except Exception:
                    pass

            # fallback: direct GET with original headers
            try:
                r = requests.get(url, timeout=12, allow_redirects=True, headers=headers)
                if r.status_code == 200 and r.text:
                    ctype = r.headers.get('Content-Type','')
                    body = r.text or ''
                    if 'text/html' in ctype and ('警告' in body or 'Warning' in body):
                        # save raw HTML for user inspection and do not return as README
                        try:
                            out_dir = Path('temp') / 'hf_raw_responses'
                            out_dir.mkdir(parents=True, exist_ok=True)
                            fname = repo_id.replace('/','_') + '_warning.html'
                            with (out_dir / fname).open('w', encoding='utf-8') as fw:
                                fw.write(body)
                        except Exception:
                            pass
                        # skip this candidate and continue
                    else:
                        # also save a copy of the successful readme (trim filename)
                        try:
                            out_dir = Path('temp') / 'hf_raw_responses'
                            out_dir.mkdir(parents=True, exist_ok=True)
                            safe_name = repo_id.replace('/','_') + '_readme.txt'
                            with (out_dir / safe_name).open('w', encoding='utf-8') as fw:
                                fw.write(body)
                        except Exception:
                            pass
                        return r.text
            except Exception:
                pass
        except Exception:
            pass
        except Exception:
            pass

    # 4) final fallback: try official huggingface.co raw paths directly
    try:
        hf_raw_base = 'https://huggingface.co'
        raw_paths = [
            f"{hf_raw_base}/{repo_id}/raw/main/README.md",
            f"{hf_raw_base}/{repo_id}/raw/master/README.md",
            f"{hf_raw_base}/{repo_id}/raw/main/README",
            f"{hf_raw_base}/{repo_id}/raw/master/README",
        ]
        for url in raw_paths:
            try:
                r = requests.get(url, timeout=12, allow_redirects=True, headers=headers)
                if r.status_code == 200 and r.text:
                    ctype = r.headers.get('Content-Type','')
                    body = r.text or ''
                    if 'text/html' in ctype and ('警告' in body or 'Warning' in body):
                        try:
                            out_dir = Path('temp') / 'hf_raw_responses'
                            out_dir.mkdir(parents=True, exist_ok=True)
                            fname = repo_id.replace('/','_') + '_warning_official.html'
                            with (out_dir / fname).open('w', encoding='utf-8') as fw:
                                fw.write(body)
                        except Exception:
                            pass
                        continue
                    try:
                        out_dir = Path('temp') / 'hf_raw_responses'
                        out_dir.mkdir(parents=True, exist_ok=True)
                        safe_name = repo_id.replace('/','_') + '_readme.txt'
                        with (out_dir / safe_name).open('w', encoding='utf-8') as fw:
                            fw.write(body)
                    except Exception:
                        pass
                    return r.text
            except Exception:
                pass
    except Exception:
        pass

    return ''


def _construct_download_url(repo_id: str, filename: str, mirror_choice: str = "auto") -> str:
    # mirror_choice may be 'auto' or a full base url like 'https://hf-mirror.com/'
    base = "https://huggingface.co"
    if mirror_choice and isinstance(mirror_choice, str) and mirror_choice.startswith("http"):
        base = mirror_choice.rstrip('/')
    # standard resolve URL
    return f"{base}/{repo_id}/resolve/main/{filename}"


def download_from_hf(repo_id: str, filename: str, dest_dir: Path, mirror_choice: str = "auto", callback=None, stop_event=None) -> Optional[Path]:
    try:
        url = _construct_download_url(repo_id, filename, mirror_choice)
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get('Content-Length', 0) or 0)
            with dest_path.open('wb') as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    try:
                        if stop_event and stop_event.is_set():
                            if callback:
                                try:
                                    callback('cancelled', -1)
                                except:
                                    pass
                            return None
                    except:
                        pass
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total and callback:
                            try:
                                pct = int(downloaded * 100 // total)
                                callback('downloading', pct)
                            except:
                                pass
        if callback:
            try:
                callback('completed', 100)
            except:
                pass
        return dest_path
    except Exception as e:
        if callback:
            try:
                callback('error', -1)
            except:
                pass
        return None
