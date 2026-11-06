"""DeepSeek run (text-only API): per question, PDF text layer of its band -> DeepSeek writes understanding + LaTeX; figure = vector SVG exported from the PDF band.
Key only from env DEEPSEEK_API_KEY. Output gen_ds.json (same schema as gen_*.json)."""
import fitz, re, json, os, urllib.request, concurrent.futures as cf
KEY = os.environ['DEEPSEEK_API_KEY']
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
    """Figure = union of embedded raster images inside the band (this book draws structures as images), rendered from the page; returns an <img> tag."""
    import base64
    rs = [fitz.Rect(x['bbox']) for x in p.get_image_info() if fitz.Rect(x['bbox']).intersects(r) and fitz.Rect(x['bbox']).width > 12 and fitz.Rect(x['bbox']).height > 12]
    rs = [x & r for x in rs]
    if not rs: return None
    u = rs[0]
    for x in rs[1:]: u |= x
    return '<img style="max-width:280px" src="data:image/png;base64,' + base64.b64encode(p.get_pixmap(dpi=150, clip=u + (-3, -3, 3, 3)).tobytes('png')).decode() + '">'


RULES = open('GEN_BRIEF.md', encoding='utf-8').read().split('3. If a stem picture')[0].split('Understand:')[1]
SYS = ("You convert one printed exam question to JSON. You get the text layer of its page band (reading order may be off; neighbouring question text/answer tables may appear: ignore them; Symbol-font glyph \\uf0b4 means ×). Steps: " + RULES +
       "\nReturn ONLY a JSON object {\"understanding\":str,\"stem_latex\":str,\"options\":{\"A\":..,\"B\":..,\"C\":..,\"D\":..}}; options a figure (empty text) -> \"\". Keep printed typos. No space inside \\ce{}.")


def ask(q):
    pg, n = where(q); p, r = band(pg, n)
    txt = p.get_text('text', clip=r)
    body = json.dumps(dict(model='deepseek-flash', max_tokens=4000, response_format={'type': 'json_object'}, messages=[dict(role='system', content=SYS), dict(role='user', content=f'Question number {n}. Text layer:\n{txt}')])).encode()
    for _ in range(3):
        try:
            rq = urllib.request.Request('https://api.deepseek.com/chat/completions', body, {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
            d = json.loads(json.load(urllib.request.urlopen(rq, timeout=120))['choices'][0]['message']['content']); break
        except Exception as e: d = dict(understanding='ERR ' + str(e)[:80], stem_latex='', options={})
    d.setdefault('options', {}); d['figure_description'] = ''; d['stem_svg'] = svg_of(p, r); d['option_svgs'] = {}
    return q, d


prev = json.load(open('gen_ds.json', encoding='utf-8')) if os.path.exists('gen_ds.json') else {}
todo = [q for q in qids if q not in prev or prev[q]['understanding'].startswith('ERR') or True]
with cf.ThreadPoolExecutor(6) as ex: out = dict(ex.map(ask, [q for q in todo if q not in prev or prev[q]['understanding'].startswith('ERR')]))
for q in qids: out.setdefault(q, prev[q]); out[q]['stem_svg'] = svg_of(*band(*where(q)))
json.dump(out, open('gen_ds.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'done;', sum(v['stem_svg'] is not None for v in out.values()), 'with exported figure;', sum(v['understanding'].startswith('ERR') for v in out.values()), 'errors')
