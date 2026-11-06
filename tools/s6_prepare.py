"""S6 without an API key: write the pipeline's own Haiku detector inputs (crop PNG + message + DETECT_RULES) for Claude Code subagents.
python s6_prepare.py -> out3/agent_s6/BRIEF.md, in_0.json, in_1.json (from the newest final stage file)"""
import base64, json, sys
from pathlib import Path

sys.path.insert(0, 'D:/MSA/old_pipe_test/final-pipeline/claude_pipeline'); sys.argv = ['cet_run.py', 'none', '1']
import cet_run as C

OUT = C.OUT; d = OUT / 'agent_s6'; d.mkdir(exist_ok=True)
g = json.load(open(OUT / 'final/paper_01_v5.json', encoding='utf-8')); items = []
for q in g['questions']:
    png, _ = C.crop_png(q)
    f = d / f"{q['qid']}.png"; f.write_bytes(base64.b64decode(png))
    msg = (f"Question {q['qid']} on page {q['page']} (locate it on the page image).\nCURRENT TEXT:\nSTEM: {q['stem']}\n" + "\n".join(f"({L}) {q['options'].get(L, '')}" for L in "ABCD") +
           "\nBook answer key: " + str(q['correct_option']) + "\nReasons it was sent to you:\n" + "\n".join(f"- {r['code']}: {r['detail']}" for r in q['reasons']))
    items.append(dict(qid=q['qid'], png=str(f).replace('\\', '/'), message=msg))
(d / 'BRIEF.md').write_text(C.DETECT_RULES + "\n\nTask: the input JSON lists questions; for EACH, Read its png and the `message`, then answer with the ONE JSON object described above. Output file (path given): a JSON object {qid: <that JSON object>} for every item; verify it parses; reply with counts only.\n", encoding='utf-8')
for i in range(2): json.dump(items[i::2], open(d / f'in_{i}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(items), 'questions ->', d)
