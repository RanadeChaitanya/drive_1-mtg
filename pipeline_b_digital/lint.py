"""KaTeX lint: python lint.py gen_a.json [...] -> lint.json {qid: [errors]} (renders every $..$ with throwOnError, via headless Chrome)."""
import json, subprocess, sys, os, re
g = {}
for f in sys.argv[1:]: g.update(json.load(open(f, encoding='utf-8')))
parts = {f"{q}|stem": v['stem_latex'] for q, v in g.items()}
parts.update({f"{q}|{k}": t for q, v in g.items() for k, t in v['options'].items() if t})
open('lint.html', 'w', encoding='utf-8').write("""<meta charset=utf-8><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js"></script><pre id=o></pre><script>
const P=%s,E={};for(const[k,t]of Object.entries(P)){const r=[];
if((t.match(/\\$/g)||[]).length%%2)r.push('unbalanced $');
for(const m of t.matchAll(/\\$([^$]+)\\$/g)){try{katex.renderToString(m[1],{throwOnError:true})}catch(e){r.push(m[1].slice(0,40)+' => '+e.message.slice(0,80))}}
if(/\\$/.test(t.replace(/\\$[^$]*\\$/g,'')))r.push('stray $');
if(r.length)E[k]=r}
document.getElementById('o').textContent=JSON.stringify(E)</script>""" % json.dumps(parts))
ch = [p for p in ("C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe") if os.path.exists(p)][0]
dom = subprocess.run([ch, '--headless', '--virtual-time-budget=10000', '--dump-dom', 'file:///D:/MSA/old_pipe_test/vision/lint.html'], capture_output=True, text=True, encoding='utf-8').stdout
E = json.loads(__import__('html').unescape(re.search(r'<pre id="o">(.*?)</pre>', dom, re.S).group(1)))
json.dump(E, open('lint.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(parts), 'strings;', len(E), 'with errors'); [print(k, v) for k, v in E.items()]
