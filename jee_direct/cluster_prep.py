"""Code proposes, a cheap model only ASSIGNS: numbered vector clusters are drawn on the page strip; the model says which cluster ids make each stem figure / option picture.
Crops are then the exact union of the chosen clusters (no coordinates read by eye, so no clipping), question text is whited out, a code check flags ink on the border.
python cluster_prep.py <pdf> <questions.json> <qids.json> <out_dir> [batch]   -> in_N.json (+ clusters), PNGs
python cluster_prep.py crop <pdf> <questions.json> <answers.json> <out_dir>       -> judge_in.json (crops), flags.json
answers: [{qid, stem:[[ids],...], options:{A:[ids]|null,...}}]"""
import json, sys
from pathlib import Path
import fitz
import numpy as np
from PIL import ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cluster_pics

PAD = 3


def regions(Q, q, H, W):
    nxt = [v["y0"] for v in Q if v["page"] == q["page"] and v["col"] == q["col"] and v["y0"] > q["y0"]]
    y0 = max(q["y0"] - 35, 60); y1 = min((min(nxt) + 12) if nxt else H - 20, H)
    x0, x1 = (30, W / 2 + 50) if q["col"] == 0 else (W / 2 - 10, W - 4)
    regs = [(x0, y0, x1, y1)]
    if q["col"] == 0 and not nxt:
        oth = [v["y0"] for v in Q if v["page"] == q["page"] and v["col"] == 1]
        if oth: regs.append((W / 2 - 10, 62, W - 4, min(oth) + 10))
    return regs


def mask_and_render(pdf, pno, box):
    """white out every text-layer span that is not inside the figure's own box (question text, neighbouring labels), keep the art"""
    pg = fitz.open(pdf)[pno]; box = fitz.Rect(box); r = (box + (-PAD, -PAD, PAD, PAD)) & pg.rect; inner = box + (-1.5, -1.5, 1.5, 1.5)
    for b in pg.get_text("dict", clip=r)["blocks"]:
        if b["type"] == 0:
            for l in b["lines"]:
                for s in l["spans"]:
                    sb = fitz.Rect(s["bbox"])
                    if s["text"].strip() and not inner.contains(sb): pg.add_redact_annot(sb & r if not inner.intersects(sb) else fitz.Rect(sb.x0, sb.y0, sb.x1, sb.y1) - (0, 0, 0, 0), fill=(1, 1, 1))
    pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    return pg.get_pixmap(dpi=200, clip=r)


if sys.argv[1] == "crop":
    _, _, pdf, qj, ans, out = sys.argv; out = Path(out); out.mkdir(parents=True, exist_ok=True)
    Q = {q["qid"]: q for q in json.load(open(qj, encoding="utf-8"))["questions"]}; pre = json.load(open(out / "clusters.json")); items = []; flags = {}
    for a in json.load(open(ans, encoding="utf-8")):
        q = Q[a["qid"]]; cl = pre[a["qid"]]; box = lambda ids: fitz.Rect(*[min(cl[str(i)][k] for i in ids) if k < 2 else max(cl[str(i)][k] for i in ids) for k in range(4)]) if ids else None
        item = dict(qid=a["qid"], number=q["number"], stem_figures=[], option_images={}); fl = {}
        for n, ids in enumerate(a.get("stem") or []):
            ids = [i for i in ids if str(i) in cl]
            if not ids: continue
            b = box(ids); pm = mask_and_render(pdf, q["page"] - 1, b); p = out / f"{a['qid']}_fig{n + 1}.png"; pm.save(p); item["stem_figures"].append(str(p))
            ar = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w, pm.n)[:, :, :3].min(axis=2) < 140; fl[f"fig{n + 1}"] = bool(ar[0].any() or ar[-1].any() or ar[:, 0].any() or ar[:, -1].any())
        ops = {L: [i for i in (ids or []) if str(i) in cl] for L, ids in (a.get("options") or {}).items()}
        shared = {}
        for L, ids in ops.items():
            if len(ids) == 1: shared.setdefault(ids[0], []).append(L)
        split = {}
        for cid, Ls in shared.items():
            if len(Ls) > 1:
                W = fitz.open(pdf)[q["page"] - 1].rect.width; reg = fitz.Rect(30, 60, W / 2 + 40, 800) if q["col"] == 0 else fitz.Rect(W / 2 - 4, 60, W - 6, 800)
                for L, r in cluster_pics.split_shared(fitz.open(pdf)[q["page"] - 1], fitz.Rect(*cl[str(cid)]), Ls, reg).items(): split[L] = r
        for L, ids in ops.items():
            if not ids: continue
            b = split[L] if L in split else box(ids); pm = mask_and_render(pdf, q["page"] - 1, b); p = out / f"{a['qid']}_opt{L}.png"; pm.save(p); item["option_images"][L] = str(p)
            ar = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w, pm.n)[:, :, :3].min(axis=2) < 140; fl[L] = bool(ar[0].any() or ar[-1].any() or ar[:, 0].any() or ar[:, -1].any())
        items.append(item); flags[a["qid"]] = fl
    json.dump(items, open(out / "judge_in.json", "w"), indent=0); json.dump(flags, open(out / "flags.json", "w"), indent=0)
    print(len(items), "questions cropped;", sum(len(f) for f in flags.values()), "images;", sum(sum(f.values()) for f in flags.values()), "with ink on the border")
    sys.exit()

pdf, qj, ids_f, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); size = int(sys.argv[5]) if len(sys.argv) > 5 else 20; out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf); Q = json.load(open(qj, encoding="utf-8"))["questions"]; M = {q["qid"]: q for q in Q}; items = []; allcl = {}
for qid in json.load(open(ids_f)):
    q = M[qid]; page = doc[q["page"] - 1]; H, W = page.rect.height, page.rect.width; regs = []; cl = {}; k = 0
    for ri, (a, b, c, d) in enumerate(regions(Q, q, H, W)):
        boxes, marks = cluster_pics.clusters(page, fitz.Rect(a, b, c, d))
        im = page.get_pixmap(dpi=144, clip=fitz.Rect(a, b, c, d)).pil_image().convert("RGB"); dr = ImageDraw.Draw(im); ids = {}
        for bx in boxes:
            k += 1; cl[str(k)] = [bx.x0, bx.y0, bx.x1, bx.y1]; ids[k] = 1
            X0, Y0, X1, Y1 = (bx.x0 - a) * 2, (bx.y0 - b) * 2, (bx.x1 - a) * 2, (bx.y1 - b) * 2
            dr.rectangle([X0, Y0, X1, Y1], outline=(220, 0, 0), width=1); dr.rectangle([X0, Y0, X0 + 7 * len(str(k)) + 4, Y0 + 12], fill=(255, 255, 200)); dr.text((X0 + 2, Y0 + 1), str(k), fill=(200, 0, 0))
        p = out / f"{qid}_{ri}.png"; im.save(p); regs.append(dict(png=str(p).replace("\\", "/"), region_pt=[a, b, c, d], cluster_ids=sorted(ids)))
    allcl[qid] = cl
    items.append(dict(qid=qid, number=q["number"], image_option_letters=[L for L, v in q["options"].items() if not v], regions=regs))
(out / "clusters.json").write_text(json.dumps(allcl), encoding="utf-8")
n = (len(items) + size - 1) // size
for i in range(n): json.dump(items[i::n], open(out / f"in_{i}.json", "w"), indent=0)
print(len(items), "questions,", sum(len(v) for v in allcl.values()), "clusters,", n, "batches")
