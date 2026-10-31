"""Haiku text-fix worklists: every question whose extraction is doubtful (not 4 options, NO_KEY, odd flags, leftover symbols) with a rendered region of the print.
python text_fix_prep.py <pdf> <questions.json> <out_dir> [batch_size]    writes region PNGs + in_N.json
Doubtful = flags OPTION_COUNT_*/NO_KEY/KEY_NOT_LETTER, or an MCQ whose options are not exactly 4, or non-ASCII leftovers in stem/options."""
import json, re, sys
from pathlib import Path
import fitz

pdf, qj, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); size = int(sys.argv[4]) if len(sys.argv) > 4 else 25; out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf); Q = json.load(open(qj, encoding="utf-8"))["questions"]
ODD = re.compile(r"[ -ÿ←-⋿](?<![°±×÷→])")
def doubtful(q):
    t = q["stem"] + " ".join(q["options"].values())
    return any(f.startswith("OPTION_COUNT") or f in ("NO_KEY", "KEY_NOT_LETTER") for f in q["flags"]) or (q["options"] and len(q["options"]) != 4) or bool(ODD.search(t))
items = []
for q in Q:
    if not doubtful(q): continue
    page = doc[q["page"] - 1]; H, W = page.rect.height, page.rect.width
    nxt = [v["y0"] for v in Q if v["page"] == q["page"] and v["col"] == q["col"] and v["y0"] > q["y0"]]
    x0, x1 = (30, W / 2 + 40) if q["col"] == 0 else (W / 2 - 4, W - 6)
    reg = fitz.Rect(x0, max(q["y0"] - 4, 60), x1, min((min(nxt) + 2) if nxt else H - 24, H))
    p = out / f"{q['qid']}.png"; page.get_pixmap(dpi=130, clip=reg).save(p)
    items.append(dict(qid=q["qid"], number=q["number"], region=str(p).replace("\\", "/"), stem=q["stem"], options=q["options"], key=q.get("correct_option") or q.get("answer")))
n = (len(items) + size - 1) // size
for i in range(n): json.dump(items[i::n], open(out / f"in_{i}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(items), "doubtful questions in", n, "batches")
