import json, base64, html, subprocess, re, sys
from score import score, opts
e = html.escape
HAIKU_TOK = sys.argv[1] if len(sys.argv) > 1 else 'pending'
S = {i['qid']: i for i in json.load(open('sample_next.json', encoding='utf-8'))}
F = json.load(open('gemma3_fixed.json', encoding='utf-8')); G = json.load(open('gemma3_out.json', encoding='utf-8'))
def L(f):
    try:
        b = open(f, 'rb').read()
        try: return json.loads(b.decode('utf-8'))
        except Exception: return json.loads(b.decode('cp1252'))
    except Exception: return {}
I = {}; I.update(L('i2_out.json')); [I.update(L(f'i_out_{i}.json')) for i in (0, 1)]       # new-30 pictures + earlier pictures for the retests
r = score(F, [S[q] for q in F])
def tally(tag): qs = [q for q in F if S[q]['tag'] == tag]; return len(qs), sum(r[q][2] for q in qs), sum(r[q][0] for q in qs) / len(qs), sum(r[q][1] for q in qs) / len(qs)
nr, okr, sr, orr = tally('retest'); nn, okn, sn, on = tally('new')
analysis = f"""<section><h2>Gemma errors found and fixed (next run on 30 new questions, same configuration)</h2>
<table border=1 cellpadding=5 style="border-collapse:collapse;font:12px sans-serif"><tr><th>Error type seen in the 47-question run</th><th>Example</th><th>Fix</th><th>Where</th></tr>
<tr><td>Invented content for drawn options (made-up LaTeX picture code or plausible formulas)</td><td>Che_q018, Che_q027</td><td>Prompt: write exactly [picture]; code: picture code in an option becomes [picture]</td><td>prompt + code</td></tr>
<tr><td>Options block repeated, glued onto option D</td><td>Bio_q029, Bio_q038</td><td>Parser keeps the first block only; stem cut at an inline (A)</td><td>code</td></tr>
<tr><td>First question sentence dropped; scheme species names copied from OCR instead of the A/B/C letters in the image</td><td>Che_q008</td><td>Prompt rule + first sentence recovered from OCR. Reagent conditions (Dry ether, UV light) NOT recovered</td><td>prompt + code (partial)</td></tr>
<tr><td>Word copied wrongly from OCR, not the image</td><td>'carbonl' for 'carbinol' (Che_q006)</td><td>Near-miss word replaced by the word used elsewhere in the same question</td><td>code</td></tr>
<tr><td>[figure] marker missing</td><td>Che_q046</td><td>Added when Gemma reports a picture in the stem</td><td>code</td></tr>
<tr><td>Options labelled (A) not A: so nothing parsed</td><td>Che_q023</td><td>Parser accepts A: (A) A. A)</td><td>code (found on the new 30)</td></tr>
<tr><td>Bracket note [R = the radius of the earth] dropped</td><td>Phy_q048</td><td>Recovered from OCR</td><td>code (found on the new 30)</td></tr>
<tr><td>Unicode subscripts (C₂H₅) instead of LaTeX</td><td>Che_q009</td><td>Converted to $\\ce{{C2H5}}$</td><td>code (found on the new 30)</td></tr>
<tr><td><b>Not fixed</b>: subscript lost in both OCR and Gemma (mu_s); reagent conditions over arrows; blank '______' and plural 'chains' misread</td><td>Phy_q028, Che_q008, Bio_q083</td><td>Needs better vision than a 4B model</td><td>-</td></tr></table>
<h3>Results</h3><table border=1 cellpadding=5 style="border-collapse:collapse;font:13px sans-serif"><tr><th>Set</th><th>Fully matching reference</th><th>Mean stem / options</th></tr>
<tr><td>Retest of the 7 earlier failures</td><td>{okr} of {nr} by the text scorer (+2 drawn-option questions now correctly marked [picture]) so 6 of 7 effectively right</td><td>{sr:.3f} / {orr:.3f}</td></tr>
<tr><td>30 NEW questions (not seen before)</td><td><b>{okn} of {nn}</b> after all repairs; 24 of 30 with only the repairs made BEFORE this sample (the last three rules were derived from errors in these same 30, so {okn}/{nn} is optimistic; 24/30 is the clean held-out number)</td><td>{sn:.3f} / {on:.3f}</td></tr>
<tr><td>Earlier run for comparison (47 questions)</td><td>37 of 44 finished at the time</td><td>0.976 / 0.945</td></tr></table>
<h3>Costing</h3><table border=1 cellpadding=5 style="border-collapse:collapse;font:13px sans-serif"><tr><th>Stage</th><th>Questions</th><th>Usage</th><th>Cost</th></tr>
<tr><td>Gemma 3 4B text (local CPU)</td><td>37</td><td>~75-150 s each</td><td>$0 tokens</td></tr>
<tr><td>Code repairs</td><td>37</td><td>none</td><td>$0</td></tr>
<tr><td>Haiku, pictures only (3 questions Gemma flagged among the new 30; earlier pictures reused for the retests)</td><td>3</td><td>{HAIKU_TOK}</td><td>~$0.01 (59,345 tokens x $0.16 per M)</td></tr></table>
<p style="font:12px sans-serif">Reference = human-verified Paper 1 v13. Match = text similarity after stripping LaTeX and punctuation, stem and all four options at >=95% (a proxy). No unused Paper 1 question has a labelled figure, so the new 30 contain few pictures. Haiku strictly pictures: it never saw or changed any text.</p></section>"""
pages = []
for q, f in F.items():
    sq = S[q]; img = base64.b64encode(open(sq['png'], 'rb').read()).decode(); hk = I.get(q) or {}; sv = hk.get('svgs') or {}
    ops = ''.join(f"<div class=o><b>({k})</b> {e(v)}{sv.get(k,'')}</div>" for k, v in f['options'].items())
    pic = ('Haiku pictures: ' + e('; '.join(x.get('where', '') + ' ' + x.get('type', '') for x in hk.get('figures', [])) + ' | faithful=' + str(hk.get('faithful')) + ' | ' + hk.get('note', ''))) if hk else ('picture flagged: ' + e('; '.join(f['why_picture'])) if f['picture_flag'] else 'no picture flagged: Haiku not used')
    pages.append(f"<section><h3>{q} ({sq['subject']}) [{sq['tag']}]</h3><div class=c><div><h4>Printed (scan)</h4><img src='data:image/png;base64,{img}'></div><div><h4>Gemma 3 4B text after code repair (stem {r[q][0]}, options {r[q][1]} {'OK' if r[q][2] else 'DIFFERS'})</h4><p>{e(f['stem_latex'])}</p>{sv.get('stem','')}{ops}<p class=u>Gemma asks: {e(f['asks'])}<br>{pic}</p></div></div></section>")
open('cet3.html', 'w', encoding='utf-8').write("<!doctype html><meta charset=utf-8><link rel=stylesheet href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js'></script><style>body{font:13px serif}section{page-break-after:always}.c{display:flex;gap:10px}.c>div{flex:1}img{width:100%}svg{max-width:220px;height:auto}.o{margin:3px 0}.u{font:10px sans-serif;color:#444}h4{font:10px sans-serif;margin:2px}</style><body>" + analysis + ''.join(pages) + "<script>renderMathInElement(document.body,{delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});</script>")
subprocess.run(["C:/Program Files/Google/Chrome/Application/chrome.exe", '--headless', '--virtual-time-budget=25000', '--no-pdf-header-footer', '--print-to-pdf=D:/MSA/out_sample1/cet_gemma_fixed_new30.pdf', 'file:///D:/MSA/old_pipe_test/vision/cet50/cet3.html'], capture_output=True)
import fitz; d = fitz.open('D:/MSA/out_sample1/cet_gemma_fixed_new30.pdf'); print(len(d), 'pages'); d[0].get_pixmap(dpi=55).save('cet3_p0.png')

