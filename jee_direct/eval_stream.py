"""python eval_stream.py <st_boxes.json> <ref_boxes.json> <verdicts.json> [tol]  - how many strict-Sonnet-accepted reference pictures does the stream box reproduce (every edge within tol pt)?"""
import collections, json, sys
import fitz

st = {b["qid"]: b for b in json.load(open(sys.argv[1]))}; ref = {b["qid"]: b for b in json.load(open(sys.argv[2]))}; V = json.load(open(sys.argv[3])); tol = float(sys.argv[4]) if len(sys.argv) > 4 else 8
close = lambda a, b: all(abs(x - y) <= tol for x, y in zip(a, b))
cat = collections.Counter(); ex = collections.defaultdict(list); extra = 0; tot = 0
for qid, j in V.items():
    s, r = st.get(qid), ref.get(qid)
    if not s or not r: continue
    refs = {f"fig{i + 1}": b for i, b in enumerate(r.get("stem_figures") or [])}; refs.update({L: b for L, b in (r.get("options") or {}).items() if b})
    got = {f"fig{i + 1}": b for i, b in enumerate(s.get("stem_figures") or [])}; got.update({L: b for L, b in (s.get("options") or {}).items() if b})
    extra += len(set(got) - set(refs)); tot += len(got)
    for k, ok in j["images"].items():
        key = k.replace(qid + "_", "").replace(".png", "")
        if not ok or key not in refs: continue
        g = got.get(key)
        if g is None: c = "no stream box"
        elif close(g, refs[key]): c = "match"
        else:
            R = fitz.Rect(refs[key]); G = fitz.Rect(g); i = (R & G).get_area(); c = "stream bigger" if i / R.get_area() >= .9 else "stream smaller" if i / max(G.get_area(), 1) >= .8 else "different"
        cat[c] += 1; ex[c].append((qid[-9:], key))
n = sum(cat.values())
print(f"{n} accepted refs: " + ", ".join(f"{c} {v}" for c, v in cat.most_common()) + f" | match {100 * cat['match'] / n:.1f}% | stream boxes {tot}, keys not in ref {extra}")
print({c: v[:5] for c, v in ex.items() if c != "match"})
