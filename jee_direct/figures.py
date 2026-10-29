"""Crop the figures of each question (images + vector drawings inside the question's column/vertical range).
python figures.py <pdf> <questions.json> <out_dir>      adds q["images"] = [relative png paths]; rewrites the json"""
import json, re, sys
from pathlib import Path
import fitz

pdf, src, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf); data = json.loads(src.read_text(encoding="utf-8")); Q = data["questions"]
by = {}
for q in Q: by.setdefault((q["page"], q["col"]), []).append(q)
n = 0
for (pg, col), qs in by.items():
    page = doc[pg - 1]; W, H = page.rect.width, page.rect.height; qs.sort(key=lambda q: q["y0"])
    rects = [fitz.Rect(i["bbox"]) for i in page.get_image_info()] + [fitz.Rect(r) for r in page.cluster_drawings()]
    x_lo, x_hi = (0, W / 2) if col == 0 else (W / 2, W)
    rects = [r for r in rects if r.width > 25 and r.height > 20 and r.get_area() < 0.4 * W * H and r.y0 > 65 and r.y1 < H - 22 and x_lo - 5 <= (r.x0 + r.x1) / 2 <= x_hi + 5]
    import re
    rects = [r for r in rects if len(re.findall(r"\(\s*[a-dA-D]\s*\)", page.get_text(clip=r))) < 5 and "ANSWER KEY" not in page.get_text(clip=r + (0, -14, 0, 0))]   # answer-key grids are not figures
    for k, q in enumerate(qs):
        top, bot = q["y0"] - 2, (qs[k + 1]["y0"] - 2 if k + 1 < len(qs) else H - 22)
        mine = [r for r in rects if (r.y0 + r.y1) / 2 >= top and (r.y0 + r.y1) / 2 < bot]
        q["images"] = []
        reg = out.parent / "jee_regions"; reg.mkdir(exist_ok=True)               # the question as printed (for side-by-side checks)
        page.get_pixmap(dpi=130, clip=fitz.Rect(x_lo + 8, top, x_hi - 4, min(bot, H - 22))).save(reg / f"{q['qid']}.png")
        if mine:                                            # one crop covering the figure group, padded
            box = fitz.Rect(x_lo + 8, min(r.y0 for r in mine) - 30, x_hi - 4, max(r.y1 for r in mine) + 30)   # full column width: atom labels / (a)-(d) letters are text outside the drawing cluster
            ys = {L: [r.y0 for r in page.search_for(f"({L})", clip=fitz.Rect(x_lo, top, x_hi, bot))] for L in "abcd"}
            fy0, fy1 = min(r.y0 for r in mine), max(r.y1 for r in mine)
            inside = {L.upper() for L, v in ys.items() if any(fy0 - 6 <= y <= fy1 + 6 for y in v)}
            if q["options"] and "IMAGE_OPTIONS" not in q["flags"] and len(inside) >= 3:   # (a)-(d) sit inside the drawing: those options are pictures, their text is label debris
                q["option_text_original"] = q["options"]; q["options"] = {k: ("[figure option]" if k in inside and not re.match(r"(Both|Neither|None of)\b", v) else v) for k, v in q["options"].items()}; q["flags"].append("IMAGE_OPTIONS")   # an option printed below the drawing ('Both (a) and (b)') stays text
            png = out / f"{q['qid']}_fig1.png"; page.get_pixmap(dpi=200, clip=box & page.rect).save(png); q["images"].append(png.name); n += 1
src.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(n, "figures cropped;", sum(1 for q in Q if q["images"]), "questions with a figure")
