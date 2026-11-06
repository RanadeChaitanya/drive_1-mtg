"""Gemma (local, Ollama) on the same 56 questions: image + text layer -> understand-first JSON (same schema as ds2). Output gen_gem_img.json + timing."""
import json, base64, time, re, urllib.request, sys
MODEL = sys.argv[1] if len(sys.argv) > 1 else 'gemma3:4b'
a = json.load(open('gen_a.json', encoding='utf-8'))  # reuse text layers (_text) and the same SYS prompt
src = open('ds2.py', encoding='utf-8').read(); SYS = src.split('SYS = r"""')[1].split('"""')[0]
SYS += "\nYou ALSO see the printed image of the question: use it for layout, options, pictures and to settle ambiguous characters; set has_picture/picture_options from what you see. Output ONLY the JSON object."
out = {}; t0 = time.time()
IMG = ['CHEMISTRY_2020_P01_Che_q042','p46_q53','p60_q49','p9_q47','p68_q81','p46_q51','p60_q46','p100_q54','p9_q48','p60_q47','p86_q52','f90_q29']
for q, v in [(q, a[q]) for q in IMG]:
    png = f"D:/MSA/old_pipe_test/{'out3/agent_s6/' if q.startswith('CHEM') else 'vision/'}{q}.png"
    img = base64.b64encode(open(png, 'rb').read()).decode()
    body = json.dumps(dict(model=MODEL, stream=False, format='json', options=dict(temperature=0, num_ctx=4096, num_predict=900), messages=[dict(role='system', content=SYS), dict(role='user', content='TEXT LAYER of the page strip:\n' + v['_text'], images=[img])])).encode()
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', body), timeout=900))
        d = json.loads(re.search(r'\{.*\}', r['message']['content'], re.S).group(0)); d['_tok'] = (r.get('prompt_eval_count'), r.get('eval_count'))
    except Exception as e: d = dict(context='ERR ' + str(e)[:80])
    d.setdefault('options', {}); d['_sec'] = round(time.time() - t); out[q] = d
    json.dump(out, open('gen_gem_img.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(q, d['_sec'], 's', d.get('context', '')[:50], flush=True)
print('total', round(time.time() - t0), 's')
