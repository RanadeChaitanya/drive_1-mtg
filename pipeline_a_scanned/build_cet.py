import json, base64, html, subprocess, re
from score import score, opts
e = html.escape
S = json.load(open('sample50.json', encoding='utf-8')); Sd = {i['qid']: i for i in S}
H = json.load(open('hh_all.json', encoding='utf-8')); G = json.load(open('gemma_snap.json', encoding='utf-8'))
rh = score({q: h['fixed'] for q, h in H.items()}, [Sd[q] for q in H]); rg = score({q: g for q, g in G.items() if 'err' not in g and q in H}, [Sd[q] for q in H])
def O(d): return ''.join(f"<div class=o><b>({k})</b> {e(str(v))}</div>" for k, v in opts(d).items())
pages = []
for q, h in H.items():
    g = G.get(q, {}); img = base64.b64encode(open(Sd[q]['png'], 'rb').read()).decode(); sv = h.get('svgs') or {}
    fo = h['fixed']; fops = ''.join(f"<div class=o><b>({k})</b> {e(str(v))}{sv.get(k,'')}</div>" for k, v in opts(fo).items())
    STEM = re.sub(r'^\(\d+\)\s*', '', fo['stem_latex'])
    ok = '✓ matches reference' if rh[q][2] else '✗ differs from reference'
    pages.append(f"<section><h3>{q} ({Sd[q]['subject']})</h3><div class=c><div><h4>Printed (scan)</h4><img src='data:image/png;base64,{img}'></div><div><h4>Gemma 3 4B draft (similarity to reference: stem {rg.get(q,(0,0))[0]}, options {rg.get(q,(0,0))[1]})</h4><p class=g>{e(str(g.get('stem_latex','(none)'))[:500])}</p><p class=g>{e(str(g.get('options',''))[:300])}</p></div><div><h4>After Haiku backup (stem {rh[q][0]}, options {rh[q][1]}): {ok}</h4><p>{e(STEM)}</p>{sv.get('stem','')}{fops}<p class=u>Haiku read: {e(h['read'])}<br>Fixes: {e('; '.join(h['diffs'])[:300] or 'none')}</p></div></div></section>")
cost = """<section><h2>Costing and what ran</h2><table border=1 cellpadding=5 style="border-collapse:collapse;font:13px sans-serif"><tr><th>Stage</th><th>Questions</th><th>Usage</th><th>Cost</th></tr>
<tr><td>Gemma 3 4B, local CPU (image only, scan has no text layer)</td><td>33 of 50 run (rest still running)</td><td>~80-100 s each</td><td>$0 (electricity)</td></tr>
<tr><td>Haiku backup x4 agents (all had to run: Gemma options never usable)</td><td>31</td><td>96,490 + 101,443 + 98,860 + 82,729 = 379,522 tokens</td><td>~$0.06 ($0.16 per M blended)</td></tr>
<tr><td><b>Total</b></td><td>31</td><td></td><td><b>~$0.06</b> (~$1.9 per 1,000 questions)</td></tr></table>
<p style="font:12px sans-serif">Reference = human-verified Paper 1 v13 JSON; 'matches' = stem and all four options at >=95% similarity after stripping LaTeX/punctuation (a proxy, not an exact check). 2 questions with whole-page crops (Phy_q005, Bio_q095) held out. Haiku was NOT used 'only when necessary': the code rule flagged every question because Gemma's options were unusable.</p></section>"""
open('cet.html', 'w', encoding='utf-8').write("<!doctype html><meta charset=utf-8><link rel=stylesheet href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js'></script><style>body{font:13px serif}section{page-break-after:always}.c{display:flex;gap:10px}.c>div{flex:1}img{width:100%}svg{max-width:200px;height:auto}.o{margin:3px 0}.u{font:10px sans-serif;color:#444}.g{font:10px monospace;color:#900;word-break:break-all}h4{font:10px sans-serif;margin:2px}</style><body>" + cost + ''.join(pages) + "<script>renderMathInElement(document.body,{delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});</script>")
subprocess.run(["C:/Program Files/Google/Chrome/Application/chrome.exe", '--headless', '--virtual-time-budget=20000', '--no-pdf-header-footer', '--print-to-pdf=D:/MSA/out_sample1/cet_gemma_haiku_31.pdf', 'file:///D:/MSA/old_pipe_test/vision/cet50/cet.html'], capture_output=True)
import fitz; d = fitz.open('D:/MSA/out_sample1/cet_gemma_haiku_31.pdf'); print(len(d), 'pages'); d[3].get_pixmap(dpi=60).save('cet_pg.png')
