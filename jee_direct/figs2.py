"""Pictures of ONE question, cut from the rendered page. Region = the question's own rows (its number line to the next question in the column),
plus the head of the next column when the options run on there. Positions come from the born-digital text layer, not from OCR boxes.
pictures(page, col, y0, y1, cont_y) -> dict(stem=[Rect], opts=[Rect|None]*4 | None, flags=[...])
Rules: a word is figure label only if it touches drawn art (<=3 pt); every other word (stem lines, option text, question numbers) is blanked.
Option pictures = blobs (ink grown 2 pt) owned by the nearest printed letter on their left in the same row; stem figures = the other blobs (grown 7 pt)."""
import fitz, numpy as np
from scipy import ndimage

SC = 2.0                                                        # 144 dpi
LET = {f"({L})": L for L in "abcd"}


def _xr(page, col):
    W = page.rect.width; g = W / 2 + 24
    return (40, W / 2 + 40) if col == 0 else (W / 2 + 20, W - 10)


def _gap(p, q):
    return (max(p.x0 - q.x1, q.x0 - p.x1, 0) ** 2 + max(p.y0 - q.y1, q.y0 - p.y1, 0) ** 2) ** 0.5


def _seg(page, col, ya, yb, art, letters_words):
    """ink array of a segment with text blanked; returns (R, ink, words_in_R)"""
    R = fitz.Rect(30, ya, page.rect.width - 4, yb); R.col = col
    a = np.array(page.get_pixmap(dpi=144, clip=R, colorspace=fitz.csGRAY).pil_image()) < 200
    ws = [w for w in page.get_text("words") if fitz.Rect(w[:4]).intersects(R)]
    near_art = [r for r in art if r.intersects(R + (4, 4, 4, 4))]
    keep = {}
    lines = {}
    for w in ws: lines.setdefault(round(w[3] / 3), []).append(w)
    texty = lambda t: t.isalpha() and len(t) >= 3 and t[1:].islower()          # 'Arrange', 'respectively', 'compound': words, not chemical labels
    text_line = {id(w) for ln in lines.values() if sum(texty(v[4]) for v in ln) >= 2 or any(texty(v[4]) and len(v[4]) >= 6 for v in ln) for w in ln}
    for w in ws:
        t = w[4]; wr = fitz.Rect(w[:4])
        label = (len(t) <= 9 and not (t.isalpha() and len(t) >= 4 and t[1:].islower()) and not (t.islower() and len(t) >= 2 and t.isalpha()))   # CH3, NO2, Cl, H3C, (i): labels; 'respectively', 'is': text
        keep[id(w)] = (t not in LET) and id(w) not in text_line and any(_gap(wr, r) <= ((10 if len(t) <= 2 else 6) if label else 2) for r in near_art)
        w_label = label
    for _ in range(3):                                           # a label chain: 'O', '-', 'NHCH3' / 'CO2', 'H': only the first touches a bond
        for w in ws:
            t = w[4]; wr = fitz.Rect(w[:4])
            if keep[id(w)] or t in LET or id(w) in text_line or len(t) > 9 or (t.isalpha() and t.islower()) or texty(t): continue
            if any(keep[id(v)] and _gap(wr, fitz.Rect(v[:4])) <= 6 for v in ws if v is not w): keep[id(w)] = True
    for w in ws:
        if not keep[id(w)]:                                      # letters and stem/option text: not picture ink
            wr = fitz.Rect(w[:4]); a[max(int((wr.y0 - R.y0 - 1) * SC), 0):int((wr.y1 - R.y0 + 1) * SC), max(int((wr.x0 - R.x0 - 1) * SC), 0):int((wr.x1 - R.x0 + 1) * SC)] = False
    return R, a, ws


