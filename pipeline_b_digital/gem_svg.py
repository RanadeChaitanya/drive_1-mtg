"""Gemma 3 4B only: crop of ONE drawn structure -> description -> atom/bond list -> SVG. Output gem_svg_out.json"""
import json, base64, re, time, urllib.request
SYS = """You are a chemist and SVG author. You see ONE cropped skeletal structure drawing (a single option from an exam question). Skeletal convention: every line end and every corner is a carbon atom; hydrogens on carbon are not drawn; labels like NO2 are drawn as text.
Work in this order and fill the JSON fields in this order:
1. look: describe only what you literally see: how many line segments, which way each goes (up-right, down-right, vertical-down...), where the corners are, what text label appears and at which end/corner.
2. atoms: list every atom as {"id":"C1","x":..,"y":..,"label":""} using a canvas of 200x200 px, standard zig-zag geometry: bond length 40, bond angles 120 degrees (so neighbouring atoms differ by dx=+-35, dy=+-20 for slanted bonds, dy=40 for vertical bonds). A heteroatom group like NO2 is its own atom with label "NO2" at the end of its bond.
3. bonds: list pairs ["C1","C2"] of atoms joined by a line.
4. svg: standalone SVG built ONLY from atoms and bonds: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200"><rect width="200" height="200" fill="white"/>` then one `<line x1= y1= x2= y2= stroke="black" stroke-width="2"/>` per bond (shorten a bond by 8 px at an end that has a text label so the line does not touch the text) and one `<text x= y= font-family="serif" font-size="18">NO<tspan dy="5" font-size="12">2</tspan></text>` per labelled atom, then `</svg>`.
5. name: the IUPAC name of the compound as drawn (carbons = corners and ends).
Example of the format (a DIFFERENT molecule: isobutanol skeleton, Y shape with OH below):
{"look":"three segments meeting at a centre point: two going up-left and up-right, one going straight down ending in the text OH","atoms":[{"id":"C1","x":65,"y":50,"label":""},{"id":"C2","x":100,"y":70,"label":""},{"id":"C3","x":135,"y":50,"label":""},{"id":"X","x":100,"y":125,"label":"OH"}],"bonds":[["C1","C2"],["C2","C3"],["C2","X"]],"svg":"<svg xmlns=\\"http://www.w3.org/2000/svg\\" viewBox=\\"0 0 200 200\\" width=\\"200\\" height=\\"200\\"><rect width=\\"200\\" height=\\"200\\" fill=\\"white\\"/><line x1=\\"65\\" y1=\\"50\\" x2=\\"100\\" y2=\\"70\\" stroke=\\"black\\" stroke-width=\\"2\\"/><line x1=\\"100\\" y1=\\"70\\" x2=\\"135\\" y2=\\"50\\" stroke=\\"black\\" stroke-width=\\"2\\"/><line x1=\\"100\\" y1=\\"70\\" x2=\\"100\\" y2=\\"108\\" stroke=\\"black\\" stroke-width=\\"2\\"/><text x=\\"90\\" y=\\"128\\" font-family=\\"serif\\" font-size=\\"18\\">OH</text></svg>","name":"2-propanol"}
Return ONLY one JSON object with keys look, atoms, bonds, svg, name."""
out = {}
for k, opt in enumerate('ABCD'):
    img = base64.b64encode(open(f'q42_img{k}.png', 'rb').read()).decode()
    body = json.dumps(dict(model='gemma3:4b', stream=False, format='json', options=dict(temperature=0, num_ctx=4096, num_predict=1500), messages=[dict(role='system', content=SYS), dict(role='user', content='Option ' + opt + ' crop:', images=[img])])).encode()
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/chat', body), timeout=900))
        d = json.loads(re.search(r'\{.*\}', r['message']['content'], re.S).group(0))
    except Exception as e: d = dict(err=str(e)[:100])
    d['_sec'] = round(time.time() - t); out[opt] = d; print(opt, d['_sec'], 's', d.get('name', d.get('err')), flush=True)
    json.dump(out, open('gem_svg_out.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
