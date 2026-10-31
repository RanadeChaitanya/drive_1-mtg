"""Pictures with NO model: figs2 geometry boxes + padding + white-out of question-text spans + code judge (ink on the crop border = clipped).
python code_pics.py <pdf> <questions.json> <out_dir> <ref_boxes.json> <accepted_ref.json>
ref_boxes: boxes from the model route; accepted_ref: {qid: [image keys the Sonnet audit accepted]} -> IoU>=0.8 against them is the proxy score."""
import json, re, sys
from pathlib import Path
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
import figs2

pdf, qj, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
ref = {b["qid"]: b for b in json.load(open(sys.argv[4]))}; acc = json.load(open(sys.argv[5]))
doc = fitz.open(pdf); Q = json.load(open(qj, encoding="utf-8"))["questions"]; PAD = 3


def texty(t):
    ws = t.split(); return sum(w.isalpha() and len(w) >= 3 and w[1:].islower() for w in ws) >= 1 and len(t) > 6


def render(page, box):
    """grow each side that still has ink on the border (2 pt steps, max 8) after whiting out question-text spans"""
    box = fitz.Rect(box); r = (box + (-PAD, -PAD, PAD, PAD)) & page.rect
    for _ in range(9):
        pm = None
        pg = fitz.open(pdf)[page.number]
        for sp in [s for b in pg.get_text("dict", clip=r)["blocks"] if b["type"] == 0 for l in b["lines"] for s in l["spans"]]:
            if texty(sp["text"]): pg.add_redact_annot(fitz.Rect(sp["bbox"]), fill=(1, 1, 1))
        pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        pm = pg.get_pixmap(dpi=200, clip=r); a = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w, pm.n)[:, :, :3].min(axis=2) < 140
        t, b_, l_, r_ = a[0].any(), a[-1].any(), a[:, 0].any(), a[:, -1].any()
        if not (t or b_ or l_ or r_): return pm, False, r
        r = fitz.Rect(r.x0 - 2 * l_, r.y0 - 2 * t, r.x1 + 2 * r_, r.y1 + 2 * b_) & page.rect
    return pm, True, r


def iou(a, b):
    a, b = fitz.Rect(a), fitz.Rect(b); i = (a & b).get_area(); u = a.get_area() + b.get_area() - i
    return i / u if u > 0 else 0


got = {}; tot = ok = border_n = 0; refhit = refn = 0
for q in Q:
    if q["qid"] not in ref: continue
    pg = q["page"]; qs = [v for v in Q if v["page"] == pg]; H = doc[pg - 1].rect.height
    nxt = [v["y0"] for v in qs if v["col"] == q["col"] and v["y0"] > q["y0"]]; oth = [v["y0"] for v in qs if v["col"] != q["col"]]
    cont = min(oth) if (q["col"] == 0 and not nxt and oth) else None
    pic = figs2.pictures(doc[pg - 1], q["col"], q["y0"] - 30, (min(nxt) + 30) if nxt else H - 24, cont, lo=q["y0"] - 8, hi=(min(nxt) - 8) if nxt else H)
    items = {f"fig{i + 1}": o for i, o in enumerate(pic["stem"])}; items.update({L: c for L, c in zip("ABCD", pic["opts"] or []) if c is not None})
    rb = ref[q["qid"]]; refs = {f"fig{i + 1}": b for i, b in enumerate(rb.get("stem_figures") or [])}; refs.update({L: b for L, b in (rb.get("options") or {}).items() if b})
    for k, box in items.items():
        page = fitz.open(pdf)[pg - 1]; pm, border, r = render(page, box)
        pm.save(out / f"{q['qid']}_{k}.png"); got[(q['qid'], k)] = r; tot += 1; border_n += border; ok += (not border)
    for k in acc.get(q["qid"], []):
        if k in refs:
            refn += 1; g = got.get((q['qid'], k)); refhit += bool(g and (g & fitz.Rect(refs[k])).get_area() / fitz.Rect(refs[k]).get_area() >= 0.9 and (g & fitz.Rect(refs[k])).get_area() / g.get_area() >= 0.8)
print(f"code pictures: {tot} crops, {ok} pass the border-ink check ({100 * ok / max(tot, 1):.1f}%); vs Sonnet-accepted reference boxes: {refhit}/{refn} match (covers >=90% of the reference, >=80% of the crop is the reference)")
import collections
cat = collections.Counter(); ex = {}
for q in Q:
    if q["qid"] not in ref: continue
    rb = ref[q["qid"]]; refs = {f"fig{i + 1}": b for i, b in enumerate(rb.get("stem_figures") or [])}; refs.update({L: b for L, b in (rb.get("options") or {}).items() if b})
    for k in acc.get(q["qid"], []):
        if k not in refs: continue
        g = got.get((q["qid"], k)); R = fitz.Rect(refs[k])
        if g is None: c = "no code box for key"
        else:
            cov = (g & R).get_area() / R.get_area(); pur = (g & R).get_area() / g.get_area()
            c = "match" if cov >= .9 and pur >= .8 else "code too big" if cov >= .9 else "code too small" if pur >= .8 else "different"
        cat[c] += 1; ex.setdefault(c, []).append((q["qid"][-9:], k))
print(cat); print({c: v[:4] for c, v in ex.items()})
