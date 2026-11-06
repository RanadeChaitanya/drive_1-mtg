"""List question bands that contain short vector line segments (bond-like strokes): candidate figure questions."""
import re, fitz
d = fitz.open('D:/Copy of CHEMISTRY 2020.pdf'); hits = []
for pi, p in enumerate(d):
    W, H = p.rect.width, p.rect.height; segs = []
    for x in p.get_drawings():
        for it in x['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]; L = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** .5
                if 4 < L < 45 and 60 < a.y < H - 50: segs.append((a.x, a.y))
    for lo, hi in ((0, 297), (297, W)):
        ms = sorted((b[1], int(m.group(1))) for b in p.get_text('blocks') if (m := re.match(r'\((\d{1,3})\)', b[4].strip())) and lo <= b[0] < lo + 100)
        for k, (y, n) in enumerate(ms):
            y1 = ms[k + 1][0] if k + 1 < len(ms) else H - 45
            c = sum(1 for s in segs if lo <= s[0] < hi and y <= s[1] < y1)
            if c >= 5: hits.append((c, pi + 1, n))
hits.sort(reverse=True); print(len(hits), hits[:30])
