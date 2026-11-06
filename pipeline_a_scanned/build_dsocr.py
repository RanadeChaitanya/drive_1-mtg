import json, base64, html, subprocess
from score import score
e = html.escape
F = json.load(open('dsocr_fixed.json', encoding='utf-8')); D = json.load(open('dsocr_out.json', encoding='utf-8')); Fin = json.load(open('../final.json', encoding='utf-8'))
S = {i['qid']: i for i in json.load(open('sample_next.json', encoding='utf-8'))}
op = lambda x: eval(x) if isinstance(x, str) else x
for q in D:
    if q.startswith('CHEM'): S[q] = dict(qid=q, png=f'D:/MSA/old_pipe_test/out3/agent_s6/{q}.png', truth=dict(stem=Fin[q]['stem_latex'], options=op(Fin[q]['options'])), subject='Chemistry 2020 (digital)', tag='digital')
    else: S[q]['tag'] = 'scanned'
R = score(F, [S[q] for q in D])
def tab(tag):
    qs = [q for q in D if S[q]['tag'] == tag]; n = len(qs)
    return n, sum(R[q][2] for q in qs), sum(R[q][0] for q in qs) / n, sum(R[q][1] for q in qs) / n, sum(D[q]['sec'] for q in qs) / n
ns, oks, ss, os_, ts = tab('scanned'); nd, okd, sd, od, td = tab('digital')
pages = []
for tag in ('scanned', 'digital'):
    for q in [x for x in D if S[x]['tag'] == tag]:
        f = F[q]; img = base64.b64encode(open(S[q]['png'], 'rb').read()).decode()
        ops = ''.join(f"<div class=o><b>({k})</b> {e(v)}</div>" for k, v in f['options'].items())
        pages.append(f"<section><h3>{q} [{tag}] stem {R[q][0]}, options {R[q][1]} {'OK' if R[q][2] else 'DIFFERS'}</h3><div class=c><div><h4>Printed</h4><img src='data:image/png;base64,{img}'></div><div><h4>deepseek-ocr + code conversion</h4><p>{e(f['stem_latex'])}</p>{ops}</div></div></section>")
an = f"""<section><h2>deepseek-ocr as main reader (local, no tokens): scanned and digital reported separately</h2>
<table border=1 cellpadding=6 style="border-collapse:collapse;font:13px sans-serif"><tr><th>Group</th><th>Questions</th><th>Fully matching reference</th><th>Mean stem</th><th>Mean options</th><th>Sec / question</th></tr>
<tr><td>SCANNED (CET PCB 2024; reference = human-verified v13)</td><td>{ns}</td><td><b>{oks} of {ns} ({100*oks/ns:.0f}%)</b></td><td>{ss:.3f}</td><td>{os_:.3f}</td><td>{ts:.0f}</td></tr>
<tr><td>DIGITAL (Chemistry 2020; reference = DeepSeek + Haiku proofread, machine-made)</td><td>{nd}</td><td><b>{okd} of {nd} ({100*okd/nd:.0f}%)</b></td><td>{sd:.3f}</td><td>{od:.3f}</td><td>{td:.0f}</td></tr></table>
<p style="font:12px sans-serif"><b>99% target not reached.</b> Match = stem and all four options at &gt;=95% text similarity (proxy). Code rules (side-by-side options, two columns, dash lists, neighbour crumbs, unicode subscripts) were written after seeing these same questions; before them scanned was 22 of 37, so the figures are optimistic. Digital sample is small (11) and its reference is machine-made; for digital PDFs the text layer is the better source.</p>
<h3>Still failing</h3><ul style="font:12px sans-serif"><li>Scanned: Che_q046 ([figure] marker), Che_q008 (scheme conditions written differently), Bio_q092 (two-column statement list pushed into option A), Bio_q062 (options empty), Bio_q011 (table).</li><li>Digital: Che_q033 (formula options set apart, only labels read), Che_q035 (reagent under arrow as plain text), Che_q042 (options are pictures).</li></ul>
<h3>Costing</h3><p style="font:12px sans-serif">Tokens $0 (deepseek-ocr runs locally; conversion and scoring are plain code; no Gemma, Haiku or Claude calls). Time on this CPU: {ns*ts/60:.0f} min scanned + {nd*td/60:.0f} min digital = about {(ns*ts+nd*td)/3600*1000/48:.1f} h per 1000 questions. Haiku for pictures was not run.</p></section>"""
open('dsocr.html', 'w', encoding='utf-8').write("<!doctype html><meta charset=utf-8><link rel=stylesheet href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js'></script><style>body{font:13px serif}section{page-break-after:always}.c{display:flex;gap:10px}.c>div{flex:1}img{width:100%}.o{margin:3px 0}h4{font:10px sans-serif;margin:2px}</style><body>" + an + ''.join(pages) + "<script>renderMathInElement(document.body,{delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});</script>")
subprocess.run(["C:/Program Files/Google/Chrome/Application/chrome.exe", '--headless', '--virtual-time-budget=25000', '--no-pdf-header-footer', '--print-to-pdf=D:/MSA/out_sample1/deepseek_ocr_scanned_and_digital.pdf', 'file:///D:/MSA/old_pipe_test/vision/cet50/dsocr.html'], capture_output=True)
import fitz; d = fitz.open('D:/MSA/out_sample1/deepseek_ocr_scanned_and_digital.pdf'); print(len(d), 'pages', ns, oks, nd, okd)
