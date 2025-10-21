# hf workflow test: search, readme, list files, download single file, import to models_imported
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import hf_browser
from app import model_manager
import shutil

OUT_BASE = Path('temp') / 'models_downloads'
IMPORT_BASE = Path('models_imported')


def safe_print(*a, **k):
    print(*a, **k)


def run():
    query = 'Uno'
    safe_print('搜索模型:', query)
    hits = hf_browser.search_models(query, limit=10)
    if not hits:
        safe_print('未找到匹配模型（search_models 返回空）')
        return
    safe_print(f'找到 {len(hits)} 条结果，取第一条用于测试')
    first = hits[0]
    repo_id = first.get('id') or first.get('modelId') or first.get('repoId') or ''
    safe_print('选择模型 repo:', repo_id)

    safe_print('\n获取 README（尝试）')
    readme = hf_browser.get_model_readme(repo_id)
    if readme:
        out = Path('temp') / 'hf_readmes'
        out.mkdir(parents=True, exist_ok=True)
        p = out / (repo_id.replace('/', '_') + '_readme.txt')
        p.write_text(readme, encoding='utf-8')
        safe_print('README 已保存到', p)
    else:
        safe_print('未能获取 README（可能被镜像或不存在）')

    safe_print('\n列出仓库文件（尝试）')
    files = hf_browser.list_model_files(repo_id)
    if not files:
        safe_print('未获取到文件列表（list_model_files 返回空），尝试使用 download_repo 获取常见文件')
        repo_folder = hf_browser.download_repo(repo_id, OUT_BASE, mirror_choice='auto', callback=lambda m,p: safe_print(m,p))
        if repo_folder and repo_folder.exists():
            safe_print('download_repo 完成，查看文件夹:', repo_folder)
            for f in repo_folder.iterdir():
                safe_print(' -', f.name)
        else:
            safe_print('download_repo 未能获取任何文件')
        return

    # 如果拿到文件列表，找第一个非二进制常见文件（.md/.txt/.json）优先
    candidate = None
    for it in files:
        name = it.get('name') if isinstance(it, dict) else str(it)
        if name and any(name.endswith(ext) for ext in ('.md', '.txt', '.json', '.yaml', '.yml')):
            candidate = name
            break
    if not candidate and files:
        candidate = files[0].get('name') if isinstance(files[0], dict) else str(files[0])

    safe_print('\n选中文件进行下载（demo）:', candidate)
    if candidate:
        outdir = OUT_BASE / repo_id.replace('/', '_')
        outdir.mkdir(parents=True, exist_ok=True)
        p = hf_browser.download_from_hf(repo_id, candidate, outdir, mirror_choice='auto', callback=lambda m,pct: safe_print(m,pct))
        if p:
            safe_print('文件下载成功:', p)
            IMPORT_BASE.mkdir(parents=True, exist_ok=True)
            dst = IMPORT_BASE / p.name
            shutil.copy2(p, dst)
            safe_print('已模拟导入到:', dst)
        else:
            safe_print('文件下载失败或受限')


if __name__ == '__main__':
    run()
