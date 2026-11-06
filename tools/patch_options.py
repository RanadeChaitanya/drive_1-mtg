"""Quick fix on the COPY only: fill each question's options from the PDF text layer (this book has one) instead of OCR-box crops.
python patch_options.py  -> out/final/paper_01_v5.json (newest stage file, picked up by cet_run reconstruct)"""
import json, re
from pathlib import Path
import fitz

OUT = Path('D:/MSA/old_pipe_test/out2'); PAGES = (10, 11)
d = json.load(open(OUT / 'checked/paper_01.json', encoding='utf-8'))
lines = [l.strip() for l in fitz.open('D:/Copy of CHEMISTRY 2020.pdf')[PAGE - 1].get_text().splitlines() if l.strip()]
lines = [l for l in lines if not re.match(r'(Chemistry|Some Basic Concepts of Chemistry|\[\d+\]|Article Deleted.*)$', l)]
blocks, cur = {}, None
for l in lines:
    m = re.match(r'^\((\d{1,3})\)\s*(.*)$', l)
    if m: cur = int(m.group(1)); blocks[cur] = [m.group(2)] if m.group(2) else []
    elif cur is not None: blocks[cur].append(l)


def fix(t):
    t = t.replace('', ' × ').replace('', '')
    t = re.sub(r'10\s*[–-](\d+)', lambda m: '10^{-' + m.group(1) + '}', t)
    return re.sub(r'\s+', ' ', t).strip()


def split_opts(ls):
    opts, key = {}, None
    for l in ls:
        m = re.match(r'^([ABCD])(?:\s+(.*))?$', l)
        if m and (key is None or ord(m.group(1)) == ord(key) + 1): key = m.group(1); opts[key] = [m.group(2)] if m.group(2) else []
        elif key: opts[key].append(l)
    return {k: fix(' '.join(v)) for k, v in opts.items()}


n = 0
for q in d['questions']:
    ls = blocks.get(int(q['number']))
    if not ls: continue
    o = split_opts(ls)
    if len(o) == 4 and all(o.values()):
        q['options'] = o; n += 1
        q['flags'] = [f for f in q.get('flags', []) if f.get('code') != 'OPTION_EMPTY']
        q['reasons'] = [r for r in q.get('reasons', []) if not (isinstance(r, dict) and r.get('code') == 'OPTION_EMPTY')]
        q['figures'] = {k: ([] if k in 'ABCD' else v) for k, v in q['figures'].items()}
        q['edits'] = (q.get('edits') or []) + [{'type': 'text_layer_options', 'field': 'options'}]
(OUT / 'final').mkdir(exist_ok=True)
json.dump(d, open(OUT / 'final/paper_01_v5.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(n, 'of', len(d['questions']), 'questions got text options')
