"""python eval_cluster.py <pdf> <questions.json> <out_dir> <ref_boxes.json> <accepted_ref.json> [--save]   crops by cluster_pics + score vs Sonnet-accepted reference boxes"""
import collections, json, sys
from pathlib import Path
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cluster_pics

pdf, qj, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
ref = {b["qid"]: b for b in json.load(open(sys.argv[4]))}; acc = json.load(open(sys.argv[5])); save = "--save" in sys.argv
doc = fitz.open(pdf); Q = json.load(open(qj, encoding="utf-8"))["questions"]; PAD = 3
TEXTY = lambda t: sum(w.isalpha() and len(w) >= 3 and w[1:].islower() for w in t.split()) >= 1 and len(t) > 6


def crop(pno, box, name):
    pg = fitz.open(pdf)[pno]; r = (fitz.Rect(box) + (-PAD, -PAD, PAD, PAD)) & pg.rect
    for b in pg.get_text("dict", clip=r)["blocks"]:
        if b["type"] == 0:
            for l in b["lines"]:
                t = " ".join(s["text"] for s in l["spans"])
                if (sum(w.isalpha() and len(w) >= 3 and w[1:].islower() for w in t.split()) >= 3 or len(t) > 45) and not (fitz.Rect(box) + (2, 2, -2, -2)).contains(fitz.Rect(l["bbox"])):
                    pg.add_redact_annot(fitz.Rect(l["bbox"]), fill=(1, 1, 1))
    pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    pm = pg.get_pixmap(dpi=200, clip=r); a = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w, pm.n)[:, :, :3].min(axis=2) < 140
    if save: pm.save(out / name)
    return bool(a[0].any() or a[-1].any() or a[:, 0].any() or a[:, -1].any())


cat = collections.Counter(); ex = collections.defaultdict(list); tot = clip = 0; extra = 0
for q in Q:
    if q["qid"] not in ref: continue
    pg = q["page"]; qs = [v for v in Q if v["page"] == pg and v["col"] == q["col"] and v["y0"] > q["y0"]]; H = doc[pg - 1].rect.height; W = doc[pg - 1].rect.width
    y_hi = min(v["y0"] for v in qs) if qs else H - 24; xr = (30, W / 2 + 40) if q["col"] == 0 else (W / 2 - 4, W - 6)
    pic = cluster_pics.pictures2(doc[pg - 1], q, q["y0"] - 2, y_hi, xr)
    got = {f"fig{i + 1}": b for i, b in enumerate(pic["stem"])}; got.update(pic["opts"])
    for k, b in got.items(): tot += 1; clip += crop(pg - 1, b, f"{q['qid']}_{k}.png")
    rb = ref[q["qid"]]; refs = {f"fig{i + 1}": b for i, b in enumerate(rb.get("stem_figures") or [])}; refs.update({L: b for L, b in (rb.get("options") or {}).items() if b})
    extra += len(set(got) - set(refs))
    for k in acc.get(q["qid"], []):
        if k not in refs: continue
        R = fitz.Rect(refs[k]); g = got.get(k)
        if g is None: c = "none"
        else:
            i = (g & R).get_area(); cov, pur = i / R.get_area(), i / max(g.get_area(), 1)
            c = "match" if cov >= .9 and pur >= .8 else "too big" if cov >= .9 else "too small" if pur >= .8 else "different"
        cat[c] += 1; ex[c].append((q["qid"][-9:], k))
n = sum(cat.values())
print(f"vs {n} Sonnet-accepted refs: " + ", ".join(f"{c} {v}" for c, v in cat.most_common()), f"| match {100 * cat['match'] / n:.1f}% | crops {tot}, border-ink {clip}, extra keys {extra}")
print({c: v[:5] for c, v in ex.items() if c != "match"})
