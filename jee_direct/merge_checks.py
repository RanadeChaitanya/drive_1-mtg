"""Apply the page-image checks. python merge_checks.py <questions.json> <fix2_dir>
B (outB.json): leftover options / keys read from the page images.  A (outA_*.json): figure questions checked against the print:
a corrected stem/options is accepted only if it is mostly the same words (label debris removed, small fixes), else flagged for the next attempt.
A book key that the checker thinks is wrong is never overwritten: it is flagged KEY_DISPUTED."""
import glob, json, re, sys
from pathlib import Path
src, d = Path(sys.argv[1]), sys.argv[2]
data = json.loads(src.read_text(encoding="utf-8")); M = {q["qid"]: q for q in data["questions"]}
words = lambda t: re.findall(r"[A-Za-z0-9]+", t or "")
def close(new, old):
    a, b = words(new), set(words(old)); return bool(a) and sum(w in b for w in a) / len(a) >= 0.85
n = dict(opt=0, key=0, stem=0, optfix=0, stem_rejected=0, disputed=0, fig_bad=0)
if Path(d, "outB.json").exists():
    for r in json.load(open(Path(d, "outB.json"), encoding="utf-8")):
        q = M[r["qid"]]
        if r.get("unsure"): continue
        if r.get("options") and len(r["options"]) == 4: q["options"] = r["options"]; q["flags"] = [f for f in q["flags"] if not f.startswith("OPTION_COUNT")]; n["opt"] += 1
        if r.get("answer") and "NO_KEY" in q["flags"]:
            a = str(r["answer"]); (q.__setitem__("correct_option", a.upper()) if q["options"] and a.upper() in "ABCD" else q.__setitem__("answer", a)); n["key"] += 1
        q["flags"] = [f for f in q["flags"] if f not in ("NO_KEY", "KEY_NOT_LETTER") or not (q["correct_option"] or q["answer"])]
for f in sorted(glob.glob(f"{d}/outA_*.json")):
    for r in json.load(open(f, encoding="utf-8")):
        q = M[r["qid"]]
        if r.get("text_ok") is False:
            cs, co = r.get("corrected_stem"), r.get("corrected_options")
            if cs and close(cs, q["stem"]) : q["stem"] = cs; n["stem"] += 1
            elif cs: q["flags"].append("STEM_CHECK"); n["stem_rejected"] += 1
            if co and "IMAGE_OPTIONS" not in q["flags"] and len(co) == 4 and all(close(v, q["options"].get(k, "")) for k, v in co.items()): q["options"] = co; n["optfix"] += 1
        if r.get("key_ok") is False and "KEY_DISPUTED" not in q["flags"]: q["flags"].append("KEY_DISPUTED"); q["key_note"] = r.get("issue", ""); n["disputed"] += 1
        if r.get("figure_ok") is False: q["flags"].append("FIGURE_CHECK"); n["fig_bad"] += 1
src.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"); print(n)

# ---- attempt 2 (out2_*.json): a transcription from the print. Accepted when it is not unsure and shares most words with the extracted text.
data = json.loads(src.read_text(encoding="utf-8")); M = {q["qid"]: q for q in data["questions"]}; m2 = dict(stem=0, opts=0, open=0)
def overlap(a, b):
    a, b = words(a), set(words(b)); return bool(a) and sum(w in b for w in a) / len(a)
for f in sorted(glob.glob(f"{d}/out2_*.json")):
    for r in json.load(open(f, encoding="utf-8")):
        q = M[r["qid"]]; ok = not r.get("unsure")
        if ok and r.get("stem") and overlap(r["stem"], q["stem"]) >= 0.8 and "not visible" not in r["stem"]: q["stem"] = r["stem"]; m2["stem"] += 1; q["flags"] = [x for x in q["flags"] if x != "STEM_CHECK"]
        o = r.get("options")
        if ok and o and len(o) == 4 and "IMAGE_OPTIONS" not in q["flags"] and not any("not visible" in str(v) for v in o.values()) and any(f.startswith("OPTION_COUNT") for f in q["flags"]):
            q["options"] = o; q["flags"] = [x for x in q["flags"] if not x.startswith("OPTION_COUNT")]; m2["opts"] += 1
        if r.get("figure_ok") is True: q["flags"] = [x for x in q["flags"] if x != "FIGURE_CHECK"]
        if r.get("key_ok") is True and "KEY_DISPUTED" in q["flags"]: q["flags"].remove("KEY_DISPUTED"); q["key_note"] = "confirmed by second reader"
        if r.get("key_ok") is False and "KEY_DISPUTED" not in q["flags"]: q["flags"].append("KEY_DISPUTED"); q["key_note"] = r.get("issue", "")
        if not (ok and r.get("figure_ok") is not False) : q.setdefault("open", True)
src.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"); print("attempt 2:", m2)

def rd(f):                                              # a helper agent saved one file in cp1252
    b = open(f, "rb").read()
    try: return json.loads(b.decode("utf-8"))
    except UnicodeDecodeError: return json.loads(b.decode("cp1252"))


# ---- attempt 3 (out3_*.json, Sonnet): final transcription accepted; book keys are never overwritten, only annotated
data = json.loads(src.read_text(encoding="utf-8")); M = {q["qid"]: q for q in data["questions"]}; m3 = dict(stem=0, opts=0, disputed=0, unverified=0, clipped=0)
for f in sorted(glob.glob(f"{d}/out3_*.json")):
    for r in rd(f):
        q = M[r["qid"]]; q.pop("open", None)
        if r.get("stem") and "not visible" not in r["stem"] and overlap(r["stem"], q["stem"]) >= 0.6 and r.get("figure_ok") is not False: q["stem"] = r["stem"]; m3["stem"] += 1
        o = r.get("options")
        if o and len(o) == 4 and "IMAGE_OPTIONS" not in q["flags"] and not any("not visible" in str(v) or "cut" in str(v) for v in o.values()) and r.get("figure_ok") is not False: q["options"] = o; m3["opts"] += 1
        q["flags"] = [x for x in q["flags"] if x not in ("STEM_CHECK", "FIGURE_CHECK", "KEY_DISPUTED")]
        if r.get("figure_ok") is False: q["flags"].append("FIGURE_CLIPPED"); q["figure_note"] = r.get("figure_issue", ""); m3["clipped"] += 1
        if r.get("agrees") is False: q["flags"].append("KEY_DISPUTED"); q["key_note"] = f"solver {r.get('solver_answer')} (conf {r.get('confidence')}): {r.get('note', '')}"; m3["disputed"] += 1
        elif r.get("agrees") is None: q["flags"].append("KEY_UNVERIFIED"); q["key_note"] = r.get("note", ""); m3["unverified"] += 1
for q in M.values():
    if q["correct_option"] or q["answer"]: q["flags"] = [x for x in q["flags"] if x not in ("NO_KEY", "KEY_NOT_LETTER")]
    q["flags"] = sorted(set(q["flags"]))
src.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"); print("attempt 3:", m3)
