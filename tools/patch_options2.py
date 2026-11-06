"""Quick fix on the COPY only (pages 10-11 run): options from the PDF text layer where the text layer has all four; questions whose options are drawn keep the pipeline's crops.
python patch_options2.py -> out2/final/paper_01_v5.json"""
import json, re
from pathlib import Path
import fitz

OUT = Path('D:/MSA/old_pipe_test/out3'); PAGES = (98,)
d = json.load(open(OUT / 'checked/paper_01.json', encoding='utf-8'))
doc = fitz.open('D:/Copy of CHEMISTRY 2020.pdf')
blocks = {}
for pg in PAGES:
    lines = [l.strip() for l in doc[pg - 1].get_text().splitlines() if l.strip()]
    lines = [l for l in lines if not re.match(r'(Chemistry|[A-Z][A-Za-z ,]+ of Chemistry|Some Basic Concepts of Chemistry|\[\d+\]|Article Deleted.*)$', l)]
    cur = None
    for l in lines:
        m = re.match(r'^\((\d{1,3})\)\s*(.*)$', l)
        if m: cur = (pg, int(m.group(1))); blocks[cur] = [m.group(2)] if m.group(2) else []
        elif cur is not None: blocks[cur].append(l)


def fix(t):
    t = t.replace('\uf0b4', ' \u00d7 ').replace('\uf0b7', '')
    t = re.sub(r'10\s*[\u2013-](\d+)', lambda m: '10^{-' + m.group(1) + '}', t)
    return re.sub(r'\s+', ' ', t).strip()


def split_opts(ls):
    opts, key = {}, None
    for l in ls:
        m = re.match(r'^([ABCD])(?:\s+(.*))?$', l)
        if m and (key is None or ord(m.group(1)) == ord(key) + 1): key = m.group(1); opts[key] = [m.group(2)] if m.group(2) else []
        elif key: opts[key].append(l)
    return {k: fix(' '.join(v)) for k, v in opts.items()}


n = drawn = 0
for q in d['questions']:
    ls = blocks.get((int(q['page']), int(re.sub(r'\D', '', str(q['number'])) or 0)))
    o = split_opts(ls) if ls else {}
    if len(o) == 4 and all(o.values()):
        q['options'] = o; n += 1
        q['flags'] = [f for f in q.get('flags', []) if f.get('code') != 'OPTION_EMPTY']
        q['reasons'] = [r for r in q.get('reasons', []) if not (isinstance(r, dict) and r.get('code') == 'OPTION_EMPTY')]
        q['figures'] = {k: ([] if k in 'ABCD' else v) for k, v in q['figures'].items()}
        q['edits'] = (q.get('edits') or []) + [{'type': 'text_layer_options', 'field': 'options'}]
    else: drawn += 1
(OUT / 'final').mkdir(exist_ok=True)
json.dump(d, open(OUT / 'final/paper_01_v5.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(n, 'questions got text options;', drawn, 'keep the pipeline crops (drawn options or no text)', 'of', len(d['questions']))
