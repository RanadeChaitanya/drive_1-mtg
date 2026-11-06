"""Gemma 3 4B (local CPU) on scanned CET questions: image only -> understand-first JSON. Resumable. Output gemma_out.json"""
import json, base64, re, time, os, urllib.request
SYS = r"""You are a senior MHT-CET (Physics/Chemistry/Biology) teacher and a LaTeX typesetter. You see the scanned printed image of ONE multiple-choice question from a 2024 CET practice book (tails of the neighbouring questions or an answer key may appear at the edges: ignore them). Re-typeset it for a question bank.

Work in this order and fill the JSON fields in this order (thinking before typing):
1. context: subject and topic being tested (one line).
2. asked: in your own words, what the student must find (one sentence).
3. qtype: conceptual | numerical | reaction | match | assertion | statements | diagram | other.
4. picture_check: does the question contain a drawn figure (diagram, graph, circuit, apparatus, structure, scheme drawn with bond lines, table image)? List where: stem and/or which option letters. Plain text, numbers and formulas typed in a line are NOT pictures.
5. Only now type: stem_latex and options A-D exactly as printed (same words, numbers, units, printed typos), dropping the question number and the option boxes' letters. If an option is a picture set it to "" and list its letter in picture_options.
6. unsure: list anything you could not read with certainty (digits, signs, exponents, subscripts, Greek letters, arrows).

LaTeX rules (machine-linted with KaTeX + mhchem): every formula inside $...$ with balanced dollars; chemistry $\ce{CH3COOH}$ (no spaces inside a formula word), ions $\ce{SO4^{2-}}$; physics quantities with units $5\,\mathrm{m\,s^{-1}}$; powers and subscripts in braces; \times, \frac{a}{b}, \sqrt{x}, \propto, \Delta, \theta, \omega etc. by command; degrees $^\circ$; never Unicode superscripts or raw _ ^ outside math.

Return ONLY one JSON object with keys: context, asked, qtype, picture_check, stem_latex, options (A,B,C,D), picture_options (list of letters), has_picture (bool), unsure (list), needs_review (bool; true if you were unsure about anything or a picture exists)."""
S = json.load(open('sample50.json', encoding='utf-8'))
out = json.load(open('gemma_out.json', encoding='utf-8')) if os.path.exists('gemma_out.json') else {}
for it in S:
    q = it['qid']
    if q in out and 'err' not in out[q]: continue
    img = base64.b64encode(open(it['png'], 'rb').read()).decode()
    body = json.dumps(dict(model='gemma3:4b', stream=False, format='json', options=dict(temperature=0, num_ctx=4096, num_predict=1200), messages=[dict(role='system', content=SYS), dict(role='user', content='Question image:', images=[img])])).encode()
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', body), timeout=1200))
        d = json.loads(re.search(r'\{.*\}', r['message']['content'], re.S).group(0))
    except Exception as e: d = dict(err=str(e)[:100])
    d['_sec'] = round(time.time() - t); out[q] = d
    json.dump(out, open('gemma_out.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(q[-8:], d['_sec'], 's', (d.get('err') or d.get('context', ''))[:50], flush=True)
print('ALLDONE')
