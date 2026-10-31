"""Pictures from the PDF's own drawing order (no model, no geometry guessing).
The content stream of a born-digital paper is written question by question: question number+text, then the stem figure's paths and labels, then the
marker "(a)" followed by option A's paths and labels, "(b)" ... so every drawn item is assigned to the stem or to an option by its sequence number alone.
python stream_pics.py <pdf> <questions.json> <out_dir> [qids.json]  -> boxes.json (same format as the model boxes) + crops/judge_in.json + groups.json"""
import json, os, re, sys
from pathlib import Path
import fitz
import numpy as np

MARK = re.compile(r"^\(?([a-dA-D])\)?\s*$")
PAD = 2
SVG_NAME = []


def page_items(page):
    bl = page.get_bboxlog(); tt = {}
    for s in page.get_texttrace():
        s["text"] = "".join(chr(c[0]) for c in s["chars"]); tt.setdefault(s["seqno"], []).append(s)
    return bl, tt


def question_start(q, tt):
    for sq, spans in tt.items():
        for s in spans:
            b = s["bbox"]
            if abs(b[1] - q["y0"]) <= 4 and s["text"].strip().startswith(f"{q['number']}.") and abs(b[0] - q.get("x0", b[0])) < 400: return sq
    return None


def groups_for(page, Q, q, bl, tt):
    """-> (stem_items, {letter: items}) with items = list of (seqno, Rect); plus own seqnos"""
    H, W = page.rect.height, page.rect.width
    starts = sorted(s for s in (question_start(v, tt) for v in Q if v["page"] == q["page"]) if s is not None)
    s0 = question_start(q, tt)
    if s0 is None: return None
    nxt = [s for s in starts if s > s0]; s1 = nxt[0] if nxt else len(bl)
    for sq in range(s0, s1):                                            # the answer-key grid and section banners end the question's own items
        if any(re.search(r"ANSWER KEY|Numeric Value Answer", s["text"], re.I) for s in tt.get(sq, [])): s1 = sq; break
    stem, opts, cur = [], {}, None; own = set(); late = []
    for sq in range(s0, s1):
        kind, bb = bl[sq][0], fitz.Rect(bl[sq][1])
        if bb.x1 >= bb.x0 and bb.y1 >= bb.y0 and (bb.x1 - bb.x0 < 0.6 or bb.y1 - bb.y0 < 0.6):      # a vertical bond / axis line has zero width: widen it so it counts and is not 'empty'
            bb = fitz.Rect(bb.x0 - 0.4, bb.y0 - 0.4, bb.x1 + 0.4, bb.y1 + 0.4)
        if "text" in kind:
            for s in tt.get(sq, []):
                t = s["text"].strip(); sb = fitz.Rect(s["bbox"])
                m = MARK.match(t)
                if m and sq > s0: cur = m.group(1).upper(); opts.setdefault(cur, []); continue
                e = re.search(r"\(([a-dA-D])\)\s*$", t)
                if e and len(t) > 6 and e.group(1).upper() == ("A" if cur is None else chr(ord(cur) + 1)): cur = e.group(1).upper(); opts.setdefault(cur, []); continue      # marker glued to the end of a text line
                words = sum(w.isalpha() and len(w) >= 3 and w[1:].islower() for w in t.split())
                if sq == s0 or re.fullmatch(r"\d{1,3}\.", t) or not t: continue                                        # question number / the stem paragraph
                if words >= 1 and len(t) > 6:
                    if sb.height <= 18 and not (sb.y1 < 62 or sb.y0 > H - 22): late.append((sq, sb, cur))                # may be a reagent / axis name inside the figure: decided below
                    continue
                if sb.y1 < 62 or sb.y0 > H - 22: continue
                (stem if cur is None else opts[cur]).append((sq, sb))
        elif kind in ("fill-path", "stroke-path", "fill-image", "fill-shade"):
            if bb.is_empty or bb.width * bb.height > 0.4 * W * H / 2 or (bb.height < 2 and bb.width > 100) or bb.width > 260 or bb.y1 < 62 or bb.y0 > H - 22 or (kind == "fill-image" and bb.height < 20 and bb.width < 160): continue      # page-wide rules/tables/banners and the footer logo are not figures
            (stem if cur is None else opts[cur]).append((sq, bb))
    for sq, sb, c in late:                                              # text sitting inside (or touching) its own figure is a label of it
        grp = stem if c is None else opts.get(c, [])
        if not grp: continue
        g = union(grp); g = fitz.Rect(g.x0 - 6, g.y0 - 6, g.x1 + 6, g.y1 + 6)
        if g.contains(sb) or (sb.width < 0.6 * (g.width) and g.intersects(sb) and (g & sb).get_area() > 0.5 * sb.get_area()): grp.append((sq, sb))
    return stem, opts


def union(items):
    r = fitz.Rect(items[0][1])
    for _, b in items[1:]: r |= b
    return r


def split_stem(items, gap=14):
    """several stem figures: cluster by rectangle gap"""
    boxes = [fitz.Rect(b) for _, b in items]; groups = [[b] for b in boxes]; changed = True
    while changed:
        changed = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                ri = fitz.Rect(groups[i][0]); [ri.include_rect(x) for x in groups[i]]; rj = fitz.Rect(groups[j][0]); [rj.include_rect(x) for x in groups[j]]
                if max(ri.x0 - rj.x1, rj.x0 - ri.x1, 0) ** 2 + max(ri.y0 - rj.y1, rj.y0 - ri.y1, 0) ** 2 <= gap ** 2: groups[i] += groups.pop(j); changed = True; break
            if changed: break
    out = []
    for g in groups:
        r = fitz.Rect(g[0]); [r.include_rect(x) for x in g]; out.append(r)
    return sorted(out, key=lambda r: (round(r.y0 / 20), r.x0))


