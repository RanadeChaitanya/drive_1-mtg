import json, sys
from score import *
S = {i['qid']: i for i in json.load(open('sample_next.json', encoding='utf-8'))}; F = json.load(open('gemma3_fixed.json', encoding='utf-8'))
for tag in ('retest', 'new'):
    qs = [q for q in F if S[q]['tag'] == tag]
    if not qs: continue
    r = score(F, [S[q] for q in qs]); n = len(r)
    print(f'## {tag}: {n} done | fully matching {sum(v[2] for v in r.values())} | mean stem {sum(v[0] for v in r.values())/n:.3f} | mean options {sum(v[1] for v in r.values())/n:.3f}')
    for q in qs:
        if not r[q][2] or tag == 'retest': print('  ', q[-8:], r[q][:2], 'OK' if r[q][2] else 'DIFF', '| pic:', F[q]['why_picture'])
