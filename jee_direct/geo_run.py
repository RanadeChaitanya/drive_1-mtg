"""Pictures for every question of the given pages, positions from the born-digital JSON (no OCR needed for this step).
python geo_run.py <pdf> <questions.json> <out.json> <figs_dir> <page> [<page> ...]"""
import json, sys
from pathlib import Path
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
from cet_figures import grow
import figs2

pdf, qj, out, figs = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); figs.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf); Q = json.load(open(qj, encoding="utf-8"))["questions"]; res = []
for pg in map(int, sys.argv[5:]):
    page = doc[pg - 1]; H = page.rect.height; qs = [q for q in Q if q["page"] == pg]
    for q in qs:
        nxt = [v["y0"] for v in qs if v["col"] == q["col"] and v["y0"] > q["y0"]]
        oth = [v["y0"] for v in qs if v["col"] != q["col"]]
        cont = min(oth) if (q["col"] == 0 and not nxt and oth) else None            # last question of the left column: options may continue on the right
        pic = figs2.pictures(page, q["col"], q["y0"] - 30, (min(nxt) + 30) if nxt else H - 24, cont, lo=q["y0"] - 8, hi=(min(nxt) - 8) if nxt else H)    # inline figures reach a little above the number row
        r = dict(qid=q["qid"], page=pg, number=q["number"], stem_images=[], option_images={}, flags=pic["flags"])
        for i, o in enumerate(pic["stem"]):
            p = figs / f"{q['qid']}_fig{i + 1}.png"; page.get_pixmap(dpi=200, clip=(o & page.rect)).save(p); r["stem_images"].append(p.name)
        for L, c in zip("ABCD", pic["opts"] or []):
            if c is None: continue
            p = figs / f"{q['qid']}_opt{L}.png"; page.get_pixmap(dpi=200, clip=(c & page.rect)).save(p); r["option_images"][L] = p.name
        res.append(r)
Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(res), "questions;", sum(bool(r["stem_images"] or r["option_images"]) for r in res), "with pictures;", sum(len(r["stem_images"]) + len(r["option_images"]) for r in res), "images")
