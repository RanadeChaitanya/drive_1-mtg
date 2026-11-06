"""Code-side repair of Gemma's raw output (no model calls). Rules from the run-2/run-3 error analysis.
python postproc.py  -> gemma3_fixed.json = {qid: {stem_latex, options, picture_flag, why_picture}}"""
import json, re, difflib, sys
BS = chr(92)
BAD = re.compile(r'\\begin\{picture\}|\\draw|\\includegraphics|\\begin\{tikz')
TEMPLATE = re.compile(r'letters of options that are drawn|kind \(circuit', re.I)

def parse_raw(t):
    t = re.split(r'\n(?=ASKS:)', t.strip())[0]                   # first block only
    d = {}
    lab = lambda L: rf'(?:\({L}\)|{L}[:.)])'                      # 'A:' or '(A)' or 'A.' or 'A)'
    m = re.search(rf'^STEM:\s*(.*?)(?=^\s*{lab("A")})', t, re.S | re.M); d['stem'] = m.group(1).strip() if m else ''
    d['options'] = {}
    for L, nxt in (('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', None)):
        pat = rf'^\s*{lab(L)}\s*(.*?)(?=^\s*{lab(nxt)})' if nxt else rf'^\s*{lab(L)}\s*(.*?)(?=^\s*(?:UNSURE:|{lab("A")}|{lab("B")}|{lab("C")})|\Z)'
        m = re.search(pat, t, re.S | re.M); d['options'][L] = m.group(1).strip() if m else ''
    for k in ('ASKS', 'PICTURE', 'UNSURE'):
        m = re.search(rf'^{k}:\s*(.*)$', t, re.M); d[k.lower()] = m.group(1).strip() if m else ''
    return d

def words(s): return re.findall(r"[A-Za-z]{4,}", s)

def fix_words(text, ocr_text):
    """replace a word the OCR text never contains by a close OCR word that Gemma's text lacks (carbonl -> carbinol)"""
    ow = {w.lower(): w for w in words(ocr_text)}; gw = {w.lower() for w in words(text)}
    for w in set(words(text)):
        if w.lower() in ow: continue
        cand = [(difflib.SequenceMatcher(None, w.lower(), o).ratio(), o) for o in ow if o not in gw]
        best = max(cand, default=(0, ''))
        if best[0] >= 0.85: text = re.sub(rf'\b{w}\b', ow[best[1]], text)
    return text

def first_sentence(s):
    m = re.match(r'\s*(.{15,}?[.?:])(?:\s|$)', s.replace('\n', ' ')); return m.group(1) if m else ''

