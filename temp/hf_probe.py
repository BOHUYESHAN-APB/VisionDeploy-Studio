import logging
import sys
from pathlib import Path
# ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app import hf_browser

logging.basicConfig(level=logging.DEBUG)

queries = ['yolo', 'CNN']

print('Using HF official API base:')
for q in queries:
    try:
        res = hf_browser.search_models(q, limit=5, api_base=None)
        print(q, '->', len(res))
        if res:
            print(' sample:', res[0])
    except Exception as e:
        print('error', e)

print('\nUsing mirror api base: https://hf-mirror.com/api')
for q in queries:
    try:
        res = hf_browser.search_models(q, limit=5, api_base='https://hf-mirror.com/api')
        print(q, '->', len(res))
        if res:
            print(' sample:', res[0])
    except Exception as e:
        print('error', e)
