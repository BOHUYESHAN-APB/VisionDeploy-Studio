"""
Scan temp/hf_raw_responses for HTML files, extract basic metadata (title, presence of warning keywords), and write a summary to analysis.txt.
"""
from pathlib import Path
def analyze_dir(root: Path):
    out_lines = []
    files = list(root.glob('*.html'))
    out_lines.append(f"Found {len(files)} HTML files in {root}")
    for p in files:
        out_lines.append(f"--- {p.name} ---")
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
            # try a lightweight title extraction
            title = ''
            try:
                low = txt.lower()
                tstart = low.find('<title>')
                tend = low.find('</title>')
                if tstart != -1 and tend != -1 and tend > tstart:
                    title = txt[tstart+7:tend].strip()
            except Exception:
                title = ''
            # collapse text roughly by stripping tags
            try:
                import re
                body = re.sub('<[^<]+?>', ' ', txt)
                body = ' '.join(body.split())
            except Exception:
                body = txt[:2000]
            has_warning = any(k in body for k in ('警告', 'Warning', 'Access Denied', '403', '404', 'captcha'))
            out_lines.append(f"Title: {title}")
            out_lines.append(f"Contains warning-like text: {has_warning}")
            out_lines.append(f"Excerpt: {body[:500].replace('\n', ' ')}")
        except Exception as e:
            out_lines.append(f"parse error: {e}")
    return '\n'.join(out_lines)

if __name__ == '__main__':
    root = Path('temp') / 'hf_raw_responses'
    out = Path('temp') / 'hf_raw_responses' / 'analysis.txt'
    root.mkdir(parents=True, exist_ok=True)
    try:
        report = analyze_dir(root)
    except Exception as e:
        report = f"Error analyzing: {e}"
    out.write_text(report, encoding='utf-8')
    print(report)
