#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Temp test: fetch README for a repo using new get_model_readme API.
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
print('Fetching README...')
text = hf_browser.get_model_readme(repo, api_base=API)
print('len:', len(text))
print(text[:1000])
