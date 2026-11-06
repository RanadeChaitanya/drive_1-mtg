"""DeepSeek run (text-only API): per question, PDF text layer of its band -> DeepSeek writes understanding + LaTeX; figure = vector SVG exported from the PDF band.
Key only from env NV_KEY. Output gen_nv.json (same schema as gen_*.json)."""
import fitz, re, json, os, urllib.request, concurrent.futures as cf
KEY = os.environ['NV_KEY']
doc = fitz.open('D:/Copy of CHEMISTRY 2020.pdf')
SRC = [json.load(open(f, encoding='utf-8')) for f in ('gen_all.json', 'gen2_0.json', 'gen2_1.json', 'gen2_2.json', 'gen3_all.json')]
qids = [q for g in SRC for q in g]


def where(q):
    if q.startswith('CHEMISTRY'): return 98, int(q[-3:])
    m = re.match(r'[pf](\d+)_q(\d+)', q); return int(m[1]), int(m[2])


def band(pg, n):
    p = doc[pg - 1]; W, H = p.rect.width, p.rect.height
    for lo, hi in ((0, 297), (297, W)):
        ms = sorted((b[1], int(m.group(1))) for b in p.get_text('blocks') if (m := re.match(r'\((\d{1,3})\)', b[4].strip())) and lo <= b[0] < lo + 100)
        for k, (y, num) in enumerate(ms):
            if num == n: return p, fitz.Rect(lo, max(y - 4, 0), hi, ms[k + 1][0] - 2 if k + 1 < len(ms) else H - 45)
    return None, None


def svg_of(p, r):
    ndraw = sum(1 for d in p.get_drawings() if d['rect'].intersects(r) and d['rect'].width < r.width * .9 and (d['rect'].width > 3 or d['rect'].height > 3))
    if ndraw < 25: return None  # shortcut: <25 vector pieces in the band = text-only question (option boxes are rects)
    old = p.cropbox; p.set_cropbox(r); s = p.get_svg_image(text_as_path=False); p.set_cropbox(old)
    return s


RULES = open('GEN_BRIEF.md', encoding='utf-8').read().split('3. If a stem picture')[0].split('Understand:')[1]
SYS = ("You convert one printed exam question to JSON. You get the text layer of its page band (reading order may be off; neighbouring question text/answer tables may appear: ignore them; Symbol-font glyph \\uf0b4 means ×). Steps: " + RULES +
       "\nReturn ONLY a JSON object {\"understanding\":str,\"stem_latex\":str,\"options\":{\"A\":..,\"B\":..,\"C\":..,\"D\":..}}; options a figure (empty text) -> \"\". Keep printed typos. No space inside \\ce{}.")


def ask(q):
    pg, n = where(q); p, r = band(pg, n)
    txt = p.get_text('text', clip=r)
    body = json.dumps(dict(model='nvidia/nemotron-3-ultra-550b-a55b', max_tokens=3000, temperature=0.2, chat_template_kwargs={'enable_thinking': False}, messages=[dict(role='system', content=SYS), dict(role='user', content=f'Question number {n}. Text layer:\n{txt}')])).encode()
    for _ in range(3):
        try:
            rq = urllib.request.Request('https://integrate.api.nvidia.com/v1/chat/completions', body, {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
            c = json.load(urllib.request.urlopen(rq, timeout=180))['choices'][0]['message']['content']; d = json.loads(re.search(r'\{.*\}', c, re.S).group(0)); break
        except Exception as e: d = dict(understanding='ERR ' + str(e)[:80], stem_latex='', options={})
    d.setdefault('options', {}); d['figure_description'] = ''; d['stem_svg'] = svg_of(p, r); d['option_svgs'] = {}
    return q, d


with cf.ThreadPoolExecutor(6) as ex: out = dict(ex.map(ask, qids))
json.dump(out, open('gen_nv.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'done;', sum(v['stem_svg'] is not None for v in out.values()), 'with exported figure;', sum(v['understanding'].startswith('ERR') for v in out.values()), 'errors')
