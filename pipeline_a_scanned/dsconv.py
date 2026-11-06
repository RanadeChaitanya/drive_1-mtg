"""deepseek-ocr text -> {stem_latex, options} by code only (no model), then score scanned (v13 truth) and digital (Chemistry 2020 reference) SEPARATELY."""
import json, re, sys
from score import score
BS = chr(92)
def conv(t):
    t = re.sub(r'<table>.*?</table>', ' [figure] ', t, flags=re.S)
    t = re.sub(r'<sup>(.*?)</sup>', lambda m: '^{' + m[1] + '}', t); t = re.sub(r'<sub>(.*?)</sub>', lambda m: '_{' + m[1] + '}', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = re.sub(re.escape(BS + '(') + '(.*?)' + re.escape(BS + ')'), lambda m: '$' + m[1].strip() + '$', t, flags=re.S); t = re.sub(re.escape(BS + '[') + '(.*?)' + re.escape(BS + ']'), lambda m: '$' + m[1].strip() + '$', t, flags=re.S)
    t = re.sub(r'<\|[^|]*\|>', '', t).strip()
    t = re.sub(r'^(assistant|Chemistry|Physics|Biology|Mathematics)\s*\n', '', t.replace('**', '')).strip()
    t = re.sub(r'^\s*\(?\d{1,3}[.)]\s*', '', t)                            # question number
    m = re.search(r'\n\s*\(?\d{1,3}[.)]\s+[A-Z]', t[15:]); t = t[:15 + m.start()] if m else t   # neighbouring question
    m = re.search(r'\(?\b\d{1,3}[.)]\s*(?=[A-Z][a-z])', t[:70])                  # crumbs of the neighbouring question before this question's number
    if m and m.start() > 0: t = t[m.end():]
    pos = []
    for m in re.finditer(r'\(([A-D])\)\s*', t): pos.append((m.start(), m.end(), m[1]))
    if len({p[2] for p in pos}) < 4:
        pos = []; cur = 0
        for k in 'ABCD':
            m = re.compile(r'(?m)^\s*(?:-\s*)?%s(?:[.)]\s*|\s+)(?=\S)' % k).search(t, cur)
            if not m: break
            pos.append((m.start(), m.end(), k)); cur = m.end()
    seen = set(); pos = [p for p in pos if not (p[2] in seen or seen.add(p[2]))]
    stem = t[:pos[0][0]] if pos else t; o = {k: '' for k in 'ABCD'}
    for i, (st, en, k) in enumerate(pos): o[k] = ' '.join(t[en:(pos[i + 1][0] if i + 1 < len(pos) else len(t))].split())
    SUB = str.maketrans('₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789' * 2)
    o = {k: (v if '$' in v or not re.search('[₀-₉⁰-⁹]', v) else '$' + BS + 'ce{' + v.translate(SUB).replace(' ', '') + '}$') for k, v in o.items()}
    return dict(stem_latex=' '.join(stem.split()), options=o)
if __name__ == '__main__':
    D = json.load(open('dsocr_out.json', encoding='utf-8')); F = {q: conv(v['text']) for q, v in D.items()}
    json.dump(F, open('dsocr_fixed.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    S = [i for i in json.load(open('sample_next.json', encoding='utf-8'))]
    Fin = json.load(open('../final.json', encoding='utf-8'))
    def op(x): return eval(x) if isinstance(x, str) else x
    DIG = [dict(qid=q, truth=dict(stem=Fin[q]['stem_latex'], options=op(Fin[q]['options']))) for q in D if q.startswith('CHEM')]
    for name, items in (('SCANNED (CET, v13 truth)', S), ('DIGITAL (Chemistry 2020, text-layer reference)', DIG)):
        r = score(F, items); n = len(r)
        if n: print(f'{name}: {n} questions | fully matching {sum(v[2] for v in r.values())} | mean stem {sum(v[0] for v in r.values())/n:.3f} | mean options {sum(v[1] for v in r.values())/n:.3f}'); [print('  DIFF', q[-8:], r[q][:2]) for q in r if not r[q][2]]
