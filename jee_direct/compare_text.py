"""Text agreement between the direct route (PDF text layer) and the OCR route (DeepSeek-OCR) on the same questions.
python compare_text.py <direct.json> <ocr_route.json> <out_ids.txt> [max_cards]"""
import json, re, statistics, sys, difflib

D = json.load(open(sys.argv[1], encoding="utf-8"))["questions"]; O = json.load(open(sys.argv[2], encoding="utf-8"))
Dq = {q["qid"]: q for q in D}


def norm(t):
    t = re.sub(r"\\mathrm|\\ce|\\\(|\\\)|[${}\\]", "", (t or "").lower())
    return re.sub(r"[^a-z0-9]", "", t)


rows = []
for o in O:
    d = Dq.get(o["qid"])
    if not d: continue
    s = difflib.SequenceMatcher(None, norm(d["stem"]), norm(o["stem_raw"])).ratio()
    opt = [difflib.SequenceMatcher(None, norm(d["options"].get(L, "")), norm(o["options_raw"].get(L, ""))).ratio() for L in "ABCD" if d["options"].get(L) and o["options_raw"].get(L)]
    rows.append((o["qid"], s, sum(opt) / len(opt) if opt else None, bool(d["options"]), len(o["options_raw"])))
print("compared", len(rows), "| stem similarity mean", round(statistics.mean(r[1] for r in rows), 3), "| >=0.9:", sum(r[1] >= 0.9 for r in rows), "| <0.8:", sum(r[1] < 0.8 for r in rows))
ov = [r[2] for r in rows if r[2] is not None]
print("option sets compared", len(ov), "| mean similarity", round(statistics.mean(ov), 3), "| OCR found 4 text options for", sum(1 for r in rows if r[4] == 4), "of", sum(1 for r in rows if r[3]), "questions that have options")
n = int(sys.argv[4]) if len(sys.argv) > 4 else 26
ids = [r[0] for r in rows if (Dq[r[0]].get("stem_images") or Dq[r[0]].get("option_images") or r[1] < 0.8)][:n]
open(sys.argv[3], "w").write(" ".join(ids)); print(len(ids), "cards")
