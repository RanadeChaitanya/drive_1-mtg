import json, sys
from score import *
S = {i['qid']: i for i in json.load(open('sample_next.json', encoding='utf-8'))}; F = json.load(open('gemma4_fixed.json', encoding='utf-8'))
for q in sys.argv[1:]:
    q = 'CET_PCB_2024_P01_' + q; t = S[q]['truth']; f = F[q]
    print('##', q[-8:]); print(' OCR :', repr((S[q]['ocr']['stem'] or '')[:120]), {k: str(v)[:30] for k, v in S[q]['ocr']['options'].items()})
    print(' GEMMA stem:', repr(f['stem_latex'][:140])); print(' TRUTH stem:', repr(t['stem'][:140]))
    for k in 'ABCD':
        a, b = f['options'].get(k, ''), str(t['options'].get(k, ''))
        if sim(a, b) < .95: print(f' opt {k} GEMMA {a[:60]!r} | TRUTH {b[:60]!r} | OCR {str(S[q]["ocr"]["options"].get(k,""))[:50]!r}')
