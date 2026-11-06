"""Gemma as a router: does this question contain a science picture that needs a stronger vision model? Usage: python gem_route.py <qid>"""
import json, base64, re, sys, time, urllib.request
q = sys.argv[1]; a = json.load(open('gen_a.json', encoding='utf-8'))
png = f"D:/MSA/old_pipe_test/{'out3/agent_s6/' if q.startswith('CHEM') else 'vision/'}{q}.png"
img = base64.b64encode(open(png, 'rb').read()).decode()
SYS = """You are a careful routing judge in a chemistry question-bank pipeline. You see the PRINTED image of one exam question and the machine TEXT LAYER extracted from the same PDF region. The text layer contains only real text characters: it NEVER contains drawn pictures (structures, skeletal formulas, reaction schemes drawn with bond lines, graphs, apparatus, circuits, tables drawn as images). Your job: decide with explicit logic whether a stronger vision model (Sonnet) is needed to read a SCIENCE PICTURE and write SVG code for it.

Reason step by step and fill the JSON fields in this order:
1. printed_content: list, top to bottom, everything you see in the image for THIS question (stem, option boxes A-D, pictures). Name each picture and what scientific object it looks like (e.g. 'skeletal structure with a nitro group').
2. text_layer_content: list what the text layer actually contains for the stem and for each option letter (say 'letter only, no words' when an option has no text).
3. gap_analysis: compare 1 and 2. Which printed things are MISSING from the text layer? Option letters with empty text mean the option is a picture. Words like 'structure', 'following', 'identify' alone do not.
4. picture_type: one of none | structure | reaction_scheme | graph | apparatus | circuit | table | other.
5. where: stem | options | both | none (and which option letters).
6. needs_sonnet: true if ANY science picture exists that the text layer cannot carry; false only if everything printed is in the text layer.
7. why: one or two sentences of logic a reviewer can verify.
8. brief_for_sonnet: if true, 2-3 sentences telling the vision model exactly what to look at and what SVG to produce (which option letters, what kind of drawing); else empty.
Return ONLY the JSON object."""
body = json.dumps(dict(model='gemma3:4b', stream=False, format='json', options=dict(temperature=0, num_ctx=4096, num_predict=900), messages=[dict(role='system', content=SYS), dict(role='user', content='TEXT LAYER:\n' + a[q]['_text'], images=[img])])).encode()
t = time.time(); r = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', body), timeout=900))
d = json.loads(re.search(r'\{.*\}', r['message']['content'], re.S).group(0)); d['_sec'] = round(time.time() - t)
json.dump(d, open(f'route_{q}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print(json.dumps(d, ensure_ascii=False, indent=1))
