"""Code post-processing of model boxes: white out text-layer spans that lie outside the figure box (question text, neighbours' labels), then grow a side
by 1.5 pt (max 4 steps) while ink still touches that side of the crop. Output is a judge worklist (same format as repair_tools crop) + flags.
python postproc.py <pdf> <questions.json> <boxes.json> <out_dir>"""
import json, re, sys
from pathlib import Path
import fitz
import numpy as np

pdf, qj, bj, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
Q = {q["qid"]: q for q in json.load(open(qj, encoding="utf-8"))["questions"]}; PAD = 2; STEP = 1.5


def render(pno, box, others):
    """others: boxes of the question's other pictures - never grown into"""
    box = fitz.Rect(box); r = (box + (-PAD, -PAD, PAD, PAD))
    for _ in range(5):
        pg = fitz.open(pdf)[pno]; r &= pg.rect
        for b in pg.get_text("dict", clip=r)["blocks"]:
            if b["type"] == 0:
                for l in b["lines"]:
                    for s in l["spans"]:
                        sb = fitz.Rect(s["bbox"])
                        t = s["text"].strip()
                        inside = (box + (-1.5, -1.5, 1.5, 1.5)).contains(sb)
                        marker = re.fullmatch(r"\(?[a-dA-D]?\)?|\(?[a-dA-D]\)?|[a-dA-D]\)|\d{1,3}\.", t) is not None and t not in ("",)
                        if t and not inside and (marker or (len(t) > 6 and any(w.isalpha() and len(w) >= 3 and w[1:].islower() for w in t.split()))): pg.add_redact_annot(sb, fill=(1, 1, 1))   # only real words are foreign text; short labels may be the figure's own
        pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        pm = pg.get_pixmap(dpi=200, clip=r); a = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w, pm.n)[:, :, :3].min(axis=2) < 140
        t, b_, l_, r_ = bool(a[0].any()), bool(a[-1].any()), bool(a[:, 0].any()), bool(a[:, -1].any())
        if not (t or b_ or l_ or r_): return pm, False
        n = fitz.Rect(r.x0 - STEP * l_, r.y0 - STEP * t, r.x1 + STEP * r_, r.y1 + STEP * b_)
        if any(n.intersects(o) and (n & o).get_area() > 4 for o in others): return pm, True
        r = n
    return pm, True


items, flags = [], {}
for b in json.load(open(bj)):
    q = Q[b["qid"]]; stems = b.get("stem_figures") or []; opts = {L: x for L, x in (b.get("options") or {}).items() if x}
    allb = [fitz.Rect(x) for x in stems] + [fitz.Rect(x) for x in opts.values()]
    item = dict(qid=b["qid"], number=q["number"], stem_figures=[], option_images={}); fl = {}
    for i, x in enumerate(stems):
        pm, bad = render(q["page"] - 1, x, [o for o in allb if o != fitz.Rect(x)]); p = out / f"{b['qid']}_fig{i + 1}.png"; pm.save(p); item["stem_figures"].append(str(p)); fl[f"fig{i + 1}"] = bad
    for L, x in opts.items():
        pm, bad = render(q["page"] - 1, x, [o for o in allb if o != fitz.Rect(x)]); p = out / f"{b['qid']}_opt{L}.png"; pm.save(p); item["option_images"][L] = str(p); fl[L] = bad
    items.append(item); flags[b["qid"]] = fl
json.dump(items, open(out / "judge_in.json", "w"), indent=0); json.dump(flags, open(out / "flags.json", "w"), indent=0)
print(len(items), "questions;", sum(len(f) for f in flags.values()), "images;", sum(sum(f.values()) for f in flags.values()), "still touch the border")
