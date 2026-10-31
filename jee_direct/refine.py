"""Snap a model-proposed crop box to the actual drawing, without pulling in text.
refine(page, box, others) -> (rect, white_rects)
 1. render the area 6 pt around the box with figs2's text mask (stem lines, option text, letters blanked; labels touching art kept)
 2. blank the neighbouring boxes (other options) outside this box
 3. keep the ink blobs (grown 1 pt) that touch the box interior; new rect = their bounding box + 2 pt
 4. white_rects = every non-label word and every neighbouring box part inside the new rect, to be whited out when rendering
Fixes the judge complaints a plain rectangle cannot: a ring/arrow cut by 1 pt, a stray letter or neighbour fragment inside the box."""
import re
import fitz, numpy as np
from scipy import ndimage
import figs2

SC = figs2.SC


def _art(page):
    r = page.rect
    art = [fitz.Rect(d["rect"]) for d in page.get_drawings() if d.get("rect") is not None and d["rect"].width * d["rect"].height > 0] + [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
    return [a for a in art if a.get_area() < 0.5 * r.width * r.height and not (a.height < 2.5 and a.width > 150)]


def _label(t):
    texty = t.isalpha() and len(t) >= 3 and t[1:].islower()
    return len(t) <= 9 and not texty and not (t.islower() and len(t) >= 2 and t.isalpha()) and not re.fullmatch(r"\d{1,3}\.", t)


def _minus(o, b):
    """o without b, as up to four rects"""
    o, b = fitz.Rect(o), fitz.Rect(b)
    if not o.intersects(b): return [o]
    out = []
    if o.y0 < b.y0: out.append(fitz.Rect(o.x0, o.y0, o.x1, b.y0))
    if o.y1 > b.y1: out.append(fitz.Rect(o.x0, b.y1, o.x1, o.y1))
    yy0, yy1 = max(o.y0, b.y0), min(o.y1, b.y1)
    if o.x0 < b.x0: out.append(fitz.Rect(o.x0, yy0, b.x0, yy1))
    if o.x1 > b.x1: out.append(fitz.Rect(b.x1, yy0, o.x1, yy1))
    return out


def refine(page, box, others=(), reach=6.0, pad=2.0):
    box = fitz.Rect(box); E = (box + (-reach, -reach, reach, reach)) & page.rect; art = _art(page)
    col = 0 if (box.x0 + box.x1) / 2 < page.rect.width / 2 + 6 else 1
    R, a, ws = figs2._seg(page, col, max(E.y0 - 2, 0), min(E.y1 + 2, page.rect.height), art, None)
    x0, y0 = max(int((E.x0 - R.x0) * SC), 0), max(int((E.y0 - R.y0) * SC), 0)
    a = a[y0:int((E.y1 - R.y0) * SC), x0:int((E.x1 - R.x0) * SC)].copy()
    own = (int((box.x0 - E.x0) * SC), int((box.y0 - E.y0) * SC), int((box.x1 - E.x0) * SC), int((box.y1 - E.y0) * SC))
    for o in others:                                              # neighbouring options are not ours
        for p in _minus(fitz.Rect(o) & E, box):
            a[max(int((p.y0 - E.y0) * SC), 0):int((p.y1 - E.y0) * SC), max(int((p.x0 - E.x0) * SC), 0):int((p.x1 - E.x0) * SC)] = False
    if not a.any(): return box, []
    lab, _ = ndimage.label(ndimage.binary_dilation(a, structure=np.ones((3, 3)), iterations=2))
    inner = np.zeros(a.shape, dtype=bool); inner[max(own[1], 0):own[3], max(own[0], 0):own[2]] = True
    keep = np.unique(lab[inner & a]); keep = keep[keep > 0]
    if not len(keep): return box, []
    yy, xx = np.nonzero(np.isin(lab, keep) & a)
    new = fitz.Rect(E.x0 + xx.min() / SC, E.y0 + yy.min() / SC, E.x0 + (xx.max() + 1) / SC, E.y0 + (yy.max() + 1) / SC) + (-pad, -pad, pad, pad)
    new &= page.rect
    white = []
    for w in page.get_text("words"):                              # printed text inside the new rect that is not a figure label near art
        wr = fitz.Rect(w[:4])
        if not wr.intersects(new): continue
        near = any(figs2._gap(wr, r) <= (10 if len(w[4]) <= 2 else 6) for r in art if r.intersects(new + (6, 6, 6, 6)))
        if not (near and _label(w[4])): white.append(wr)
    for o in others:
        white += [p & new for p in _minus(fitz.Rect(o) & new, box) if not (p & new).is_empty]
    return new, white
