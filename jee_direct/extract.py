"""Direct extraction of born-digital question books (no OCR, no LLM): PDF text layer -> question JSON in the pipeline's schema.
python extract.py <pdf> <out.json> [first_page last_page]     pages are 1-based
Handles: two columns, running header/footer, section banners, 'N.' question numbers, (a)-(d) options, sub/superscripts from span size
and baseline (-> LaTeX), figures flagged by position. Anything it cannot place is flagged, never guessed."""
import json, re, sys
from collections import Counter
from pathlib import Path
import fitz

BANNER = re.compile(r"^(MCQs?\b.*|Numeric Value.*|Integer.*|Paragraph.*|Comprehension.*|Assertion.*|Match.*|Single Correct.*|Multiple Correct.*|Subjective.*|Solved Examples?.*|Exercise.*)$", re.I)
GREEK = {"α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta", "Δ": r"\Delta", "θ": r"\theta", "λ": r"\lambda", "μ": r"\mu", "ν": r"\nu", "π": r"\pi", "ρ": r"\rho",
         "σ": r"\sigma", "τ": r"\tau", "φ": r"\phi", "ω": r"\omega", "Ω": r"\Omega", "ε": r"\varepsilon", "×": r"\times", "°": r"^\circ", "≤": r"\leq", "≥": r"\geq", "≠": r"\neq", "≈": r"\approx", "→": r"\rightarrow"}


def script_text(t):
    return t.replace("–", "-").replace("−", "-").replace("—", "-").strip()


ELEMENTS = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th U Pu".split())


def is_formula(base, kind, content):
    """chemistry: element symbols + digit subscript or charge superscript -> mhchem; K_a, E_1 and the like stay maths"""
    if not re.fullmatch(r"(?:[A-Z][a-z]?)+", base) or not all(s in ELEMENTS for s in re.findall(r"[A-Z][a-z]?", base)):
        return False
    return bool(re.fullmatch(r"\d+", content)) if kind == "sub" else bool(re.fullmatch(r"\d*[+-]", content))


def math_token(base, kind, sup, chem=False):
    if chem and is_formula(base, kind, sup):
        return "$\\ce{" + base + (sup if kind == "sub" else "^{" + sup + "}" if len(sup) > 1 else sup) + "}$"
    b = base if len(base) == 1 or re.fullmatch(r"\d+(\.\d+)?", base) else r"\mathrm{" + base + "}"
    return "$" + b + ("^{" if kind == "sup" else "_{") + sup + "}$"


