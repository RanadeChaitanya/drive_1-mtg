"""Patch: row-based ANSWER KEY grid parsing (cells split across spans: '(6.5x10' '-5)', merged '(a) 19', blank '( )')."""
from pathlib import Path

p = Path(__file__).with_name("extract.py"); s = p.read_text(encoding="utf-8")
if "PAIR_ROW" in s: raise SystemExit("already patched")
anchor = "    if grid:\n        state[\"grids\"].append(grid)"
add = '''    PAIR_ROW = re.compile(r"(?:\\s*\\d{1,3}\\s*\\([^()]{0,16}\\))+\\s*")                       # a row made ONLY of 'number (answer)' cells is an answer-key row
    rows_g = {}
    for l in lines: rows_g.setdefault(round(l["y1"] / 3), []).append(l)
    for ls in rows_g.values():
        ls.sort(key=lambda l: l["x0"]); t = " ".join(txt(l) for l in ls)
        pairs = re.findall(r"(\\d{1,3})\\s*\\(([^()]{0,16})\\)", t)
        if len(pairs) >= 2 and PAIR_ROW.fullmatch(t):
            for n_, v in pairs:
                v = v.strip().replace("\\u2013", "-").replace("\\u2212", "-").replace(" ", "")
                if v: grid[int(n_)] = v
            for l in ls: lines.remove(l)
'''
assert anchor in s
s = s.replace(anchor, add + anchor, 1)
p.write_text(s, encoding="utf-8"); print("patched")
