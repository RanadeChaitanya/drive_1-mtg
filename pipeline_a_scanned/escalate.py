"""Code decides which questions need Haiku (picture, unsure, missing/odd options, lint error, OCR disagreement). Writes esc.json + haiku inputs."""
import json, re, subprocess, difflib, sys
S = json.load(open('sample50.json', encoding='utf-8')); G = json.load(open('gemma_snap.json', encoding='utf-8'))
def norm(t): return re.sub(r'[^0-9a-z\u0370-\u03ff]', '', re.sub(r'\[a-zA-Z]+', lambda m: {'\times': 'x', '\Delta': 'delta'}.get(m[0], ''), str(t).lower().replace('$', '')))
def sim(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()
# lint via the vision-folder KaTeX linter (needs gen-style dict)
def _o(g):
    o = g.get('options') or {}
    return dict(zip('ABCD', o)) if isinstance(o, list) else (o if isinstance(o, dict) else {})
lint_in = {q: dict(stem_latex=str(g.get('stem_latex', '')), options={k: str(v) for k, v in _o(g).items()}) for q, g in G.items() if 'err' not in g}
json.dump(lint_in, open('lint_in.json', 'w', encoding='utf-8')); subprocess.run([sys.executable, '../lint.py', 'lint_in.json'], capture_output=True)
lint = json.load(open('lint.json', encoding='utf-8')) if __import__('os').path.exists('lint.json') else {}
esc, items = {}, []
S = [i for i in S if i['qid'] in G]
for it in S:
    q = it['qid']; g = G.get(q, {'err': 'missing'}); why = []
    if 'err' in g: why.append('gemma failed: ' + g['err'])
    else:
        opts = g.get('options') or {}
        if isinstance(opts, list): opts = dict(zip('ABCD', opts))
        if not isinstance(opts, dict): opts = {}
        g['options'] = opts
        if g.get('has_picture') or g.get('picture_options'): why.append('picture present (gemma)')
        if g.get('needs_review') and g.get('unsure'): why.append('gemma unsure: ' + str(g['unsure'])[:80])
        if not g.get('picture_options') and sum(bool(str(opts.get(k, '')).strip()) for k in 'ABCD') < 4: why.append('fewer than 4 options')
        if not str(g.get('stem_latex', '')).strip(): why.append('empty stem')
        if any(k.startswith(q + '|') for k in lint): why.append('KaTeX lint error')
        o = it['ocr']
        if o['stem']:
            s1 = sim(g.get('stem_latex', ''), o['stem']); s2 = sum(sim(opts.get(k, ''), o['options'].get(k, '')) for k in 'ABCD') / 4
            if s1 < 0.85 or s2 < 0.8: why.append(f'disagrees with existing OCR text (stem {s1:.2f}, options {s2:.2f})')
    esc[q] = why
    if why: items.append(dict(qid=q, png=it['png'], gemma_draft=g if 'err' not in g else None, ocr_text=it['ocr'], reasons=why))
json.dump(esc, open('esc.json', 'w', encoding='utf-8'), indent=1)
n = 5
for i in range(n): json.dump(items[i::n], open(f'h_in_{i}.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(len(S), 'questions;', len(items), 'to Haiku;', len(S) - len(items), 'Gemma-only')
