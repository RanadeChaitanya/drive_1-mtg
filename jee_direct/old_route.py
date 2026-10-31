"""The ORIGINAL pipeline's way, as-is, on JEE pages: OCR tags -> questions (split_options) -> figure crops from OCR image boxes grown to catch clipped labels (cet_figures.grow),
four option pictures in ONE OCR box split by whitespace gutters (cet_figures.split_box). No letter/pixel logic, no text-layer positions.
Only change: lowercase (a)-(d) are normalised to (A)-(D) because this book prints them that way.
python old_route.py <pdf> <ocr_dir> <out.json> <figs_dir> <page> ..."""
import json, sys
from pathlib import Path
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
from cet_figures import grow, split_box
from cet_options import split_options
from ocr_route import blocks, questions, upper_markers

pdf, ocr, out, figs = sys.argv[1], Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]); figs.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf); book = Path(pdf).stem; res = []
for pg in map(int, sys.argv[5:]):
    page = doc[pg - 1]; W, H = page.rect.width, page.rect.height; png = ocr / f"page_{pg:03d}.png"
    pr = lambda b: fitz.Rect(b[0] / 1000 * W, b[1] / 1000 * H, b[2] / 1000 * W, b[3] / 1000 * H)
    for q in questions(blocks((ocr / f"page_{pg:03d}.txt").read_text(encoding="utf-8")), pg):
        qid = f"{book}_p{pg:03d}_q{q['number']:03d}"; sp = split_options(upper_markers(q["text"]))
        r = dict(qid=qid, number=q["number"], page=pg, stem_raw=sp["stem"], options_raw=sp["options"], options_status=sp["status"], stem_images=[], option_images={}, flags=[])
        boxes = q["boxes"]; cells = None
        if boxes and sp["status"] != "ok" and len(boxes) == 1:         # the old rule: one OCR picture box holding all four option pictures
            s = split_box(png, boxes[0])
            if s: cells = s["cells"]
        if cells:
            for L, c in cells.items():
                p = figs / f"{qid}_opt{L}.png"; page.get_pixmap(dpi=200, clip=grow(page, pr(c))).save(p); r["option_images"][L] = p.name
        else:
            for i, b in enumerate(boxes):
                p = figs / f"{qid}_fig{i + 1}.png"; page.get_pixmap(dpi=200, clip=grow(page, pr(b))).save(p); r["stem_images"].append(p.name)
        if sp["status"] != "ok" and not r["option_images"]: r["flags"].append("OPTIONS_" + sp["status"].upper())
        res.append(r)
Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(res), "questions;", sum(bool(r["option_images"]) for r in res), "with option images")