def row_text(spans, main, chem=False):
    """join the spans of one visual row into text; script spans become $base^{..}$ / $base_{..}$ attached to the preceding token"""
    base_y = sorted(s["origin"][1] for s in spans if s["size"] >= 0.88 * main)
    base_y = base_y[len(base_y) // 2] if base_y else None
    out = ""
    for s in sorted(spans, key=lambda s: s["bbox"][0]):
        t = s["text"]
        if base_y is not None and s["size"] < 0.88 * main and t.strip():
            kind = "sup" if s["origin"][1] < base_y - 1.2 else "sub" if s["origin"][1] > base_y + 1.2 else None
            if kind is None and re.search(r"_\{[^{}]*\}\$$", out):                    # 4d_{z^2}: a script riding on a subscript
                out = out[:-2] + "^{" + script_text(t) + "}}$"; continue
            if kind:
                m = re.search(r"([A-Za-z]+|\d+(?:\.\d+)?|[\)\]])$", out)
                base = m.group(1) if m else ""
                tok = math_token(base if base not in ")]" else base, kind, script_text(t), chem)
                if m and base not in ")]":
                    out = out[:m.start()] + tok
                else:
                    out += tok.replace("$", "$", 1) if not base else tok
                continue
        out += t
    return out


def clean(t):
    t = re.sub(r"\}\$\$\\ce\{", "", t)                                                   # $\ce{H2}$$\ce{SO4}$ -> $\ce{H2SO4}$
    t = re.sub(r"\$([^$]+)\$\s*/\s*\$([^$]+)\$", r"$\1/\2$", t)                       # E_2 / E_1 in one formula
    t = re.sub(r"(\d[\d.]*)\s*[×x]\s*\$10(\^\{[^}]*\})\$", r"$\1 \\times 10\2$", t)     # 3 x 10^{-5}
    for g, l in GREEK.items(): t = t.replace(g, " $" + l + "$ ")
    t = t.replace("�", "'").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace(" ", " ")
    return re.sub(r"[ \t]+", " ", t).strip()


def parse_page(page, state):
    d = page.get_text("dict"); W, H = page.rect.width, page.rect.height
    lines = []
    for b in d["blocks"]:
        for l in b.get("lines", []):
            sp = [s for s in l["spans"] if s["text"].strip() or s["text"]]
            if sp: lines.append(dict(spans=sp, x0=l["bbox"][0], y0=l["bbox"][1], x1=l["bbox"][2], y1=l["bbox"][3]))
    sizes = Counter(round(s["size"], 1) for l in lines for s in l["spans"] if len(s["text"].strip()) > 3)
    main = sizes.most_common(1)[0][0] if sizes else 10.0
    big_images = [fitz.Rect(i["bbox"]) for i in page.get_image_info() if fitz.Rect(i["bbox"]).get_area() > 0.4 * W * H]
    txt = lambda l: "".join(s["text"] for s in l["spans"]).strip()
    grid = {}
    for a in [l for l in lines if re.fullmatch(r"\d{1,3}", txt(l))]:                  # ANSWER KEY grid: '12' followed on the same baseline by '(b)' or '(731)'
        b = next((c for c in lines if re.fullmatch(r"\(\s*[a-dA-D\d.\-–, ]+\)", txt(c)) and abs(c["y1"] - a["y1"]) < 3 and 0 < c["x0"] - a["x1"] < 40), None)
        if b: grid[int(txt(a))] = txt(b).strip("() ").replace("–", "-"); lines.remove(a); lines.remove(b)
    if grid:
        state["grids"].append(grid); state["keys"].setdefault(state.get("seg", 0), {}).update(grid)
    header = [l for l in lines if l["y1"] < 70 or l["y0"] > H - 22]
    body = [l for l in lines if l not in header]
    for l in header:
        t = "".join(s["text"] for s in l["spans"]).strip()
        if t and not t.isdigit() and "CHEMISTRY PHYSICS MATHEMATICS".find(t.upper()) < 0: state["chapter"] = t
        if t.upper() in ("CHEMISTRY", "PHYSICS", "MATHEMATICS"): state["subject"] = t.title()
    mid = W / 2
    rows = []
    for col in (0, 1):
        cl = [l for l in body if (l["x0"] < mid - 4) == (col == 0) and not (l["x1"] - l["x0"] > 0.75 * W)]
        cl.sort(key=lambda l: (l["y0"], l["x0"]))
        for l in cl:                                       # merge lines on the same baseline (number + first text line, option letter + text)
            by = max((s for s in l["spans"]), key=lambda s: s["size"])["origin"][1]
            if rows and rows[-1]["col"] == col and abs(rows[-1]["by"] - by) < 2.6:
                rows[-1]["spans"] += l["spans"]; rows[-1]["y1"] = max(rows[-1]["y1"], l["y1"]); rows[-1]["x0"] = min(rows[-1]["x0"], l["x0"])
            else:
                rows.append(dict(col=col, by=by, spans=list(l["spans"]), x0=l["x0"], y0=l["y0"], y1=l["y1"]))
    qs, cur = state["qs"], state["cur"]
    for r in rows:
        spans = sorted(r["spans"], key=lambda s: s["bbox"][0]); raw = "".join(s["text"] for s in spans).strip()
        m = re.match(r"^(\d{1,3})\.\s*(.*)$", raw)
        if m:
            num = int(m.group(1)); prev = state.get("prev", 0)
            if not ((num == 1 and (prev == 0 or prev >= 5)) or prev < num <= prev + 3 or state.get("fresh")):          # '5.' ending a wrapped stem line is text, not a new question
                m = None
        if m and (spans[0]["flags"] & 16 or len(raw) <= 4 or r["x0"] < (mid if r["col"] == 0 else W) * 0.35 + (0 if r["col"] == 0 else mid)):
            state["prev"], state["fresh"] = num, False
            if num == 1: state["seg"] = state.get("seg", 0) + 1                              # each chapter exercise restarts at 1; its ANSWER KEY grid lands in the same segment
            rest = row_text(spans, main, state["subject"] == "Chemistry"); rest = re.sub(r"^\s*\d{1,3}\.\s*", "", rest)
            cur = dict(seg=state.get("seg", 0), gi=len(state["grids"]), number=num, page=page.number + 1, section=state["section"], chapter=state["chapter"], subject=state["subject"], stem=clean(rest), options={}, y0=r["y0"], col=r["col"], flags=[])
            qs.append(cur); state["last"] = "stem"; continue
        if BANNER.match(raw) and len(raw) < 60:
            state["section"] = raw; state["fresh"] = True; cur = None; continue
        if cur is None: continue
        t = clean(row_text(spans, main, state["subject"] == "Chemistry")); mo = re.match(r"^\(([a-dA-D])\)\s*(.*)$", t)
        if mo:                                              # several options can share one row: (a) x (b) y
            nxt, cuts = mo.group(1).upper(), []                              # accept (a),(b),(c),(d) only in order, so '(d)' inside option text is not a split
            for m2 in re.finditer(r"\(([a-dA-D])\)\s*", t):
                if m2.group(1).upper() == nxt: cuts.append((m2.group(1).upper(), m2.start(), m2.end())); nxt = chr(ord(nxt) + 1)
            for k, (L, a0, a1) in enumerate(cuts):
                cur["options"][L] = t[a1:cuts[k + 1][1] if k + 1 < len(cuts) else None].strip(); state["last"] = L
        elif state["last"] == "stem":
            cur["stem"] += " " + t
        else:
            cur["options"][state["last"]] = (cur["options"].get(state["last"], "") + " " + t).strip()
    for q in qs:                                            # figures: an image/drawing cluster inside the question's vertical range
        if q["page"] == page.number + 1 and "ymax" not in q: q["ymax"] = H
    state["cur"] = cur
    state["images"][page.number + 1] = [list(map(round, i["bbox"])) for i in page.get_image_info() if fitz.Rect(i["bbox"]).get_area() <= 0.4 * W * H]


def main():
    pdf, out = sys.argv[1], sys.argv[2]
    doc = fitz.open(pdf); a, b = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1, len(doc))
    state = dict(qs=[], cur=None, section="", chapter="", subject="", last="stem", images={}, grids=[], keys={})
    for n in range(a, b + 1): parse_page(doc[n - 1], state)
    book = Path(pdf).stem; res = []
    for q in state["qs"]:
        q["stem"] = re.sub(r"\s+([,.;:?])", r"\1", q["stem"]).strip(); fl = q["flags"]
        if q["options"] and len(q["options"]) != 4: fl.append("OPTION_COUNT_" + str(len(q["options"])))
        if "�" in q["stem"] or any("�" in v for v in q["options"].values()): fl.append("BAD_CHAR")
        ans = state["keys"].get(q["seg"], {}).get(q["number"]) or (state["grids"][q["gi"]] if q["gi"] < len(state["grids"]) else {}).get(q["number"])
        if ans is None: fl.append("NO_KEY")
        elif q["options"] and ans.lower() not in "abcd": fl.append("KEY_NOT_LETTER")
        res.append(dict(y0=round(q["y0"]), col=q["col"], qid=f"{book}_p{q['page']:03d}_q{q['number']:03d}", number=q["number"], page=q["page"], subject=q["subject"], chapter=q["chapter"], section=q["section"],
                        stem=q["stem"], options=q["options"], correct_option=ans.upper() if ans and q["options"] and ans.lower() in "abcd" else None, answer=ans if ans and not q["options"] else None, flags=fl, edits=[], source="text_layer"))
    Path(out).write_text(json.dumps(dict(source_pdf=pdf, pages=[a, b], questions=res), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(res)} questions from pages {a}-{b}; with options {sum(bool(q['options']) for q in res)}; flagged {sum(bool(q['flags']) for q in res)}")


if __name__ == "__main__":
    main()
