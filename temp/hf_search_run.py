#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Temp runner: call app.hf_browser.search_models with explicit hf mirror api_base and print results.
"""
import logging
import sys
import os
# ensure project root is on path
proj = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj not in sys.path:
    sys.path.insert(0, proj)
# enable debug logs for urllib3
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('urllib3').setLevel(logging.DEBUG)

try:
    from app import hf_browser
except Exception as e:
    logging.exception('Failed to import app.hf_browser')
    raise

API_BASE = 'https://hf-mirror.com/api'
query = 'yolo'
try:
    results = hf_browser.search_models(query, limit=10, api_base=API_BASE)
    print(f"SEARCH query='{query}' api_base='{API_BASE}' -> {len(results)} results")
    for i, r in enumerate(results[:10]):
        mid = r.get('modelId') if isinstance(r, dict) else str(r)
        tag = r.get('pipeline_tag') or r.get('task') if isinstance(r, dict) else ''
        print(f"{i+1}. {mid}  {tag}")
except Exception as e:
    logging.exception('Search failed')
    raise
