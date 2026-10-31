"""Side-by-side scoring worklist: direct route vs old pipeline (DeepSeek stage 1 + Haiku stage 2 + OCR-box crops) on the same questions.
python build_score.py <cmp_dir> <final_figs_dir> <regions_dir>"""
import json, re, sys
from pathlib import Path

cmp_, figs, regs = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
raw = (cmp_ / "old_ds_stage2.json").read_bytes().decode("utf-8")
raw = re.sub(r'\\(?:["\\/]|u[0-9a-fA-F]{4})|\\', lambda m: m.group(0) if len(m.group(0)) > 1 else "\\\\", raw)   # \ce, \times are not JSON escapes
S2 = {r["qid"]: r for r in json.loads(raw)}
O = {r["qid"]: r for r in json.load(open(cmp_ / "old_all.json", encoding="utf-8"))}
D = {q["qid"]: q for q in json.load(open(cmp_ / "direct_all.json", encoding="utf-8"))["questions"]}
items = []
for qid in open(cmp_ / "ids.txt").read().split():
    d, o, s = D[qid], O[qid], S2.get(qid, {})
    items.append(dict(qid=qid, number=d["number"], region=f"{regs}/{qid}.png",
                      direct=dict(stem=d["stem"], options=d["options"], stem_images=[f"{figs}/{n}" for n in d["stem_images"]], option_images={L: f"{figs}/{n}" for L, n in d["option_images"].items()}),
                      old=dict(stem=s.get("stem", ""), options=s.get("options", {}), stem_images=[f"{cmp_.as_posix()}/oldfigs/{n}" for n in o["stem_images"]], option_images={L: f"{cmp_.as_posix()}/oldfigs/{n}" for L, n in o["option_images"].items()})))
json.dump(items, open(cmp_ / "score_in.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
(cmp_ / "SCORE_TASK.md").write_text("""# Scoring task
Input: score_in.json (same folder). For EACH item Read its `region` PNG (the question as printed) and every image listed under `direct` and `old`.
Two candidate outputs for the same question: `direct` and `old` (stem text, options text, stem_images, option_images). A picture option has empty/placeholder text and an image instead.
For EACH candidate decide strictly, as for publication:
- stem_ok: stem text matches the print (wording, numbers, formulas; no figure-label debris, no missing/extra words).
- options_ok: all four options present and correct (text options match; drawn options covered by complete, correct option_images; empty options when the print has options = NOT ok; numeric questions with no options = ok).
- pictures_ok: every picture the printed question needs is provided, complete (nothing clipped), no stray text/neighbour fragments; no picture needed and none provided = ok.
Output score_out.json (same folder), valid JSON (double every backslash): list of {qid, direct:{stem_ok,options_ok,pictures_ok,note}, old:{stem_ok,options_ok,pictures_ok,note}}. One entry per item; verify; reply with counts only.
""", encoding="utf-8")
print(len(items))
