import json,base64,html,subprocess,os
import re
g={}
for f in ('final.json',): g.update(json.load(open(f,encoding='utf-8')))
def ld(f):
    try: return json.load(open(f,encoding='utf-8'))
    except Exception: return {}
H,S=ld('chk6_haiku.json'),ld('chk6_sonnet.json')
def v(c,q):
    d=c.get(q)
    if not d: return 'n/a'
    return ('text ✓' if d.get('text_ok') else 'text ✗')+('' if d.get('figure_ok') is None else (' fig ✓' if d['figure_ok'] else ' fig ✗'))+(' — '+'; '.join(d.get('issues',[])) if d.get('issues') else '')
e=html.escape;out=[]
for q,x in g.items():
    img=base64.b64encode(open(q.startswith('CHEMISTRY') and f'D:/MSA/old_pipe_test/out3/agent_s6/{q}.png' or f'{q}.png','rb').read()).decode()
    STEM=re.sub(r'\$\$','$',re.sub(r'^\(\d+\)\s*','',x['stem_latex']))
    ops=''.join(f"<div class=o><b>({k})</b> {e(t) if t else ''}{x.get('option_svgs',{}).get(k,'')}</div>" for k,t in x['options'].items())
    out.append(f"<section><h3>{q}</h3><div class=c><div><h4>Printed</h4><img src='data:image/png;base64,{img}'></div><div><h4>Regenerated</h4><p>{e(STEM)}</p>{x.get('figure_img') or ''}{x.get('stem_svg') or ''}{ops}<p class=u>Context: {e(x.get('context') or '')}<br>Asks: {e(x.get('asked') or x.get('understanding') or '')}<br>Haiku proofread: {e('; '.join(x.get('haiku_diffs') or []) or 'matches print')}{' <b>(crop cut off: options not visible)</b>' if x.get('cut_off') else ''}</p></div></div><p class=v>{x.get('src','')} | {'Haiku: '+e(v(H,q))+' || Sonnet: '+e(v(S,q)) if q in H else ''}</p></section>")
open('r.html','w',encoding='utf-8').write("""<!doctype html><meta charset=utf-8><link rel=stylesheet href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css"><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js"></script><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<style>body{font:14px serif}section{page-break-after:always}.c{display:flex;gap:16px}.c>div{flex:1}img{width:100%}svg{max-width:260px;height:auto}.o{margin:4px 0}.u,.v{font:11px sans-serif;color:#444}h4{font:11px sans-serif;margin:2px}</style><body>"""+'''<section><h2>Costing (56 questions)</h2><table border=1 cellpadding=5 style="border-collapse:collapse;font:13px sans-serif"><tr><th>Stage</th><th>Model</th><th>Questions</th><th>Usage</th><th>Cost</th></tr>
<tr><td>A. understand-first draft from text layer</td><td>DeepSeek flash (v4-pro fallback)</td><td>56</td><td>78,490 in / 66,921 out (metered)</td><td>~$0.04 (est. at $0.14 in / $0.28 out per M; rates not verified)</td></tr>
<tr><td>B. proofread vs printed image</td><td>Haiku x4</td><td>56</td><td>329,586 tokens</td><td>~$0.05 ($0.16 per M blended)</td></tr>
<tr><td>C. hard cases (pictures, cut-off, unsure)</td><td>Sonnet x3</td><td>12 (21%)</td><td>188,770 tokens</td><td>~$0.60 ($3.2 per M blended)</td></tr>
<tr><td>D. independent final checks</td><td>Haiku + Sonnet</td><td>12</td><td>200,550 tokens (Haiku 79,478; Sonnet 67,903 + 53,169 recheck)</td><td>~$0.40</td></tr>
<tr><td><b>Total</b></td><td></td><td>56</td><td></td><td><b>~$1.09</b> (~$19 per 1,000 questions at this hard-case share)</td></tr></table>
<p style="font:12px sans-serif">Blend = 85% input / 15% output; Haiku $0.10/$0.50, Sonnet $2/$10 per M tokens. Token counts include image reads. No Opus. Sonnet only saw the 12 questions that had a picture, drawn options, a cut-off crop or an unresolved Haiku doubt.</p></section>'''+''.join(out)+"""<script>renderMathInElement(document.body,{delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});</script>""")
ch=[p for p in ("C:/Program Files/Google/Chrome/Application/chrome.exe","C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe") if os.path.exists(p)][0]
subprocess.run([ch,'--headless','--virtual-time-budget=15000','--no-pdf-header-footer','--print-to-pdf=D:/MSA/out_sample1/staged_deepseek_haiku_sonnet_chemistry2020.pdf','file:///D:/MSA/old_pipe_test/vision/r.html'])
