"""Comparative PDF, one question per page: printed crop | old pipeline as-is (v4) | old pipeline + text-layer options (v5) | + Haiku-agent detector (v6)."""
import base64, json, sys

sys.path.insert(0, 'D:/MSA/old_pipe_test/final-pipeline/claude_pipeline'); sys.argv = ['cet_run.py', 'none', '1']
import cet_run as C
import fitz

OUT = C.OUT; g = json.load(open(OUT / 'final/paper_01_v6.json', encoding='utf-8'))
pdfs = {k: fitz.open(OUT / f'reconstructed/paper_01_{k}.pdf') for k in ('v4', 'v5', 'v6')}
where = {k: {q['qid']: n for n in range(len(d)) for q in g['questions'] if q['qid'] in d[n].get_text()} for k, d in pdfs.items()}
doc = fitz.open(); W, H = 842, 595; titles = ['Printed (source crop)', 'Old pipeline as-is', '+ options from the text layer', '+ Haiku-agent detector']
for i, q in enumerate(g['questions']):
    page = doc.new_page(width=W, height=H)
    page.insert_text((20, 22), f"{q['qid']}   (book question {q['number']}, page {q['page']})   verdict after all steps: {q['verdict']}", fontsize=11)
    cw = (W - 50) / 4; imgs = [base64.b64decode(C.crop_png(q, dpi=110, pad=15)[0])] + [pdfs[k][where[k][q['qid']]].get_pixmap(dpi=85, clip=fitz.Rect(0, 25, 595, 470)).tobytes('png') for k in ('v4', 'v5', 'v6')]
    for j, (t, im) in enumerate(zip(titles, imgs)):
        x = 10 + j * (cw + 10); page.insert_text((x, 44), t, fontsize=9)
        pm = fitz.Pixmap(im); r = fitz.Rect(x, 52, x + cw, 52 + (H - 70)); s = min(cw / pm.width, (H - 70) / pm.height)
        page.insert_image(fitz.Rect(x, 52, x + pm.width * s, 52 + pm.height * s), stream=im)
doc.save('D:/MSA/out_sample1/old_pipeline_comparison_page98.pdf'); print(len(doc), 'pages')