def render(pdf, pno, box, own, tt, dr):
    """crop the box; text spans that are not part of this figure (by sequence number) are whited out, the figure's own labels stay"""
    pg = fitz.open(pdf)[pno]; r = (fitz.Rect(box) + (-PAD, -PAD, PAD, PAD)) & pg.rect
    for sq, spans in tt.items():
        if sq in own: continue
        for s in spans:
            sb = fitz.Rect(s["bbox"])
            if s["text"].strip() and sb.intersects(r) and sb.height <= 18: pg.add_redact_annot(sb, fill=(1, 1, 1))      # multi-line 'spans' have a bbox over the whole paragraph: handled by the line pass below
    inner = fitz.Rect(box) + (-1.5, -1.5, 1.5, 1.5)
    for w in pg.get_text("words", clip=r):                                # word boxes are exact (a text op that mixes a paragraph with figure glyphs has one huge line box, which erased the figure's own '|' bonds)
        wb = fitz.Rect(w[:4]); t = w[4]
        if len(t) >= 3 and any(c.isalpha() for c in t) and t[1:].lower() != t[1:].upper() and any(c.islower() for c in t[1:]) and not inner.contains(wb): pg.add_redact_annot(wb + (0.4, 0.4, -0.4, -0.4), fill=(1, 1, 1))
    pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    sh = pg.new_shape()                                                  # foreign drawings (other options / the stem) are redrawn in white, stroke by stroke, so overlapping boxes do not matter
    for d in dr:
        if d["seqno"] in own or not fitz.Rect(d["rect"]).intersects(r) or fitz.Rect(d["rect"]).get_area() > 0.4 * pg.rect.get_area() / 2: continue
        for it in d["items"]:
            if it[0] == "l": sh.draw_line(it[1], it[2])
            elif it[0] == "c": sh.draw_bezier(it[1], it[2], it[3], it[4])
            elif it[0] == "re": sh.draw_rect(it[1])
            elif it[0] == "qu": sh.draw_quad(it[1])
        sh.finish(color=(1, 1, 1), fill=(1, 1, 1) if d.get("fill") else None, width=(d.get("width") or 1) + 1.6, closePath=False)
    sh.commit()
    pm = pg.get_pixmap(dpi=200, clip=r)
    if SVG_NAME:                                                          # exact vector export of the same cleaned crop (paths + labels as outlines), no model
        pg.set_cropbox(r); Path(SVG_NAME[0]).write_text(pg.get_svg_image(text_as_path=True), encoding="utf-8")
    a = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w, pm.n)[:, :, :3].min(axis=2) < 140
    return pm, bool(a[0].any() or a[-1].any() or a[:, 0].any() or a[:, -1].any())


if __name__ == "__main__":
    pdf, qj, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf); Q = json.load(open(qj, encoding="utf-8"))["questions"]; want = set(json.load(open(sys.argv[4]))) if len(sys.argv) > 4 else None
    cache = {}; boxes, items, flags, nostart = [], [], {}, 0
    for q in Q:
        if want is not None and q["qid"] not in want: continue
        pno = q["page"] - 1
        if pno not in cache: cache[pno] = page_items(doc[pno])
        bl, tt = cache[pno]; dr = cache.setdefault((pno, 'd'), doc[pno].get_drawings()); g = groups_for(doc[pno], Q, q, bl, tt)
        if g is None: nostart += 1; continue
        stem, opts = g; figs = split_stem(stem) if stem else []
        img_letters = [L for L, v in q["options"].items() if not v]
        b = dict(qid=q["qid"], stem_figures=[[r.x0, r.y0, r.x1, r.y1] for r in figs], options={L: ([union(opts[L]).x0, union(opts[L]).y0, union(opts[L]).x1, union(opts[L]).y1] if opts.get(L) else None) for L in "ABCD"})
        boxes.append(b)
        it = dict(qid=q["qid"], number=q["number"], stem_figures=[], option_images={}); fl = {}
        owns = {}
        for i, r in enumerate(figs):
            own = {sq for sq, bb in stem if bb.intersects(r)}; SVG_NAME[:] = [str(out / f"{q['qid']}_fig{i + 1}.svg")] if os.environ.get('SVG') else []; pm, bad = render(pdf, pno, r, own, tt, dr); p = out / f"{q['qid']}_fig{i + 1}.png"; pm.save(p); it["stem_figures"].append(str(p)); fl[f"fig{i + 1}"] = bad
        for L in "ABCD":
            if opts.get(L):
                r = union(opts[L]); own = {sq for sq, _ in opts[L]}; SVG_NAME[:] = [str(out / f"{q['qid']}_opt{L}.svg")] if os.environ.get('SVG') else []; pm, bad = render(pdf, pno, r, own, tt, dr); p = out / f"{q['qid']}_opt{L}.png"; pm.save(p); it["option_images"][L] = str(p); fl[L] = bad
        items.append(it); flags[q["qid"]] = fl
    json.dump(boxes, open(out / "boxes.json", "w")); json.dump(items, open(out / "judge_in.json", "w"), indent=0); json.dump(flags, open(out / "flags.json", "w"), indent=0)
    print(len(boxes), "questions;", nostart, "without a locatable start;", sum(len(f) for f in flags.values()), "images;", sum(sum(f.values()) for f in flags.values()), "with ink on the border;",
          sum(1 for i in items if i["stem_figures"] or i["option_images"]), "questions with pictures")
