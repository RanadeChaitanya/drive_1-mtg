import json,base64,html,subprocess,os
import re
g={}
for f in ('gen_final.json',): g.update(json.load(open(f,encoding='utf-8')))
def ld(f):
    try: return json.load(open(f,encoding='utf-8'))
    except Exception: return {}
H,S={},{}
def v(c,q):
    d=c.get(q)
    if not d: return 'n/a'
    return ('text ✓' if d.get('text_ok') else 'text ✗')+('' if d.get('figure_ok') is None else (' fig ✓' if d['figure_ok'] else ' fig ✗'))+(' — '+'; '.join(d.get('issues',[])) if d.get('issues') else '')
e=html.escape;out=[]
for q,x in g.items():
    img=base64.b64encode(open(q.startswith('CHEMISTRY') and f'D:/MSA/old_pipe_test/out3/agent_s6/{q}.png' or f'{q}.png','rb').read()).decode()
    STEM=re.sub(r'\$\$','$',re.sub(r'^\(\d+\)\s*','',x['stem_latex']))
    ops=''.join(f"<div class=o><b>({k})</b> {e(t) if t else ''}{x.get('option_svgs',{}).get(k,'')}</div>" for k,t in x['options'].items())
    out.append(f"<section><h3>{q}</h3><div class=c><div><h4>Printed</h4><img src='data:image/png;base64,{img}'></div><div><h4>Regenerated</h4><p>{e(STEM)}</p>{x.get('stem_svg') or ''}{ops}<p class=u>Understood: {e(x['understanding'])}</p></div></div><p class=v>{x.get('src','')} | embedded PDF image kept where the question has one</p></section>")
open('r.html','w',encoding='utf-8').write("""<!doctype html><meta charset=utf-8><link rel=stylesheet href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css"><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js"></script><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<style>body{font:14px serif}section{page-break-after:always}.c{display:flex;gap:16px}.c>div{flex:1}img{width:100%}svg{max-width:260px;height:auto}.o{margin:4px 0}.u,.v{font:11px sans-serif;color:#444}h4{font:11px sans-serif;margin:2px}</style><body>"""+'''<section><h2>Costing (this run, 56 questions)</h2><table border=1 cellpadding=5 style="border-collapse:collapse;font:13px sans-serif"><tr><th>Part</th><th>Questions</th><th>Usage</th><th>Cost</th></tr>
<tr><td>DeepSeek (text layer to LaTeX), deepseek-flash</td><td>56 (45 text-only + 11 later overwritten by Sonnet)</td><td>~56 calls + retries, ~1k in / 0.3k out each (estimated, not metered)</td><td>~$0.09 (est. at the old $0.0016 per question)</td></tr>
<tr><td>Sonnet agents (image questions only)</td><td>11</td><td>120,614 tokens (58,833 + 61,781) at the 85/15 input/output blend</td><td>~$0.39 ($3.2 per M blended; $0.035 per image question)</td></tr>
<tr><td>Haiku agents (started, then stopped by you before any output)</td><td>0</td><td>not reported</td><td>small, unmetered</td></tr>
<tr><td><b>Total</b></td><td>56</td><td></td><td><b>~$0.48</b>, i.e. ~$8.6 per 1,000 questions at this image share (20%)</td></tr></table>
<p style="font:12px sans-serif">Sonnet used on image-containing questions only (11 with an embedded PDF image). DeepSeek failed on 2 questions that have no embedded image (f90_q32, f88_q7): left as errors on purpose. No Opus. Not independently checked by Haiku/Sonnet reviewers.</p></section>'''+''.join(out)+"""<script>renderMathInElement(document.body,{delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});</script>""")
ch=[p for p in ("C:/Program Files/Google/Chrome/Application/chrome.exe","C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe") if os.path.exists(p)][0]
subprocess.run([ch,'--headless','--virtual-time-budget=15000','--no-pdf-header-footer','--print-to-pdf=D:/MSA/out_sample1/deepseek_text_sonnet_images_chemistry2020.pdf','file:///D:/MSA/old_pipe_test/vision/r.html'])
