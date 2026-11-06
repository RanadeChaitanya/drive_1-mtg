"""Gemma 3 4B, v3: fixes for the 5 error types found in run 2. Input sample_next.json, output gemma3_out.json (resumable)."""
import json, base64, re, time, os, urllib.request
SYS = r"""You are a senior MHT-CET teacher typesetting ONE multiple-choice question from a scanned printed book. You get (1) the question IMAGE (truth) and (2) OCR_TEXT from an older OCR pass. The OCR is often right but it loses digits, signs, exponents, subscripts, fractions and Greek letters, merges or drops words, and when a picture is present it may invent text for it. Neighbouring questions or an answer key may show at the image edges: ignore them.

First understand, then type. Reply in EXACTLY this plain format, once, and then stop (never repeat the options):
ASKS: <one sentence: what the student must find>
PICTURE: <none, or: stem and/or the letters of options that are drawn pictures + kind (circuit, graph, structure, diagram, table)>
STEM: <the full stem exactly as printed, without the question number>
A: <option A exactly as printed>
B: <option B>
C: <option C>
D: <option D>
UNSURE: <none, or the tokens you could not read>

Rules:
- The image is the truth. Type every character you SEE, letter by letter. Do not auto-correct, modernise or complete words (print says 'carbinol' -> write 'carbinol'; print has a typo -> keep the typo). Use OCR_TEXT only to settle a word you cannot read.
- STEM must begin with the question sentence exactly as printed (e.g. 'Identify the product C formed in the following series of reactions.'). Never drop the first sentence, never put ASKS content into STEM. Statements/lists (I, II, III or a, b, c) stay inside STEM, one per line.
- NEVER describe or interpret a picture and never invent its content. If the stem refers to a figure/diagram, keep the printed words and put [figure] where the picture is printed. In a reaction scheme copy what is printed: single letters A, B, C on the chain are labels (write them as letters, not compound names) and keep conditions printed above/below arrows (dry ether, UV light, Delta, heat, catalysts).
- If an option is a picture (drawn structure, graph, circuit) write exactly [picture] for it (never a formula or name you guessed), and list its letter in PICTURE.
- Mathematics in LaTeX in single dollars with ordinary backslashes: $\frac{mL^2}{3}$, $5\,\mathrm{m\,s^{-1}}$, $x^{2}$, $\sqrt{2}$, $\times$, $\Delta$, $\theta$, $^\circ$, $\vec{F}$, $\hat{i}$. Chemistry $\ce{CH3COOH}$, $\ce{SO4^{2-}}$ (no spaces inside a formula word); reagents over an arrow: $\xrightarrow[\text{UV light}]{\ce{Br2}}$. Never Unicode superscripts.
- All four options A-D must appear once; if the crop lacks one write [not visible].

Example: <omitted: example from a book, not published>
"""
BAD = re.compile(r'\\begin\{picture\}|\\draw|\\includegraphics|\\begin\{tikz')
def parse(t):
    d = {'raw': t}
    t = re.split(r'\n(?=ASKS:)', t.strip())[0]            # first block only
    m = re.search(r'^STEM:\s*(.*?)(?=^\s*A:)', t, re.S | re.M); d['stem'] = m.group(1).strip() if m else ''
    d['options'] = {}
    for L, nxt in (('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', None)):
        pat = rf'^\s*{L}:\s*(.*?)(?=^\s*{nxt}:)' if nxt else rf'^\s*{L}:\s*(.*?)(?=^\s*(?:UNSURE|[ABC]):|\Z)'
        m = re.search(pat, t, re.S | re.M); d['options'][L] = m.group(1).strip() if m else ''
    for k in ('ASKS', 'PICTURE', 'UNSURE'):
        m = re.search(rf'^{k}:\s*(.*)$', t, re.M); d[k.lower()] = m.group(1).strip() if m else ''
    # code-side guards for the failure modes seen in run 2
    pic = d['picture']; letters = set()
    if pic and not re.match(r'\s*none', pic, re.I):
        m = re.match(r'\s*((?:[ABCD]\s*[,&and ]*\s*)+)', pic)
        letters = set(re.findall(r'[ABCD]', m.group(1))) if m else set()
        if re.search(r'\boptions?\b|\ball\b', pic, re.I) and not letters: letters = set('ABCD')
    for L in 'ABCD':
        if L in letters or BAD.search(d['options'][L]): d['options'][L] = '[picture]'
    if re.search(r'stem|figure|diagram|circuit|graph', d['picture'], re.I) and '[figure]' not in d['stem'] and letters != set('ABCD'): d['stem'] = d['stem'].rstrip() + ' [figure]'
    return d
S = json.load(open('sample_next.json', encoding='utf-8'))
out = json.load(open('gemma3_out.json', encoding='utf-8')) if os.path.exists('gemma3_out.json') else {}
for it in S:
    q = it['qid']
    if q in out and 'err' not in out[q]: continue
    img = base64.b64encode(open(it['png'], 'rb').read()).decode()
    o = it['ocr']; ocr = (o['stem'] or '(none)') + '\n' + '\n'.join(f'{k}: {v}' for k, v in (o['options'] or {}).items())
    body = json.dumps(dict(model='gemma3:4b', stream=False, options=dict(temperature=0, num_ctx=4096, num_predict=600, repeat_penalty=1.1), messages=[dict(role='system', content=SYS), dict(role='user', content='OCR_TEXT:\n' + ocr, images=[img])])).encode()
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', body), timeout=1200)); d = parse(r['message']['content'])
    except Exception as e: d = dict(err=str(e)[:100])
    d['_sec'] = round(time.time() - t); d['_tag'] = it['tag']; out[q] = d
    json.dump(out, open('gemma3_out.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(it['tag'], q[-8:], d['_sec'], 's', 'opts', sum(bool(v) for v in d.get('options', {}).values()), '| pic:', d.get('picture', '')[:25], flush=True)
print('ALLDONE')
