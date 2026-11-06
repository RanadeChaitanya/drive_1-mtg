import json, re, difflib, sys
BS = chr(92)
def norm(t):
    t = str(t).replace(BS + BS, BS).replace(BS + BS, BS)
    t = re.sub(re.escape(BS) + r'(mathrm|text|left|right|quad|qquad|displaystyle|mathbf)', '', t)
    t = re.sub(re.escape(BS) + r'[a-zA-Z]+', lambda m: {BS + 'times': 'x', BS + 'Delta': 'delta'}.get(m[0], ''), t.lower().replace('$', ''))
    return re.sub('[^0-9a-zͰ-Ͽ]', '', t)
def sim(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()
def opts(g):
    o = g.get('options') or {}
    return dict(zip('ABCD', o)) if isinstance(o, list) else (o if isinstance(o, dict) else {})
def score(fix, S):
    """fix: {qid:{stem_latex,options}} -> {qid:(stem_sim, mean option sim, ok)}"""
    r = {}
    for it in S:
        g = fix.get(it['qid'])
        if not g: continue
        t = it['truth']; o = opts(g)
        s1 = sim(g.get('stem_latex', ''), t['stem']); s2 = sum(sim(o.get(k, ''), t['options'].get(k, '')) for k in 'ABCD') / 4
        r[it['qid']] = (round(s1, 3), round(s2, 3), s1 >= .95 and all(sim(o.get(k, ''), t['options'].get(k, '')) >= .95 for k in 'ABCD'))
    return r
if __name__ == '__main__':
    S = json.load(open('sample50.json', encoding='utf-8')); G = json.load(open('gemma_snap.json', encoding='utf-8'))
    fix = {q: g for q, g in G.items() if 'err' not in g}; r = score(fix, S); E = json.load(open('esc.json', encoding='utf-8'))
    n = len(r); print(n, 'scored; Gemma-only fully correct (all fields >=0.95):', sum(v[2] for v in r.values()), '| mean stem sim', round(sum(v[0] for v in r.values()) / n, 3), '| mean option sim', round(sum(v[1] for v in r.values()) / n, 3))
    for flag in ('picture present', 'fewer than 4', 'disagrees', 'unsure'):
        fl = [q for q in r if any(flag in w for w in E.get(q, []))]; ok = sum(r[q][2] for q in fl)
        print(f'flag "{flag}": {len(fl)} flagged, {ok} of them actually correct')
    un = [q for q in r if not E.get(q)]; print('unflagged:', len(un), sum(r[q][2] for q in un), 'correct')
