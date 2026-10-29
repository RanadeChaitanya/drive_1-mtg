"""OCR route for the JEE book (the old pipeline's way): DeepSeek-OCR page text with per-mille boxes -> questions, text options,
stem figures and ONE IMAGE PER OPTION when the options are drawings. Code only; the LaTeX clean-up of stem/options is the model stage after this.
python ocr_route.py <pdf> <ocr_dir> <out.json> <figs_dir> <page> [<page> ...]      ocr_dir has page_NNN.txt and page_NNN.png (ocr_test.py)
Reuses claude_pipeline/cet_figures.py (split_box, grow) and cet_options.py (split_options)."""
import json, re, sys
from pathlib import Path
import fitz, numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))   # copies of the final-pipeline helpers; the original pipeline is not touched
from cet_figures import split_box, grow, _gaps  # noqa: E402
from cet_options import split_options  # noqa: E402

TAG = re.compile(r"^([a-z_]+)\[\[(\d+), (\d+), (\d+), (\d+)\]\]\s*$")


def blocks(txt):
    out, cur = [], None
    for line in txt.splitlines():
        m = TAG.match(line.strip())
        if m:
            cur = dict(kind=m.group(1), box=[int(v) for v in m.groups()[1:]], text=[]); out.append(cur)
        elif cur is not None:
            cur["text"].append(line)
    for b in out: b["text"] = "\n".join(b["text"]).strip()
    return out


def questions(bl, page):
    qs, cur = [], None
    for b in bl:
        if b["kind"] in ("image", "figure"):
            if cur:
                cur["boxes"].append(b["box"]); cur.setdefault("above", b["box"][1] if cur.get("text_bottom") is None else cur["text_bottom"])
            continue
        if b["kind"] in ("sub_title", "title") and not re.match(r"\d+\.", b["text"]): cur = None; continue
        parts = re.split(r"(?m)^\s*(?=\d{1,3}\.\s)", b["text"])
        for p in parts:
            m = re.match(r"(\d{1,3})\.\s", p)
            if m: cur = dict(number=int(m.group(1)), page=page, text=p.strip(), boxes=[], col=int(b["box"][0] > 480), y0=b["box"][1], text_bottom=b["box"][3]); qs.append(cur)
            elif cur and p.strip():
                cur["text"] += "\n" + p.strip()
                if not cur["boxes"]: cur["text_bottom"] = b["box"][3]
    for q in qs:                                                  # the next question in the same column bounds the options from below
        nxt = [o["y0"] for o in qs if o["col"] == q["col"] and o["y0"] > q["y0"]]
        q["below"] = min(nxt) if nxt else 960
    return qs


