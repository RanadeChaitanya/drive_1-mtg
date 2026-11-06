"""Stage A: DeepSeek, understand-first. Key only via env DEEPSEEK_API_KEY. Writes gen_a.json + usage in a_usage.json."""
import os, re, json, time, urllib.request, concurrent.futures as cf
src = open('ds_run.py', encoding='utf-8').read().split("RULES =")[0].replace("os.environ['NV_KEY']", "''")
exec(src)  # doc, qids, where, band, svg_of (embedded images)
KEY = os.environ['DEEPSEEK_API_KEY']

SYS = r"""You are a senior MHT-CET/JEE chemistry teacher and a LaTeX typesetter. You are re-typesetting ONE multiple-choice question from a printed 2020 MHT-CET chemistry chapter-wise book for a question bank.

WHAT YOU RECEIVE: the machine text layer of the page strip that holds the question. Its characters are reliable but: reading order is scrambled, the strip may include the tail of the previous question, the head of the next one, page headers ("Chemistry", chapter name, "[213]"), and answer-key tables. Symbol-font glyph  means the multiplication sign. Option boxes print as lone letters A B C D. You CANNOT see pictures: structures, schemes and graphs are not in your text. Never invent them.

METHOD - work in this order and fill the JSON fields in this order (thinking before typing is the point):
1. context: chapter/topic and the chemistry idea being tested (one line).
2. asked: in your own words, what the student must find (one sentence).
3. given: the data/conditions stated (list, may be empty).
4. qtype: one of conceptual | reaction-product | reaction-reagent | numerical | identify-compound | match | assertion | other.
5. Only now type: find this question's own stem and options in the noisy text (it starts at the printed number "(N)"), drop the number, and typeset.
6. sanity: does stem+options make sense as ONE coherent question (4 options, options answer what "asked" says)? If a piece is missing, cut off, or the text shows an option that is clearly a picture (empty/short fragments, "Y", "X", dangling arrows), say so; do not guess.

TYPESETTING RULES (output is machine-checked by KaTeX + mhchem):
- Keep the printed wording, order, numbers and printed typos exactly. Copy characters from the text layer; never retype numbers from memory.
- Every formula in $...$ with balanced dollars. Chemistry: $\ce{CH3COOH}$, ions $\ce{SO4^{2-}}$, arrows $\ce{->}$; reagent above arrow: $\xrightarrow{\ce{HNO3}}$ or $\ce{->[H2O][\Delta]}$ with NO nested dollars. No spaces inside a formula word ($\ce{CH3COCl}$ not $\ce{CH3 COCl}$); spaces only around + and arrows.
- Units \mathrm{g}, \mathrm{mol\,dm^{-3}}, \mathrm{kJ\,mol^{-1}}; powers/subscripts in braces; $^\circ$; \%; Greek by command;  -> \times; "10 -23" -> 10^{-23}; never Unicode super/subscripts; no raw _ ^ & # outside math.
- Option letters A-D are the boxed letters. If an option has no text in the layer it is a picture: set it to "" and list its letter in picture_options.

FEW-SHOT 1
LAYER: <omitted: example from a book, not published>
JSON: <omitted: example from a book, not published>

FEW-SHOT 2 (picture present, text layer holds only part)
LAYER: <omitted: example from a book, not published>
JSON: <omitted: example from a book, not published>

Return ONLY one JSON object with keys: context, asked, given, qtype, stem_latex, options (A-D), picture_options, has_picture, sanity, needs_review, note. needs_review=true whenever you inferred anything you could not read, an option is missing, or sanity is not "ok"."""


def ask(q):
    pg, n = where(q); p, r = band(pg, n)
    txt = p.get_text('text', clip=r).replace('', '\\uf0b4')
    use = None
    for model in ('deepseek-flash', 'deepseek-flash', 'deepseek-v4-pro'):
        body = json.dumps(dict(model=model, max_tokens=4000, temperature=0, response_format={'type': 'json_object'}, messages=[dict(role='system', content=SYS), dict(role='user', content=f'Question number {n}. TEXT LAYER of its page strip:\n{txt}')])).encode()
        try:
            rq = urllib.request.Request('https://api.deepseek.com/chat/completions', body, {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
            resp = json.load(urllib.request.urlopen(rq, timeout=180)); use = resp.get('usage')
            d = json.loads(resp['choices'][0]['message']['content']); d['model'] = model; break
        except Exception as e: d = dict(context='ERR ' + str(e)[:80]); time.sleep(5)
    d.setdefault('options', {}); d['_usage'] = use; d['_text'] = txt
    return q, d


with cf.ThreadPoolExecutor(6) as ex: out = dict(ex.map(ask, qids))
json.dump(out, open('gen_a.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ti = sum((v['_usage'] or {}).get('prompt_tokens', 0) for v in out.values()); to = sum((v['_usage'] or {}).get('completion_tokens', 0) for v in out.values())
print(len(out), 'done;', sum(v['context'].startswith('ERR') for v in out.values()), 'errors; tokens in/out', ti, to, '; needs_review', sum(bool(v.get('needs_review')) for v in out.values()))
