"""Model-guided crop repair (the step that lifts picture accuracy from ~47% to ~98%).
  python repair_tools.py strips <pdf> <questions.json> <qid_list.json> <out_dir>      gridded page strips + worklists (in_N.json) for Sonnet 'box' agents
  python repair_tools.py crop   <pdf> <questions.json> <boxes.json> <out_dir>         crop the boxes the agent returned (absolute PDF points) -> worklist for the judge
Loop: code crops (geo_run.py) -> Sonnet judge -> failures -> strips (with judge reasons) -> Sonnet corrects boxes -> crop -> judge again (2-3 rounds)."""
import json, sys
from pathlib import Path
import fitz
from PIL import ImageDraw

mode, pdf, qj, third, out = sys.argv[1:6]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf); Q = {q["qid"]: q for q in json.load(open(qj, encoding="utf-8"))["questions"]}

if mode == "strips":
    items = []
    for qid in json.load(open(third, encoding="utf-8")):
        q = Q[qid]; page = doc[q["page"] - 1]; H, W = page.rect.height, page.rect.width
        nxt = [v["y0"] for v in Q.values() if v["page"] == q["page"] and v["col"] == q["col"] and v["y0"] > q["y0"]]
        y0 = max(q["y0"] - 35, 60); y1 = min((min(nxt) + 45) if nxt else H - 20, H)
        x0, x1 = (30, W / 2 + 50) if q["col"] == 0 else (W / 2 - 10, W - 4)
        regs = [(x0, y0, x1, y1)]
        if q["col"] == 0 and not nxt:                                   # options may continue at the head of the right column
            oth = [v["y0"] for v in Q.values() if v["page"] == q["page"] and v["col"] == 1]
            if oth: regs.append((W / 2 - 10, 62, W - 4, min(oth) + 10))
        pngs = []
        for k, (a, b, c, d) in enumerate(regs):
            im = page.get_pixmap(dpi=144, clip=fitz.Rect(a, b, c, d)).pil_image().convert("RGB"); dr = ImageDraw.Draw(im)
            for x in range(int(a // 20 + 1) * 20, int(c), 20): X = (x - a) * 2; dr.line([(X, 0), (X, im.height)], fill=(255, 150, 150)); dr.text((X + 2, 2), str(x), fill=(200, 0, 0))
            for y in range(int(b // 20 + 1) * 20, int(d), 20): Y = (y - b) * 2; dr.line([(0, Y), (im.width, Y)], fill=(150, 150, 255)); dr.text((2, Y + 1), str(y), fill=(0, 0, 200))
            p = out / f"{qid}_{k}.png"; im.save(p); pngs.append(dict(png=str(p), region_pt=[a, b, c, d]))
        items.append(dict(qid=qid, number=q["number"], regions=pngs))
    json.dump(items, open(out / "in_all.json", "w"), indent=0); print(len(items), "strips")
else:
    items = []
    for b in json.load(open(third, encoding="utf-8")):
        q = Q[b["qid"]]; page = doc[q["page"] - 1]

        def crop(box, name):
            r = fitz.Rect(box) & page.rect; p = out / f"{b['qid']}_{name}.png"; page.get_pixmap(dpi=200, clip=r).save(p); return str(p)
        items.append(dict(qid=b["qid"], number=q["number"], stem_figures=[crop(x, f"fig{k + 1}") for k, x in enumerate(b.get("stem_figures") or [])],
                          option_images={L: crop(x, f"opt{L}") for L, x in (b.get("options") or {}).items() if x}))
    json.dump(items, open(out / "judge_in.json", "w"), indent=0); print(len(items), "questions cropped")
