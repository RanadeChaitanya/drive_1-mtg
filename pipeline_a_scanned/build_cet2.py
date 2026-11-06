import json, base64, html, subprocess, re
from score import score, opts
e = html.escape
S = {i['qid']: i for i in json.load(open('sample50.json', encoding='utf-8'))}
F = json.load(open('g2_fix.json', encoding='utf-8')); G = json.load(open('g2_snap.json', encoding='utf-8'))
def L(f):
    try:
        b = open(f, 'rb').read()
        try: return json.loads(b.decode('utf-8'))
        except Exception: return json.loads(b.decode('cp1252'))
    except Exception: return {}
I = {}; [I.update(L(f'i_out_{i}.json')) for i in (0, 1)]
old = L('hh_all.json')  # earlier run: Gemma draft + Haiku full text backup
r = score(F, [S[q] for q in F]); ro = score({q: h['fixed'] for q, h in old.items()}, [S[q] for q in old if q in F])
pages = []
for q, f in F.items():
    img = base64.b64encode(open(S[q]['png'], 'rb').read()).decode(); sv = (I.get(q) or {}).get('svgs') or {}
    STEM = f['stem_latex']; ops = ''.join(f"<div class=o><b>({k})</b> {e(v)}{sv.get(k,'')}</div>" for k, v in f['options'].items())
    oldtxt = ('earlier run (Gemma + Haiku text backup): stem %s, options %s' % ro[q][:2]) if q in ro else 'not in earlier run'
    hk = I.get(q); note = ('Haiku pictures: ' + e('; '.join(x.get('where', '') + ' ' + x.get('type', '') for x in hk.get('figures', [])) + ' | faithful=' + str(hk.get('faithful')) + ' | ' + hk.get('note', ''))) if hk else ('Haiku not used' + (' (Gemma: no picture)' if q in G else ''))
    pages.append(f"<section><h3>{q} ({S[q]['subject']})</h3><div class=c><div><h4>Printed (scan)</h4><img src='data:image/png;base64,{img}'></div><div><h4>Gemma 3 4B text (match to reference: stem {r[q][0]}, options {r[q][1]} {'OK' if r[q][2] else 'DIFFERS'}); picture field: {e(G[q].get('picture',''))}</h4><p>{e(STEM)}</p>{sv.get('stem','')}{ops}<p class=u>Gemma asks: {e(G[q].get('asks',''))}<br>Gemma unsure: {e(G[q].get('unsure',''))}<br>{e(oldtxt)}<br>{note}</p>{(hk or {}).get('description') and '<p class=u>'+e(hk['description'][:400])+'</p>' or ''}</div></div></section>")
n = len(F); ok = sum(v[2] for v in r.values()); okold = sum(v[2] for v in ro.values())
cmp = f"""<section><h2>Gemma does all text; Haiku does pictures only</h2><table border=1 cellpadding=5 style="border-collapse:collapse;font:13px sans-serif"><tr><th></th><th>Earlier run (Gemma JSON draft + Haiku rewrites text)</th><th>This run (Gemma plain format + OCR hint; Haiku pictures only)</th></tr>
<tr><td>Text fully matching reference (stem and 4 options >=95%)</td><td>{okold} of {len(ro)} (after Haiku's text rewrite; Gemma alone: 1 of 31)</td><td><b>{ok} of {n}</b> (Gemma only, no text help from Haiku)</td></tr>
<tr><td>Mean stem / options similarity</td><td>{sum(v[0] for v in ro.values())/max(len(ro),1):.3f} / {sum(v[1] for v in ro.values())/max(len(ro),1):.3f}</td><td>{sum(v[0] for v in r.values())/n:.3f} / {sum(v[1] for v in r.values())/n:.3f}</td></tr>
<tr><td>Haiku used on</td><td>all 31 (text + pictures)</td><td>{len(I)} picture-flagged questions of {n} (pictures only)</td></tr>
<tr><td>Haiku tokens / cost</td><td>379,522 / ~$0.06</td><td>200,107 (115,195 + 84,912) / ~$0.03</td></tr></table>
<p style="font:12px sans-serif">Reference = human-verified Paper 1 v13. Match = text similarity after stripping LaTeX and punctuation (a proxy). Questions with drawn options (Che_q018, Che_q027, Che_q048) show low option scores because the options are pictures, not text. Gemma still running on the rest of the sample; this PDF covers the {n} finished.</p></section>"""
open('cet2.html', 'w', encoding='utf-8').write("<!doctype html><meta charset=utf-8><link rel=stylesheet href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js'></script><script src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js'></script><style>body{font:13px serif}section{page-break-after:always}.c{display:flex;gap:10px}.c>div{flex:1}img{width:100%}svg{max-width:220px;height:auto}.o{margin:3px 0}.u{font:10px sans-serif;color:#444}h4{font:10px sans-serif;margin:2px}</style><body>" + cmp + ''.join(pages) + "<script>renderMathInElement(document.body,{delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});</script>")
subprocess.run(["C:/Program Files/Google/Chrome/Application/chrome.exe", '--headless', '--virtual-time-budget=20000', '--no-pdf-header-footer', '--print-to-pdf=D:/MSA/out_sample1/cet_gemma_text_haiku_images_28.pdf', 'file:///D:/MSA/old_pipe_test/vision/cet50/cet2.html'], capture_output=True)
import fitz; d = fitz.open('D:/MSA/out_sample1/cet_gemma_text_haiku_images_28.pdf'); print(len(d), 'pages'); d[0].get_pixmap(dpi=60).save('cet2_p0.png'); d[8].get_pixmap(dpi=60).save('cet2_p8.png')
