from pathlib import Path
import sys
import os

# ensure project root is on sys.path so `import app` works when running this script
proj_root = Path(__file__).resolve().parents[1]
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

print('启动 HF 浏览器自动测试')
try:
    from app import hf_browser
except Exception as e:
    print('无法导入 app.hf_browser:', e)
    sys.exit(2)

q = 'Uno'
print(f"搜索: {q}")
res = hf_browser.search_models(q, limit=10)
print(f'找到 {len(res)} 个结果')
for i, r in enumerate(res[:10]):
    print(i, r.get('modelId') or r.get('id') or r.get('name'), '-', (r.get('pipeline_tag') or r.get('tags') or '') )

if not res:
    print('没有搜索结果，退出')
    sys.exit(0)

# 选取候选模型：优先包含 yolo 或 yolov 的 id，否则第一个
candidate = None
for r in res:
    mid = r.get('modelId') or r.get('id') or r.get('name') or ''
    if 'yolo' in mid.lower() or 'yolov' in mid.lower():
        candidate = mid
        break
if not candidate:
    candidate = res[0].get('modelId') or res[0].get('id') or res[0].get('name')

print('选择候选 repo:', candidate)
files = hf_browser.list_model_files(candidate, api_base=None)
print(f'列出 {len(files)} 文件')
for f in files[:50]:
    print(' -', f.get('name'), f.get('size'))

# 找权重文件
candidates = []
exts = ['.pt', '.pth', '.safetensors', '.bin', '.onnx']
for f in files:
    name = f.get('name','') or ''
    for e in exts:
        if name.lower().endswith(e):
            candidates.append(name)
            break

if not candidates:
    print('未找到明显的权重文件（.pt/.pth/.safetensors/.bin/.onnx），尝试寻找常见文件名...')
    # fallback common names
    commons = ['pytorch_model.bin','model.pt','best.pt','model.pth','model.onnx']
    for f in files:
        if f.get('name','') in commons:
            candidates.append(f.get('name'))

if not candidates:
    print('没有可下载的权重文件，退出')
    sys.exit(0)

print('权重候选:', candidates[:5])
# 下载第一个候选到 models_test
dest = Path('models_test')
from app.hf_browser import download_from_hf
fn = candidates[0]
print('开始下载', fn)
p = download_from_hf(candidate, fn, dest, mirror_choice='auto')
print('download_from_hf returned:', p)
if p:
    print('文件大小:', p.stat().st_size)

# 检查 torch
try:
    import torch
    print('torch 可用，版本', torch.__version__)
    if str(p).lower().endswith(('.pt', '.pth', '.bin')):
        try:
            obj = torch.load(str(p), map_location='cpu')
            print('torch.load 成功，类型:', type(obj))
        except Exception as e:
            print('torch.load 失败:', e)
except Exception:
    print('系统中没有安装 torch，无法在本地加载模型')

print('测试结束')
