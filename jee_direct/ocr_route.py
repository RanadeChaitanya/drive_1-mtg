"""OCR route for the JEE book (the old pipeline's way): DeepSeek-OCR page text with per-mille boxes -> questions, text options,
stem figures and ONE IMAGE PER OPTION when the options are drawings. Code only; the LaTeX clean-up of stem/options is the model stage after this.
python ocr_route.py <pdf> <ocr_dir> <out.json> <figs_dir> <page> [<page> ...]      ocr_dir has page_NNN.txt and page_NNN.png (ocr_test.py)
Reuses claude_pipeline/cet_figures.py (split_box, grow) and cet_options.py (split_options)."""
import json, re, sys
from pathlib import Path
import fitz, numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "claude_pipeline"))
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
    """option pictures cut by the printed (a)-(d) letters (text layer), NOT by the OCR boxes, which tile pictures arbitrarily.
    Layouts: stacked, one row, 2x2. None when the letters are text-option lines (spacing < 40pt: OCR lost TEXT options, not pictures)."""
    r = page.rect; rects = [fitz.Rect(b[0] / 1000 * r.width, b[1] / 1000 * r.height, b[2] / 1000 * r.width, b[3] / 1000 * r.height) for b in boxes]
    U = fitz.Rect(70 if col == 0 else r.width / 2 + 4, max(min(x.y0 for x in rects), above / 1000 * r.height + 2), r.width / 2 - 4 if col == 0 else r.width - 30, max(max(x.y1 for x in rects), 0) + 0)
    U.y1 = max(U.y1, min(below / 1000 * r.height - 2, U.y1 + 60))
    mk, prev_y = {}, U.y0 - 6
    for L in "abcd":                                            # first hit of each letter below the previous one, inside the column, up to 50pt past the boxes
        hits = [h for h in page.search_for(f"({L})", clip=fitz.Rect(U.x0 - 16, U.y0 - 6, U.x1 + 4, U.y1 + 50)) if h.y0 >= prev_y - 2]
        if not hits: return None
        mk[L] = hits[0]; prev_y = hits[0].y0 - 2 if L == "a" else hits[0].y0 - 2
    words = page.get_text("words")
    is_text = {L: any(abs(w[1] - mk[L].y0) < 3 and 0 <= w[0] - mk[L].x1 < 16 for w in words) for L in "abcd"}   # a word right after the letter = a printed text option
    if sum(is_text.values()) >= 2: return "TEXT"                     # the options are text lines (OCR lost them): not pictures
    ys = [mk[L].y0 for L in "abcd"]; xs = [mk[L].x0 for L in "abcd"]
    U = fitz.Rect(U.x0, U.y0, U.x1, min(max(U.y1, ys[3] + 70), below / 1000 * r.height - 2)) if max(xs) - min(xs) < 20 else U
    ink = lambda R: np.array(page.get_pixmap(dpi=144, clip=R & page.rect, colorspace=fitz.csGRAY).pil_image()) < 200

    def cut(axis, lo, hi, fallback):
        """centre of the widest blank band between lo and hi (points) along an axis; the label of one picture must not be sliced by a midpoint"""
        if hi - lo < 6: return fallback
        R = fitz.Rect(U.x0, lo, U.x1, hi) if axis == "y" else fitz.Rect(lo, U.y0, hi, U.y1)
        a = ink(R); prof = a.any(axis=1) if axis == "y" else a.any(axis=0); bands, run, start = [], 0, 0
        for i, v in enumerate(list(prof) + [True]):
            if not v:
                if run == 0: start = i
                run += 1
            else:
                if run: bands.append((start, run))
                run = 0
        if axis == "y":                                         # rows: the LAST band, so a label under its own picture ('Br', 'NO2') stays with it
            ok = [b for b in bands if b[1] >= 10]; best = ok[-1] if ok else (max(bands, key=lambda b: b[1]) if bands else None)
        else:                                                   # columns: the widest band
            best = max(bands, key=lambda b: b[1]) if bands else None
        return fallback if best is None else lo + (best[0] + best[1] / 2) * 72 / 144

    above_figs = [x.y1 for x in rects if x.y1 < ys[0] - 8]       # a stem figure (a reaction scheme) sitting above option (a)
    if above_figs: U.y0 = max(U.y0, max(above_figs) + 1)
    top_row = min(ys)
    a_ = ink(fitz.Rect(U.x0, U.y0, U.x1, top_row - 4)) if top_row - 4 - U.y0 > 6 else None
    if a_ is not None:                                          # start the first row at the last blank band above its letters: no stem line or arrow bleeds in
        prof = a_.any(axis=1); last = None; i = len(prof) - 1
        while i >= 0:
            if not prof[i]:
                j = i
                while j >= 0 and not prof[j]: j -= 1
                if i - j >= 4: last = (j + 1 + i) / 2; break
                i = j
            else: i -= 1
        if last is not None: U.y0 = U.y0 + last * 72 / 144
    if max(xs) - min(xs) < 20:                                  # stacked
        if min(ys[1] - ys[0], ys[2] - ys[1]) < 40: return "TEXT"
        cuts = [U.y0] + [cut("y", ys[i] + 8, ys[i + 1] - 4, (ys[i] + ys[i + 1]) / 2) for i in range(3)] + [U.y1]
        cells = [fitz.Rect(mk[L].x1 + 2, cuts[i], U.x1, cuts[i + 1]) & U for i, L in enumerate("abcd")]
        if is_text["d"] or ys[3] - ys[2] < 40: cells[3] = None                  # a printed text line under three pictures ('(d) Both (a) and (b)')
        return cells
    if max(ys) - min(ys) < 20:                                  # one row
        if min(xs[i + 1] - xs[i] for i in range(3)) < 40: return "TEXT"
        cuts = [U.x0] + [cut("x", mk["abcd"[i]].x1 + 20, xs[i + 1] - 2, xs[i + 1] - 3) for i in range(3)] + [U.x1]
        return [fitz.Rect(mk[L].x1 + 2, U.y0, cuts[i + 1], U.y1) for i, L in enumerate("abcd")]
    if max(ys) - min(ys) < 40: return "TEXT"                    # 2x2, row-major: a b / c d
    top = [L for L in "abcd" if ys["abcd".index(L)] < (max(ys) + min(ys)) / 2]
    my = cut("y", min(mk[L].y0 for L in "cd") - 70 if False else max(mk[L].y0 for L in top) + 8, min(mk[L].y0 for L in "abcd" if L not in top) - 4, (max(ys) + min(ys)) / 2)
    mx = cut("x", min(mk[L].x1 for L in "ac") + 20, min(mk[L].x0 for L in "bd") - 2, min(mk[L].x0 for L in "bd") - 3)
    out = []
    for L in "abcd":
        is_top, left = mk[L].y0 < my, mk[L].x0 < mx
        out.append(fitz.Rect(mk[L].x1 + 2, U.y0 if is_top else my, mx if left else U.x1, my if is_top else U.y1))
    return out


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
                for i, b in enumerate(stem_boxes):
                    p = figs / f"{qid}_fig{i + 1}.png"; crop(page, b, p); r["stem_images"].append(p.name)
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