def _blobs(R, a, grow, page_w=558.0, page_h=720.0):
    out = []
    lab, n = ndimage.label(ndimage.binary_dilation(a, structure=np.ones((3, 3)), iterations=grow))
    for k, sl in enumerate(ndimage.find_objects(lab), 1):
        ink = a[sl] & (lab[sl] == k)
        if ink.sum() < 25: continue
        yy, xx = np.nonzero(ink)
        o = fitz.Rect(R.x0 + (sl[1].start + xx.min()) / SC, R.y0 + (sl[0].start + yy.min()) / SC, R.x0 + (sl[1].start + xx.max() + 1) / SC, R.y0 + (sl[0].start + yy.max() + 1) / SC)
        o.px = (sl, k, lab)                                     # for splitting merged blobs
        cx = (o.x0 + o.x1) / 2
        if o.y1 < 70 or o.y0 > page_h - 30: continue                          # running header / footer
        if (R.col == 0) != (cx < page_w / 2 + 6): continue                # the neighbouring column's pictures sit in the same rows
        out.append(o)
    return out


def pictures(page, col, y0, y1, cont_y=None, lo=None, hi=None):
    r = page.rect; H = r.height; flags = []
    art = [fitz.Rect(d["rect"]) for d in page.get_drawings() if d.get("rect") is not None and d["rect"].width * d["rect"].height > 0] + [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
    art = [a for a in art if a.get_area() < 0.5 * r.width * H and not (a.height < 2.5 and a.width > 150)]    # table rules, page frames
    segs = [(col, max(y0 - 1, 60), min(y1, H - 24))]
    keep_y = (lo if lo is not None else -1e9, hi if hi is not None else 1e9)        # a blob belongs to this question if its centre is in here
    if cont_y and cont_y > 110: segs.append((1 - col, 62, cont_y - 2))                     # options continue at the head of the next column
    words_all = page.get_text("words")
    # 1. the printed letters
    mk, side, prev, si0 = {}, {}, max(segs[0][1], keep_y[0]) - 2, 0
    for L in "abcd":
        for si in range(si0, len(segs)):
            c, ya, yb = segs[si]; x0, x1 = _xr(page, c)
            ya_l = max(ya, keep_y[0]) if si == 0 else ya                                      # the margin above belongs to the previous question: its letters are not ours
            hits = [h for h in page.search_for(f"({L})", clip=fitz.Rect(x0 - 12, ya_l, x1, yb)) if si > si0 or h.y0 >= prev - 2]
            if hits:
                mk[L] = hits[0]; side[L] = si; prev = hits[0].y0 - 2; si0 = si; break
    segdata = [_seg(page, c, ya, yb, art, None) for c, ya, yb in segs]
    owned = {L: [] for L in "abcd"}; opts = None
    if len(mk) == 4:
        pic_right = lambda L: any(abs((a.y0 + a.y1) / 2 - (mk[L].y0 + mk[L].y1) / 2) < 25 and 0 <= a.x0 - mk[L].x1 < 45 for a in art)   # a drawing right after the letter: a picture option
        text_l = {L: any(abs(w[1] - mk[L].y0) < 3 and 0 <= w[0] - mk[L].x1 < 16 for w in words_all) and not pic_right(L) for L in "abcd"}
        if sum(text_l.values()) >= 2: flags.append("OPTIONS_ARE_TEXT")
        else:
            for si, (R, a, ws) in enumerate(segdata):
                G = [L for L in "abcd" if side[L] == si]
                if not G: continue
                for L in G:
                    if text_l[L]: m = mk[L]; a[max(int((m.y0 - R.y0 - 2) * SC), 0):int((m.y1 - R.y0 + 2) * SC), :] = False
                top = min(mk[L].y0 for L in G) - 62
                for o in _blobs(R, a, 4, r.width, H):
                    if si == 0 and not (keep_y[0] <= (o.y0 + o.y1) / 2 <= keep_y[1]): continue
                    txt = " ".join(w[4] for w in ws if fitz.Rect(w[:4]).intersects(o))
                    if "KEY" in txt or "JEEBOOKS" in txt or (o.height < 22 and o.width > 5 * o.height): continue
                    if min(o.width, o.height) < 16 and (o.x0 <= R.x0 + 1.5 or o.x1 >= R.x1 - 1.5 or o.y1 >= R.y1 - 1.5): continue
                    if o.y1 < top: continue
                    row = [L for L in G if o.y0 - 10 <= mk[L].y0 <= o.y1 + 10 and o.x1 > mk[L].x1]
                    if not row: continue
                    ys = sorted({round(mk[L].y0 / 20) for L in row})
                    if len(ys) > 1:                                  # two pictures grew together: cut at the widest blank rows between the letters
                        sl, k, lab = o.px; sub = a[sl] & (lab[sl] == k); ls = sorted(row, key=lambda L: mk[L].y0); ls = [L for i, L in enumerate(ls) if i == 0 or abs(mk[L].y0 - mk[ls[i - 1]].y0) > 20]
                        cuts = [0]
                        for i in range(len(ls) - 1):
                            lo = max(int((mk[ls[i]].y0 - R.y0) * SC) - sl[0].start, 0); hi = min(int((mk[ls[i + 1]].y0 - R.y0) * SC) - sl[0].start, sub.shape[0])
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
                            yy, xx = np.nonzero(sub[cuts[i]:cuts[i + 1]])
                            if len(xx): owned[L].append(fitz.Rect(R.x0 + (sl[1].start + xx.min()) / SC, R.y0 + (sl[0].start + cuts[i] + yy.min()) / SC, R.x0 + (sl[1].start + xx.max() + 1) / SC, R.y0 + (sl[0].start + cuts[i] + yy.max() + 1) / SC))
                        continue
                    near = [L for L in row if mk[L].x0 <= o.x0 + o.width / 2 + 2] or row
                    owned[max(near, key=lambda L: (mk[L].x0, -abs(mk[L].y0 - (o.y0 + o.y1) / 2)))].append(o)
            if all(owned[L] or text_l[L] for L in "abcd"):
                opts = []
                for L in "abcd":
                    if not owned[L]: opts.append(None); flags.append(f"OPTION_{L.upper()}_IS_TEXT"); continue
                    u = fitz.Rect(owned[L][0])
                    for o in owned[L][1:]: u |= o
                    opts.append(u + (-4, -4, 4, 4))
            else: flags.append("OPTION_PICTURE_MISSING")
    # 2. stem figures: the blobs that are not options, in the question's own column
    R, a, ws = segdata[0]
    for c in (opts or []):
        if c is not None: a[max(int((c.y0 - R.y0 - 2) * SC), 0):int((c.y1 - R.y0 + 2) * SC), max(int((c.x0 - R.x0 - 2) * SC), 0):int((c.x1 - R.x0 + 2) * SC)] = False
    for L in mk:                                                 # option letters that belong to text options
        pass
    pieces = []
    for o in _blobs(R, a, 14, r.width, H):
        if not (keep_y[0] <= (o.y0 + o.y1) / 2 <= keep_y[1]): continue
        txt = " ".join(w[4] for w in ws if fitz.Rect(w[:4]).intersects(o))
        if "KEY" in txt or "JEEBOOKS" in txt or (o.height < 22 and o.width > 5 * o.height) or (o.width < 14 and o.height < 14): continue
        if min(o.width, o.height) < 16 and (o.x0 <= R.x0 + 1.5 or o.x1 >= R.x1 - 1.5 or o.y1 >= R.y1 - 1.5): continue
        pieces.append(fitz.Rect(o))
    merged = True
    while merged:                                                # pieces of one scheme on the same row (reactant ... arrow ... product)
        merged = False
        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                p, q = pieces[i], pieces[j]
                if min(p.y1, q.y1) - max(p.y0, q.y0) > 0.5 * min(p.height, q.height) and max(p.x0, q.x0) - min(p.x1, q.x1) < 40:
                    pieces[i] = p | q; pieces.pop(j); merged = True; break
            if merged: break
    stem = sorted([p + (-4, -4, 4, 4) for p in pieces], key=lambda o: (o.y0, o.x0))
    return dict(stem=stem, opts=opts, flags=flags)
