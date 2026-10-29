"""full extract json -> question pages only, with confident LLM fixes (fix/out_*.json) applied.
python finalize.py <full.json> <fix_dir> <out.json> [first last]"""
import glob, json, sys
src, fixd, out = sys.argv[1], sys.argv[2], sys.argv[3]; a, b = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (5, 106)
d = json.load(open(src, encoding="utf-8")); Q = [q for q in d["questions"] if a <= q["page"] <= b]
H = {r["qid"]: r for f in sorted(glob.glob(f"{fixd}/out_*.json")) for r in json.load(open(f, encoding="utf-8"))}
for q in Q:
    h = H.get(q["qid"])
    if not q["flags"] or not h: continue
    if h.get("is_question") is False: q["flags"].append("NOT_A_QUESTION"); continue
    if h.get("unsure"): continue
    if h.get("options") and len(h["options"]) == 4 and any(f.startswith("OPTION_COUNT") for f in q["flags"]):
        q["options"] = h["options"]; q["flags"] = [f for f in q["flags"] if not f.startswith("OPTION_COUNT")]; q["edits"].append("options by Haiku")
    ans = h.get("answer")
    if ans and "NO_KEY" in q["flags"]:
        if q["options"] and ans.upper() in "ABCD": q["correct_option"] = ans.upper()
        else: q["answer"] = ans
        q["flags"].remove("NO_KEY"); q["edits"].append("key by Haiku")
d["questions"] = [q for q in Q if "NOT_A_QUESTION" not in q["flags"]]; d["pages"] = [a, b]
json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(d["questions"]), "questions;", sum(bool(q["flags"]) for q in d["questions"]), "flagged")
