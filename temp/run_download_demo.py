# demo script: use app.hf_browser.download_repo to download common files from a HF repo
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import hf_browser

if __name__ == '__main__':
    repo = 'ultralytics/yolov5'  # example
    out = Path('temp') / 'models_test'
    print(f"Downloading repo {repo} into {out} (demo: common small files only)")
    p = hf_browser.download_repo(repo, out, api_base=None, mirror_choice='auto', callback=lambda m,pct: print(m, pct))
    print('Result folder:', p)
