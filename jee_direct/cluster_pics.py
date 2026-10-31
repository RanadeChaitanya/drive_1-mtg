"""Approach 1+2, no model: vector clustering of the page's drawn art + figure labels into figures, option markers (a)-(d) claim their picture,
the rest are stem figures; the question's own text lines are whited out before the crop (approach 2).
pictures2(page, q, y_lo, y_hi) -> {"stem": [Rect], "opts": {L: Rect}}"""
import re
import fitz

MARK = re.compile(r"^\(?([a-dA-D])\)?\s*$")
GAP = 5


def _spans(page, r):
    for b in page.get_text("dict", clip=r)["blocks"]:
        if b["type"] == 0:
            for l in b["lines"]:
                yield l, [s for s in l["spans"] if s["text"].strip()]


def _gap(a, b):
    return max(a.x0 - b.x1, b.x0 - a.x1, 0) ** 2 + max(a.y0 - b.y1, b.y0 - a.y1, 0) ** 2


def clusters(page, reg, gap=GAP):
    art = [fitz.Rect(d["rect"]) for d in page.get_drawings() if d.get("rect") is not None] + [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
    art = [a & reg for a in art if a.intersects(reg) and a.width * a.height < 0.5 * reg.width * reg.height and not (a.height < 2 and a.width > 100)]
    art = [a for a in art if not a.is_empty]
    if not art: return [], []
    groups = [[a] for a in art]
    merged = True
    while merged:
        merged = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if any(_gap(a, b) <= gap ** 2 for a in groups[i] for b in groups[j]):
                    groups[i] += groups.pop(j); merged = True; break
            if merged: break
    boxes = [fitz.Rect(min(a.x0 for a in g), min(a.y0 for a in g), max(a.x1 for a in g), max(a.y1 for a in g)) for g in groups]
    lines = [(l, sp) for l, sp in _spans(page, reg) if sp]
    marks = []
    used = set()
    for n, (l, sp) in enumerate(lines):
        t = "".join(s["text"] for s in sp).strip(); bb = fitz.Rect(l["bbox"])
        if MARK.match(t) and re.search(r"[a-d]", t.lower()): marks.append((t.strip("() ").lower().upper(), bb)); used.add(n)
        elif re.fullmatch(r"\d{1,3}\.", t): used.add(n)
    for _ in range(4):                                              # labels / reagent text touching a figure join it
        for n, (l, sp) in enumerate(lines):
            if n in used: continue
            t = " ".join(s["text"] for s in sp).strip(); bb = fitz.Rect(l["bbox"])
            words = sum(w.isalpha() and len(w) >= 3 and w[1:].islower() for w in t.split())
            textline = words >= 3 or len(t) > 45 or len(t.split()) > 2 or len(t) > 22
            for i, c in enumerate(boxes):
                lim = 2 if textline else 4
                if _gap(bb, c) <= lim ** 2 and (not textline or (bb.x0 >= c.x0 - 3 and bb.x1 <= c.x1 + 3)):
                    boxes[i] = c | bb; used.add(n); break
    changed = True
    while changed:                                                   # re-merge clusters that now touch
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if _gap(boxes[i], boxes[j]) <= 3 ** 2: boxes[i] |= boxes.pop(j); changed = True; break
            if changed: break
    return boxes, marks


def pictures2(page, q, y_lo, y_hi, xr):
    reg = fitz.Rect(xr[0], y_lo, xr[1], y_hi)
    boxes, marks = clusters(page, reg)
    img_letters = [L for L, v in q["options"].items() if not v]
    opts, taken = {}, set()
    for L in img_letters:
        m = [bb for t, bb in marks if t == L]
        if not m or not boxes: continue
        mb = m[0]; best = None
        for i, c in enumerate(boxes):
            if i in taken: continue
            d = _gap(mb, c) ** 0.5 + (40 if c.x1 < mb.x0 + 4 else 0) + (25 if c.y0 > mb.y1 + 30 and c.x0 > mb.x1 + 60 else 0)
            if best is None or d < best[0]: best = (d, i)
        if best and best[0] <= 45: opts[L] = best[1]; taken.add(best[1])
    # a stacked row layout may put several clusters in one option (structure + reagent): fold clusters sitting inside the row band of an option
    out = {L: fitz.Rect(boxes[i]) for L, i in opts.items()}
    stem = [c for i, c in enumerate(boxes) if i not in taken]
    return dict(stem=sorted(stem, key=lambda r: (round(r.y0 / 20), r.x0)), opts=out)


def split_shared(page, box, letters, reg):
    """one merged outline holds several options: re-cluster its art finely and give each sub-cluster to the nearest option letter (letter sits lower-left of its picture)"""
    sub, _ = clusters(page, fitz.Rect(box), gap=2)
    _, marks = clusters(page, reg)
    pos = {t: bb for t, bb in marks if t in letters}
    res = {}
    for c in sub:
        best = None
        for L, mb in pos.items():
            d = _gap(mb, c) ** 0.5 + (40 if c.x1 < mb.x0 + 4 else 0)
            if best is None or d < best[0]: best = (d, L)
        if best: res[best[1]] = (res[best[1]] | c) if best[1] in res else fitz.Rect(c)
    return res
