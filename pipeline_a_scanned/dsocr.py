"""deepseek-ocr (local ollama) as second OCR source. python dsocr.py qid... or 'all' -> dsocr_out.json (resumable)"""
import json, base64, time, urllib.request, sys, os
out = json.load(open('dsocr_out.json', encoding='utf-8')) if os.path.exists('dsocr_out.json') else {}
S = {i['qid']: i for i in json.load(open('sample_next.json', encoding='utf-8'))}
DIG = ['CHEMISTRY_2020_P01_Che_q032', 'CHEMISTRY_2020_P01_Che_q033', 'CHEMISTRY_2020_P01_Che_q034', 'CHEMISTRY_2020_P01_Che_q035', 'CHEMISTRY_2020_P01_Che_q036', 'CHEMISTRY_2020_P01_Che_q037', 'CHEMISTRY_2020_P01_Che_q038', 'CHEMISTRY_2020_P01_Che_q039', 'CHEMISTRY_2020_P01_Che_q040', 'CHEMISTRY_2020_P01_Che_q041', 'CHEMISTRY_2020_P01_Che_q042']
for q in DIG: S[q] = dict(png='D:/MSA/old_pipe_test/out3/agent_s6/%s.png' % q)
qs = list(S) if sys.argv[1:] == ['all'] else ['CET_PCB_2024_P01_' + a for a in sys.argv[1:]]
for q in qs:
    if q in out: continue
    img = base64.b64encode(open(S[q]['png'], 'rb').read()).decode(); t = time.time()
    body = json.dumps(dict(model='deepseek-ocr', stream=False, options=dict(temperature=0, num_predict=500), messages=[dict(role='user', content='Free OCR.', images=[img])])).encode()
    try: r = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', body), timeout=900))['message']['content']
    except Exception as e: r = 'ERR ' + str(e)[:100]
    out[q] = dict(text=r, sec=round(time.time() - t)); json.dump(out, open('dsocr_out.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(q[-8:], out[q]['sec'], 's', flush=True)
print('ALLDONE')
