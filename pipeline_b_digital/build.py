import json,base64,html,subprocess,os
g=json.load(open('gen_all.json',encoding='utf-8'))
def ld(f):
    try: return json.load(open(f,encoding='utf-8'))
    except Exception: return {}
H,S=ld('chk_haiku.json'),ld('chk_sonnet.json')
def v(c,q):
    d=c.get(q)
    if not d: return 'n/a'
    return ('text ✓' if d.get('text_ok') else 'text ✗')+('' if d.get('figure_ok') is None else (' fig ✓' if d['figure_ok'] else ' fig ✗'))+(' — '+'; '.join(d.get('issues',[])) if d.get('issues') else '')
e=html.escape;out=[]
for q,x in g.items():
    img=base64.b64encode(open(f'D:/MSA/old_pipe_test/out3/agent_s6/{q}.png','rb').read()).decode()
    ops=''.join(f"<div class=o><b>({k})</b> {e(t) if t else ''}{x.get('option_svgs',{}).get(k,'')}</div>" for k,t in x['options'].items())
    out.append(f"<section><h3>{q[-4:]}</h3><div class=c><div><h4>Printed</h4><img src='data:image/png;base64,{img}'></div><div><h4>Regenerated (vision-first)</h4><p>{e(x['stem_latex'])}</p>{x.get('stem_svg') or ''}{ops}<p class=u>Understood: {e(x['understanding'])}</p></div></div><p class=v>Haiku: {e(v(H,q))}<br>Sonnet: {e(v(S,q))}</p></section>")
open('r.html','w',encoding='utf-8').write("""<meta charset=utf-8><link rel=stylesheet href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css"><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js"></script><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<style>body{font:14px serif}section{page-break-after:always}.c{display:flex;gap:16px}.c>div{flex:1}img{width:100%}svg{max-width:260px;height:auto}.o{margin:4px 0}.u,.v{font:11px sans-serif;color:#444}h4{font:11px sans-serif;margin:2px}</style><body>"""+''.join(out)+"""<script>renderMathInElement(document.body,{delimiters:[{left:'$',right:'$',display:false}]});</script>""")
ch=[p for p in ("C:/Program Files/Google/Chrome/Application/chrome.exe","C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe") if os.path.exists(p)][0]
subprocess.run([ch,'--headless','--virtual-time-budget=15000','--no-pdf-header-footer','--print-to-pdf=D:/MSA/out_sample1/vision_first_chemistry2020.pdf','file:///D:/MSA/old_pipe_test/vision/r.html'])
