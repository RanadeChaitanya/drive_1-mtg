"""Free DeepSeek-OCR test on a few pages of a PDF (local Ollama). python ocr_test.py <pdf> <out_dir> 11 12 13"""
import base64, sys, time
from pathlib import Path
import fitz, httpx

pdf, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(pdf)
for n in map(int, sys.argv[3:]):
    png = out / f"page_{n:03d}.png"
    doc[n - 1].get_pixmap(dpi=150, colorspace=fitz.csGRAY).save(png)
    t = time.time()
    r = httpx.post("http://localhost:11434/api/generate", timeout=3600, json=dict(
        model="deepseek-ocr", prompt="<|grounding|>Convert the document to markdown.", stream=False,
        images=[base64.b64encode(png.read_bytes()).decode()], options=dict(temperature=0, repeat_penalty=1.1, num_predict=6000))).json()
    (out / f"page_{n:03d}.txt").write_text(r["response"], encoding="utf-8")
    print(f"page {n}: {time.time() - t:.0f}s, {len(r['response'])} chars", flush=True)
