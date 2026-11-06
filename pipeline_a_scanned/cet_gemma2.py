"""Gemma 3 4B does ALL the text: image + older OCR text as a second source -> plain labelled output (no JSON, so LaTeX is not mangled). Resumable. Output gemma2_out.json"""
import json, base64, re, time, os, urllib.request
from PIL import Image
SYS = r"""You are a senior MHT-CET teacher typesetting ONE multiple-choice question from a scanned printed book. You get (1) the question IMAGE (truth) and (2) OCR_TEXT from an older OCR pass (often right, but it loses digits, signs, exponents, subscripts, fractions and Greek letters and can merge or drop words). Neighbouring questions or an answer key may show at the image edges: ignore them.

First understand, then type. Reply in EXACTLY this plain format, one field per line group, nothing else:
ASKS: <one sentence: what the student must find>
PICTURE: <none, or: stem / A,B,C,D (letters of options that are drawn pictures) + kind such as circuit, graph, structure, diagram, table>
STEM: <the full stem exactly as printed, without the question number>
A: <option A exactly as printed>
B: <option B>
C: <option C>
D: <option D>
UNSURE: <none, or list the tokens you could not read>

Rules:
- Read the image for every character; use OCR_TEXT only to settle words you cannot read, and where the two disagree on a number, sign or exponent trust the image.
- Keep printed wording, order and typos. Statements/lists (I, II, III or a, b, c) stay inside STEM, one per line.
- Mathematics in LaTeX inside single dollars, written with ordinary single backslashes: $\frac{mL^2}{3}$, $5\,\mathrm{m\,s^{-1}}$, $x^{2}$, $\sqrt{2}$, $\times$, $\Delta$, $\theta$, $^\circ$, $\vec{F}$, $\hat{i}$. Chemistry: $\ce{CH3COOH}$, $\ce{SO4^{2-}}$ (no spaces inside a formula word). Never Unicode superscripts; never leave a bare \ before a word.
- If an option is a picture, write A: [picture] (and list it in PICTURE); never describe it. If the stem refers to a figure, keep the sentence and add [figure] where it is printed.
- All four options A-D must appear; if the crop truly lacks one, write A: [not visible] for it.

Example: <omitted: example from a book, not published>
"""
S = [i for i in json.load(open('sample50.json', encoding='utf-8')) if Image.open(i['png']).size[1] < 1200]
out = json.load(open('gemma2_out.json', encoding='utf-8')) if os.path.exists('gemma2_out.json') else {}
def parse(t):
    d = {'raw': t}
    m = re.search(r'^STEM:\s*(.*?)(?=^\s*A:)', t, re.S | re.M); d['stem'] = m.group(1).strip() if m else ''
    d['options'] = {}
    for L, nxt in (('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', None)):
        pat = rf'^\s*{L}:\s*(.*?)(?=^\s*{nxt}:)' if nxt else rf'^\s*{L}:\s*(.*?)(?=^\s*UNSURE:|\Z)'
        m = re.search(pat, t, re.S | re.M); d['options'][L] = m.group(1).strip() if m else ''
    for k in ('ASKS', 'PICTURE', 'UNSURE'):
        m = re.search(rf'^{k}:\s*(.*)$', t, re.M); d[k.lower()] = m.group(1).strip() if m else ''
    return d
for it in S:
    q = it['qid']
    if q in out and 'err' not in out[q]: continue
    img = base64.b64encode(open(it['png'], 'rb').read()).decode()
    o = it['ocr']; ocr = (o['stem'] or '(none)') + '\n' + '\n'.join(f'{k}: {v}' for k, v in (o['options'] or {}).items())
    body = json.dumps(dict(model='gemma3:4b', stream=False, options=dict(temperature=0, num_ctx=4096, num_predict=700), messages=[dict(role='system', content=SYS), dict(role='user', content='OCR_TEXT:\n' + ocr, images=[img])])).encode()
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', body), timeout=1200)); d = parse(r['message']['content'])
    except Exception as e: d = dict(err=str(e)[:100])
    d['_sec'] = round(time.time() - t); out[q] = d
    json.dump(out, open('gemma2_out.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(q[-8:], d['_sec'], 's', 'opts', sum(bool(v) for v in d.get('options', {}).values()), '| picture:', d.get('picture', '')[:30], flush=True)
print('ALLDONE')