def row_segments(png, box):
    """stacked pictures inside one box: [(y0,y1)] runs of ink separated by blank rows (per-mille box)"""
    im = Image.open(png).convert("L"); W, H = im.size
    x0, y0, x1, y1 = [int(v) for v in (box[0] * W / 1000, box[1] * H / 1000, box[2] * W / 1000, box[3] * H / 1000)]
    a = np.array(im)[y0:y1, x0:x1] < 190
    rows = a.any(axis=1).astype(int); gaps = _gaps(rows, max(6, int(0.045 * a.shape[0])))
    edges = [0] + [(g[0] + g[1]) // 2 for g in gaps] + [a.shape[0]]
    return [[box[0], round((y0 + edges[k]) * 1000 / H), box[2], round((y0 + edges[k + 1]) * 1000 / H)] for k in range(len(edges) - 1)]


def option_cells(png, boxes):
    """the trailing picture boxes that split into exactly four option cells; the boxes before them are stem figures"""
    for k in range(1, len(boxes) + 1):
        tail = boxes[-k:]
        if k == 1:
            sp = split_box(png, tail[0])
            if sp: return boxes[:-1], [sp["cells"][L] for L in "ABCD"]
        cells = [c for b in tail for c in row_segments(png, b)]
        if len(cells) == 4: return boxes[:-k], cells
    return boxes, None


def upper_markers(t):
    """JEE prints (a)-(d); the old splitter expects (A)-(D). Only when all four appear in order, so a stray '(a)' in a stem is untouched."""
    t = re.sub(r"\\mathrm\{\(([a-d])\)\}", lambda m: "(" + m.group(1) + ")", t)
    pos = [m.start() for L in "abcd" for m in list(re.finditer(r"\(\s*" + L + r"\s*\)", t))[-1:]]
    return re.sub(r"\(\s*([a-d])\s*\)", lambda m: "(" + m.group(1).upper() + ")", t) if len(pos) == 4 and pos == sorted(pos) else t


def marker_cells(page, boxes, col=0, above=0, below=960):
    """One picture per option, cut from the rendered page, not from OCR boxes (which tile pictures arbitrarily).
    1. find the printed letters (a)-(d), in this column and, when the options run on, at the head of the next one; 2. render the option area, blank
    the letters and printed text-option lines; 3. grow the ink 2 pt so a picture and its labels (Br, NO2, C2H5, bond stubs) form ONE blob while
    neighbouring pictures stay apart; 4. each blob goes to the nearest letter on its left in its row.
    returns 'TEXT' (options are printed lines), None (letters not found / a picture missing) or four Rects (None for an option that is a text line)."""
    from scipy import ndimage
    r = page.rect; H = r.height; mid = r.width / 2
    xr = {0: (70, mid + 12), 1: (mid + 4, r.width - 12)}
    y_lo = max(above / 1000 * H, 0) + 1; y_hi = min(below / 1000 * H, H - 22) - 1
    rects = [fitz.Rect(b[0] / 1000 * r.width, b[1] / 1000 * H, b[2] / 1000 * r.width, b[3] / 1000 * H) for b in boxes]
    y_first = min(x.y0 for x in rects); oc = 1 - col
    other = [x for x in rects if (x.x0 + x.x1) / 2 > mid] if col == 0 else [x for x in rects if (x.x0 + x.x1) / 2 <= mid]
    y_oc = (70, max(x.y1 for x in other) + 10) if other else None   # head of the neighbouring column, where the options continue
    words = page.get_text("words")
    mk, side, prev_y = {}, {}, y_first - 8
    for L in "abcd":
        hits = [h for h in page.search_for(f"({L})", clip=fitz.Rect(xr[col][0] - 16, max(y_lo, y_first - 8), xr[col][1], y_hi)) if h.y0 >= prev_y - 2]
        c = col
        if not hits and y_oc:                                  # the rest of the options sit at the top of the next column
            hits = [h for h in page.search_for(f"({L})", clip=fitz.Rect(xr[oc][0] - 16, y_oc[0], xr[oc][1], y_oc[1])) if h.y0 >= (70 if not any(side[k] == oc for k in side) else prev_y - 2)]
            c = oc
        if not hits: return None
        mk[L] = hits[0]; side[L] = c; prev_y = hits[0].y0 - 2
    is_text = {L: any(abs(w[1] - mk[L].y0) < 3 and 0 <= w[0] - mk[L].x1 < 16 for w in words) for L in "abcd"}
    if sum(is_text.values()) >= 2: return "TEXT"
    owned = {L: [] for L in "abcd"}; sc = 2.0
    for c in sorted(set(side.values())):
        G = [L for L in "abcd" if side[L] == c]
        top = min(mk[L].y0 for L in G) - 62                    # a stem scheme further above than any picture can reach is not an option
        R = fitz.Rect(xr[c][0], max(top, y_lo if c == col else 70), xr[c][1], y_hi if c == col else min(y_oc[1], max(mk[L].y0 for L in G) + 90))
        a = np.array(page.get_pixmap(dpi=144, clip=R, colorspace=fitz.csGRAY).pil_image()) < 200
        for L in G:                                            # the printed letters and any text-option line are not picture ink
            m = mk[L]; a[max(int((m.y0 - R.y0 - 1) * sc), 0):int((m.y1 - R.y0 + 1) * sc), max(int((m.x0 - R.x0 - 1) * sc), 0):int((m.x1 - R.x0 + 1) * sc)] = False
            if is_text[L]: a[max(int((m.y0 - R.y0 - 2) * sc), 0):int((m.y1 - R.y0 + 2) * sc), :] = False
        blob, n = ndimage.label(ndimage.binary_dilation(a, structure=np.ones((3, 3)), iterations=4))   # 4 px = 2 pt each way
        for k, sl in enumerate(ndimage.find_objects(blob), 1):
            if int((a[sl] & (blob[sl] == k)).sum()) < 25: continue          # specks
            o = fitz.Rect(R.x0 + sl[1].start / sc, R.y0 + sl[0].start / sc, R.x0 + sl[1].stop / sc, R.y0 + sl[0].stop / sc)
            if min(o.width, o.height) < 16 and (o.x0 <= R.x0 + 1.5 or o.x1 >= R.x1 - 1.5 or o.y1 >= R.y1 - 1.5): continue   # a fragment cut by the area's edge: the neighbouring column or the next line
            row = [L for L in G if o.y0 - 10 <= mk[L].y0 <= o.y1 + 10 and o.x1 > mk[L].x1]
            if not row: continue                                # touches no letter row: stem scheme, next question, stray text
            rows_y = sorted({round(mk[L].y0 / 20) for L in row})
            if len(rows_y) > 1:                                 # two pictures grew into one blob (labels almost touch): cut it at the widest blank rows between the letters
                ls = sorted(row, key=lambda L: mk[L].y0); ls = [L for i, L in enumerate(ls) if i == 0 or abs(mk[L].y0 - mk[ls[i - 1]].y0) > 20]
                sub = a[sl] & (blob[sl] == k); y0s = sl[0].start; cuts = [0]
                for i in range(len(ls) - 1):
                    lo, hi = int((mk[ls[i]].y0 - R.y0) * sc) - y0s, int((mk[ls[i + 1]].y0 - R.y0) * sc) - y0s
                    lo, hi = max(lo, 0), min(hi, sub.shape[0])
                    prof = sub[lo:hi].any(axis=1); best, run, st = (None, 0), 0, 0
                    for j, v in enumerate(list(prof) + [True]):
                        if not v:
                            if run == 0: st = j
                            run += 1
                        else:
                            if run > best[1]: best = (st, run)
                            run = 0
                    cuts.append(lo + (best[0] + best[1] // 2 if best[0] is not None else (hi - lo) // 2))
                cuts.append(sub.shape[0])
                for i, L in enumerate(ls):
                    part = sub[cuts[i]:cuts[i + 1]]; yy, xx = np.nonzero(part)
                    if len(xx): owned[L].append(fitz.Rect(R.x0 + (sl[1].start + xx.min()) / sc, R.y0 + (y0s + cuts[i] + yy.min()) / sc, R.x0 + (sl[1].start + xx.max() + 1) / sc, R.y0 + (y0s + cuts[i] + yy.max() + 1) / sc))
                continue
            near = [L for L in row if mk[L].x0 <= o.x0 + o.width / 2 + 2] or row
            owned[max(near, key=lambda L: (mk[L].x0, -abs(mk[L].y0 - (o.y0 + o.y1) / 2)))].append(o + (2, 2, -2, -2))   # undo the 2 pt growth
    if any(not owned[L] and not is_text[L] for L in "abcd"): return None
    cells = []
    for L in "abcd":
        if is_text[L] or not owned[L]: cells.append(None); continue
        u = fitz.Rect(owned[L][0])
        for o in owned[L][1:]: u |= o
        cells.append(u + (-4, -4, 4, 4))
    return cells


def stem_blobs(page, col, y_lo, y_hi, skip=()):
    """the figure(s) of the stem: ink blobs between the stem text and the next question, after blanking printed text lines (4+ words or wide),
    the option letters and the option pictures already cut. Wide growth (7 pt) keeps a reaction scheme (reactant, arrow, reagent, product) in one piece."""
    from scipy import ndimage
    r = page.rect; mid = r.width / 2; xr = (70, mid + 12) if col == 0 else (mid + 4, r.width - 12)
    R = fitz.Rect(xr[0], y_lo, xr[1], y_hi)
    if R.height < 20: return []
    sc = 2.0; a = np.array(page.get_pixmap(dpi=144, clip=R, colorspace=fitz.csGRAY).pil_image()) < 200
    ws = [w for w in page.get_text("words") if fitz.Rect(w[:4]).intersects(R)]
    lines = {}
    for w in ws: lines.setdefault(round(w[3] / 3), []).append(w)
    for ln in lines.values():
        wide = max(w[2] for w in ln) - min(w[0] for w in ln)
        if len(ln) >= 4 or wide > 110 or any(re.fullmatch(r"\([a-dA-D]\)", w[4]) for w in ln):
            for w in ln: a[max(int((w[1] - R.y0 - 1) * sc), 0):int((w[3] - R.y0 + 1) * sc), max(int((w[0] - R.x0 - 1) * sc), 0):int((w[2] - R.x0 + 1) * sc)] = False
    for c in skip:
        a[max(int((c.y0 - R.y0 - 2) * sc), 0):int((c.y1 - R.y0 + 2) * sc), max(int((c.x0 - R.x0 - 2) * sc), 0):int((c.x1 - R.x0 + 2) * sc)] = False
    blob, n = ndimage.label(ndimage.binary_dilation(a, structure=np.ones((3, 3)), iterations=14))
    art = [fitz.Rect(d["rect"]) for d in page.get_drawings() if d.get("rect") is not None] + [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
    out = []
    for k, sl in enumerate(ndimage.find_objects(blob), 1):
        ink = a[sl] & (blob[sl] == k)
        if ink.sum() < 80: continue
        yy, xx = np.nonzero(ink)
        o = fitz.Rect(R.x0 + (sl[1].start + xx.min()) / sc, R.y0 + (sl[0].start + yy.min()) / sc, R.x0 + (sl[1].start + xx.max() + 1) / sc, R.y0 + (sl[0].start + yy.max() + 1) / sc)
        if (o.width < 14 and o.height < 14) or (o.height < 22 and o.width > 5 * o.height): continue   # specks; the site watermark banner
        txt = " ".join(w[4] for w in ws if fitz.Rect(w[:4]).intersects(o))
        if "JEEBOOKS" in txt or "KEY" in txt: continue                      # site watermark, answer-key grid
        if not any(d.intersects(o) and d.width < R.width * 0.98 for d in art): continue    # only words: a stem line fragment, not a figure
        out.append(o)
    merged = True
    while merged:                                                           # pieces of one scheme sitting on the same row (reactant ... arrow ... product)
        merged = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a_, b_ = out[i], out[j]
                if min(a_.y1, b_.y1) - max(a_.y0, b_.y0) > 0.5 * min(a_.height, b_.height) and max(a_.x0, b_.x0) - min(a_.x1, b_.x1) < 40:
                    out[i] = a_ | b_; out.pop(j); merged = True; break
            if merged: break
    out = [o + (-4, -4, 4, 4) for o in out]
    return sorted(out, key=lambda o: (o.y0, o.x0))


def tight(page, rect, path, m=6):
    """render the cell, then cut to its ink so neighbouring white space (and nothing else) is removed"""
    pm = page.get_pixmap(dpi=200, clip=rect, colorspace=fitz.csGRAY); a = np.array(pm.pil_image()) < 200
    ys, xs = np.nonzero(a)
    im = pm.pil_image().convert("RGB")
    if len(xs): im = im.crop((max(xs.min() - m, 0), max(ys.min() - m, 0), min(xs.max() + m, im.width), min(ys.max() + m, im.height)))
    im.save(path)
    return im.size


def crop(page, box, path, pad=3):
    r = page.rect; rect = fitz.Rect(box[0] / 1000 * r.width, box[1] / 1000 * r.height, box[2] / 1000 * r.width, box[3] / 1000 * r.height)
    rect = grow(page, rect) if pad is None else (rect + (-pad, -pad, pad, pad)) & r
    page.get_pixmap(dpi=200, clip=rect).save(path)


def main():
    pdf, ocr, out, figs = sys.argv[1], Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]); figs.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf); book = Path(pdf).stem; res = []
    for pg in map(int, sys.argv[5:]):
        png = ocr / f"page_{pg:03d}.png"; page = doc[pg - 1]
        for q in questions(blocks((ocr / f"page_{pg:03d}.txt").read_text(encoding="utf-8")), pg):
            qid = f"{book}_p{pg:03d}_q{q['number']:03d}"; sp = split_options(upper_markers(q["text"])); flags = []
            r = dict(qid=qid, number=q["number"], page=pg, stem_raw=sp["stem"], options_raw=sp["options"], options_status=sp["status"], stem_images=[], option_images={}, flags=flags)
            boxes = [[v for v in b] for b in q["boxes"]]
            if boxes:
                grown = []
                for b in boxes:                              # OCR boxes are tight and clip edge labels
                    g = grow(page, fitz.Rect(b[0] / 1000 * page.rect.width, b[1] / 1000 * page.rect.height, b[2] / 1000 * page.rect.width, b[3] / 1000 * page.rect.height))
                    grown.append([round(g.x0 * 1000 / page.rect.width), round(g.y0 * 1000 / page.rect.height), round(g.x1 * 1000 / page.rect.width), round(g.y1 * 1000 / page.rect.height)])
                stem_boxes, cells = grown, None
                if sp["status"] != "ok":                     # no four text options: the pictures may be the options
                    mc = marker_cells(page, grown, q["col"], q.get("above", 0), q["below"])
                    if mc == "TEXT":                         # (a)-(d) are printed text lines the OCR dropped: the pictures belong to the stem
                        stem_boxes, cells = grown, None; flags.append("OPTIONS_TEXT_MISSING_IN_OCR")
                    elif mc:
                        stem_boxes, cells = [b for b in grown if b[3] * page.rect.height / 1000 < mc[0].y0 + 2 and b[3] * page.rect.height / 1000 < mc[1].y0], mc
                    else:
                        stem_boxes, cells = option_cells(png, grown)
                    if cells is None and mc != "TEXT": flags.append("PICTURES_NOT_SPLIT_INTO_4")
                skip = [c for c in (cells or []) if isinstance(c, fitz.Rect)]
                y_lo_s = (q.get("text_bottom") or 0) / 1000 * page.rect.height + 1; y_hi_s = min(q["below"] / 1000 * page.rect.height, page.rect.height - 22) - 1
                if cells and isinstance(cells[0], fitz.Rect): y_hi_s = min(y_hi_s, min(c.y0 for c in cells if isinstance(c, fitz.Rect)) - 1)   # picture options start where the stem figure ends
                for i, o in enumerate(stem_blobs(page, q["col"], y_lo_s, y_hi_s, skip)):
                    p = figs / f"{qid}_fig{i + 1}.png"; page.get_pixmap(dpi=200, clip=o & page.rect).save(p); r["stem_images"].append(p.name)
                for L, c in zip("ABCD", cells or []):
                    if c is None: flags.append(f"OPTION_{L}_IS_TEXT"); continue
                    p = figs / f"{qid}_opt{L}.png"
                    if isinstance(c, fitz.Rect):
                        w, h = tight(page, c & page.rect, p)
                        if w < 60 or h < 40: flags.append(f"OPTION_{L}_IMAGE_TOO_SMALL")            # only its letter was cut: layout not understood
                    else: crop(page, c, p)
                    r["option_images"][L] = p.name
            if sp["status"] != "ok" and not r["option_images"]: flags.append("OPTIONS_" + sp["status"].upper())
            res.append(r)
    Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(res), "questions;", sum(bool(r["option_images"]) for r in res), "with option images;", sum(bool(r["flags"]) for r in res), "flagged")


if __name__ == "__main__":
    main()
