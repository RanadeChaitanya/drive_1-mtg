"""S6 applier with the subagents' detector answers instead of the API call: the pipeline's own apply_errors (a change is applied only when `before` occurs exactly once; confidence < 0.6 is held)."""
import json, re, sys

sys.path.insert(0, 'D:/MSA/old_pipe_test/final-pipeline/claude_pipeline'); sys.argv = ['cet_run.py', 'none', '1']
import cet_run as C

OUT = C.OUT; ans = {}
for i in range(2):
    raw = open(OUT / f'agent_s6/out_{i}.json', encoding='utf-8').read()
    raw = re.sub(r'\\(?:["\\/]|u[0-9a-fA-F]{4})|\\', lambda m: m.group(0) if len(m.group(0)) > 1 else chr(92) * 2, raw)
    ans.update(json.loads(raw))
g = json.load(open(OUT / 'final/paper_01_v5.json', encoding='utf-8')); log = {}; tot = [0, 0, 0]
for q in g['questions']:
    d = ans.get(q['qid'])
    if d is None: continue
    applied, unapplied, held = C.apply_errors(q, d.get('errors', []))
    log[q['qid']] = dict(applied=applied, unapplied=unapplied, held=held, needs_human=d.get('needs_human', False), note=d.get('note', ''))
    q['edits'] = (q.get('edits') or []) + [dict(field=a['field'], type='repair_symbol', before=a['before'], after=a['after'], basis='claude detector: ' + a.get('kind', ''), evidence=[], risk='low') for a in applied]
    q['claude_checked'] = True
    if unapplied or held or d.get('needs_human'): q['verdict'] = 'needs_human'
    tot = [tot[0] + len(applied), tot[1] + len(unapplied), tot[2] + len(held)]
json.dump(g, open(OUT / 'final/paper_01_v6.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(log, open(OUT / 'checked/paper_01_claude.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('applied', tot[0], 'unapplied', tot[1], 'held (confidence < 0.6)', tot[2], '| needs_human', sum(q['verdict'] == 'needs_human' for q in g['questions']))