def repair(raw, ocr):
    d = parse_raw(raw); pic = d['picture']; why = []
    # 1. option picture markers only when Gemma wrote them or wrote picture code
    for L in 'ABCD':
        if BAD.search(d['options'][L]): d['options'][L] = '[picture]'
    opt_pics0 = 0
    opt_pics = [L for L in 'ABCD' if d['options'][L].strip().lower().startswith('[picture')]
    # 2. options pasted into the stem: cut at the first inline (A)
    if re.search(r'\(A\)', d['stem']) and re.search(r'\(B\)', d['stem']): d['stem'] = re.split(r'\s*\(A\)', d['stem'])[0].strip()
    # 3. first question sentence dropped: recover from OCR
    ocr_stem = ocr.get('stem', '') or ''; s1 = first_sentence(ocr_stem)
    if s1 and '$' not in s1 and difflib.SequenceMatcher(None, d['stem'][:len(s1)].lower(), s1.lower()).ratio() < 0.6: d['stem'] = s1 + ' ' + d['stem']
    # 3b. trailing bracketed note present in the OCR stem but lost by Gemma ([R = the radius of the earth])
    m = re.search(r'(\[[^\[\]]{4,80}\])\s*$', ocr_stem.strip())
    if m and m.group(1) not in d['stem'] and m.group(1) != '[figure]': d['stem'] = d['stem'].rstrip() + ' ' + m.group(1)
    # 3a. all four options identical = Gemma copied one drawn option into every slot -> they are pictures
    ov = [v.strip() for v in d['options'].values()]
    if len(set(ov)) == 1 and ov[0] and not ov[0].startswith('['): d['options'] = {L: '[picture]' for L in 'ABCD'}
    # 3a2. [figure] marker: the OCR prints it reliably; add it unless all four options are pictures (then the picture is the options)
    if '[figure]' in ocr_stem and '[figure]' not in d['stem'] and not all(v.startswith('[picture') for v in d['options'].values()): d['stem'] = d['stem'].rstrip() + ' [figure]'
    # 3c. Unicode sub/superscripts -> LaTeX (prompt forbids them, Gemma still emits them)
    SUB = str.maketrans('₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789' * 2)
    def uni(v):
        if v.startswith('[') or '$' in v or not re.search('[₀-₉⁰-⁹]', v): return v
        return '$' + BS + 'ce{' + v.translate(SUB).replace('⁺', '+').replace('⁻', '-') + '}$'
    d['options'] = {k: uni(v) for k, v in d['options'].items()}
    # 4. word-level repair against OCR text
    ocr_all = ocr_stem + ' ' + ' '.join(str(v) for v in (ocr.get('options') or {}).values())
    d['stem'] = fix_words(d['stem'], ocr_all); d['options'] = {k: (v if v.startswith('[') else fix_words(v, ocr_all)) for k, v in d['options'].items()}
    # 4b. in-question consistency: a word seen once that is a near-miss of a word seen 2+ times in the same question (carbonl vs carbinol x3)
    allw = words(d['stem'] + ' ' + ' '.join(d['options'].values())); cnt = {}
    for w in allw: cnt[w.lower()] = cnt.get(w.lower(), 0) + 1
    common = [w for w, c in cnt.items() if c >= 2]
    def selfcons(text):
        for w in set(words(text)):
            best = max(((difflib.SequenceMatcher(None, w.lower(), c).ratio(), c) for c in common if cnt[c] > cnt.get(w.lower(), 0)), default=(0, ''))
            if best[0] >= 0.78 and best[1] != w.lower(): text = re.sub(rf'\b{w}\b', best[1].capitalize() if w[0].isupper() else best[1], text)
        return text
    d['stem'] = selfcons(d['stem']); d['options'] = {k: (v if v.startswith('[') else selfcons(v)) for k, v in d['options'].items()}
    # 5. picture flag for Haiku routing: Gemma's field (ignoring a copied template), [picture] options, or [figure] in stem
    stem_pic = bool(pic) and not re.match(r'\s*none', pic, re.I) and not TEMPLATE.search(pic) and re.search(r'stem|figure|diagram|circuit|graph|structure|table|scheme', pic, re.I)
    if stem_pic: why.append('PICTURE field: ' + pic[:40])
    if opt_pics: why.append('options drawn: ' + ','.join(opt_pics))
    if '[figure]' in d['stem']: why.append('[figure] in stem')
    if stem_pic and '[figure]' not in d['stem'] and len(opt_pics) < 4 and not re.search(r'\boptions?\b', pic, re.I): d['stem'] = d['stem'].rstrip() + ' [figure]'
    return dict(stem_latex=d['stem'].replace('\ufffd', "'"), options={k: v.replace('\ufffd', "'") for k, v in d['options'].items()}, picture_flag=bool(why), why_picture=why, asks=d['asks'], picture=pic)

if __name__ == '__main__':
    S = {i['qid']: i for i in json.load(open('sample_next.json', encoding='utf-8'))}; G = json.load(open(sys.argv[1] if len(sys.argv)>1 else 'gemma3_out.json', encoding='utf-8'))
    out = {q: repair(g['raw'], S[q]['ocr']) for q, g in G.items() if 'raw' in g}
    json.dump(out, open(sys.argv[2] if len(sys.argv)>2 else 'gemma3_fixed.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print(len(out), 'repaired')
