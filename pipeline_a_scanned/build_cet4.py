import json, base64, html, subprocess, re, sys
from score import score, opts
e = html.escape
HAIKU_TOK = sys.argv[1] if len(sys.argv) > 1 else 'pending'
S = {i['qid']: i for i in json.load(open('sample_next.json', encoding='utf-8'))}
F = json.load(open('gemma4_fixed.json', encoding='utf-8')); G = json.load(open('gemma3_out.json', encoding='utf-8'))
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
analysis = """<section><h2>Run 4: Gemma 3 4B with enlarged halves + code checks, 26 questions (same configuration as before)</h2>
<h3>What was tried</h3><ul style="font:12px sans-serif"><li><b>Fix 1, enlarged crops:</b> each question sent as 3 images (whole crop + upper and lower halves at 2x) so small marks are easier to read.</li>
<li><b>Fix 2, two passes + compare:</b> run 3 (whole image, ~95 s/q) and run 4 (3 images, ~376 s/q) compared; a difference flags the question for review.</li>
<li><b>New code rules:</b> four identical options become [picture]; [figure] marker added when the OCR prints it (unless all four options are pictures).</li>
<li><b>Not done yet:</b> KaTeX lint + retry, pixel check for picture false alarms, second OCR vote; Haiku not re-run (no new figure questions in this batch).</li></ul>
<h3>Accuracy (26 of the 37 finished when this was cut; proxy = stem and all 4 options at >=95% similarity to the human-verified reference)</h3>
<table border=1 cellpadding=5 style="border-collapse:collapse;font:12px sans-serif"><tr><th>Run</th><th>Fully matching</th><th>Mean stem</th><th>Mean options</th><th>Sec/question</th></tr>
<tr><td>Run 3, whole image + repairs</td><td>21 of 26 (23 of 26 counting the two drawn-option questions, which the text scorer cannot credit)</td><td>0.993</td><td>0.918*</td><td>~95</td></tr>
<tr><td>Run 4, + enlarged halves</td><td>20 of 26 (22 of 26 effective)</td><td>0.986</td><td>0.910*</td><td>~376</td></tr></table>
<p style="font:11px sans-serif">*option mean is pulled down by the 2 drawn-option questions (scored 0 because the reference has no text for them). Effective accuracy on text-checkable questions: 23/26 = 88%. <b>Target 99% NOT reached.</b> The new code rules were written after seeing these same questions, so the figures are optimistic.</p>
<h3>Findings</h3><ul style="font:12px sans-serif"><li><b>Enlarged halves did not help.</b> 20 vs 21, four times slower. Gemma resizes every image to 896x896 itself, so enlarging a crop adds no real detail; the three persistent errors (mu_s subscript in Phy_q028, units tail in Che_q011, reagent conditions in Che_q008) were identical or worse.</li>
<li>Run 4 made new errors: Che_q009 option misread, Che_q008 'Ethane' for 'Ethene' (the OCR had it right), a lost [figure] marker. More images gave Gemma more room to drift.</li>
<li><b>Two-pass comparison</b> flagged 3 questions (Che_q018, Che_q008, Che_q009). It caught 1 true error (Che_q008), 1 drawn-options question (not an error), and 1 false alarm. It <b>missed</b> Phy_q028 and Che_q011 because both runs make the same mistake. Disagreement finds random slips, not systematic misreads.</li>
<li>Code rules fixed: Che_q018 (same fake picture copied into all four options) and the [figure] marker inconsistency.</li></ul>
<h3>Costing</h3><table border=1 cellpadding=5 style="border-collapse:collapse;font:12px sans-serif"><tr><th>Item</th><th>Tokens cost</th><th>Time</th></tr>
<tr><td>Gemma run 3 (local CPU), 26 questions</td><td>$0</td><td>~41 min</td></tr>
<tr><td>Gemma run 4 (local CPU), 26 questions</td><td>$0</td><td>~163 min</td></tr>
<tr><td>Code repairs, scoring</td><td>$0</td><td>seconds</td></tr>
<tr><td>Haiku pictures</td><td>$0 (not run)</td><td>-</td></tr>
<tr><td>Estimated for 1000 questions</td><td>$0 tokens</td><td>run 3: ~26 h; run 4: ~104 h; both: ~130 h on this CPU</td></tr></table>
<p style="font:11px sans-serif">Claude tokens used this round: small (script edits and checks only); no subagents, no Opus. Per-question pages show the run-4 output after repairs.</p></section>"""
pages = []
for q, f in F.items():
    sq = S[q]; img = base64.b64encode(open(sq['png'], 'rb').read()).decode(); hk = I.get(q) or {}; sv = hk.get('svgs') or {}
    ops = ''.join(f"<div class=o><b>({k})</b> {e(v)}{sv.get(k,'')}</div>" for k, v in f['options'].items())
    pic = ('Haiku pictures: ' + e('; '.join(x.get('where', '') + ' ' + x.get('type', '') for x in hk.get('figures', [])) + ' | faithful=' + str(hk.get('faithful')) + ' | ' + hk.get('note', ''))) if hk else ('picture flagged: ' + e('; '.join(f['why_picture'])) if f['picture_flag'] else 'no picture flagged: Haiku not used')
    pages.append(f"<section><h3>{q} ({sq['subject']}) [{sq['tag']}]</h3><div class=c><div><h4>Printed (scan)</h4><img src='data:image/png;base64,{img}'></div><div><h4>Gemma 3 4B text after code repair (stem {r[q][0]}, options {r[q][1]} {'OK' if r[q][2] else 'DIFFERS'})</h4><p>{e(f['stem_latex'])}</p>{sv.get('stem','')}{ops}<p class=u>Gemma asks: {e(f['asks'])}<br>{pic}</p></div></div></section>")
open('cet4.html', 'w', encoding='utf-8').write("<!doctype html><meta charset=utf-8><link rel=stylesheet href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js'></script><style>body{font:13px serif}section{page-break-after:always}.c{display:flex;gap:10px}.c>div{flex:1}img{width:100%}svg{max-width:220px;height:auto}.o{margin:3px 0}.u{font:10px sans-serif;color:#444}h4{font:10px sans-serif;margin:2px}</style><body>" + analysis + ''.join(pages) + "<script>renderMathInElement(document.body,{delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});</script>")
subprocess.run(["C:/Program Files/Google/Chrome/Application/chrome.exe", '--headless', '--virtual-time-budget=25000', '--no-pdf-header-footer', '--print-to-pdf=D:/MSA/out_sample1/cet_gemma_run4_26.pdf', 'file:///D:/MSA/old_pipe_test/vision/cet50/cet4.html'], capture_output=True)
import fitz; d = fitz.open('D:/MSA/out_sample1/cet_gemma_run4_26.pdf'); print(len(d), 'pages'); d[0].get_pixmap(dpi=55).save('cet4_p0.png')

