#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Temp test: fetch model metadata and files for a sample repo using hf_browser new APIs.
"""
import logging, sys, os
proj = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj not in sys.path:
    sys.path.insert(0, proj)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('urllib3').setLevel(logging.DEBUG)

from app import hf_browser

repo = 'Ultralytics/YOLOv8'
API = 'https://hf-mirror.com/api'
print('Fetching metadata...')
meta = hf_browser.get_model_metadata(repo, api_base=API)
print('meta keys:', list(meta.keys())[:10])
print('description (snippet):', (meta.get('description') or '')[:200])
print('\nListing files...')
files = hf_browser.list_model_files(repo, api_base=API)
print('files count:', len(files))
for f in files[:20]:
    print('-', f)
