"""Apply the Haiku text-fix outputs (tf_dir/out_*.json) to a questions json.
Rules: stem/options replaced from the print reading; a key is only FILLED when it was empty (a book key is never overwritten, a disagreement is flagged);
unsure -> flag TEXT_UNSURE; every edit recorded in q['edits'].
python merge_textfix.py <questions.json> <tf_dir> <out.json>"""
import glob, json, re, sys
from pathlib import Path


def rd(f):
    raw = Path(f).read_bytes().decode("utf-8")
    raw = re.sub(r'\\(?:["\\/]|u[0-9a-fA-F]{4})|\\', lambda m: m.group(0) if len(m.group(0)) > 1 else "\\\\", raw)   # \ce, \times are not JSON escapes
    return json.loads(raw)


data = json.load(open(sys.argv[1], encoding="utf-8")); Q = {q["qid"]: q for q in data["questions"]}
n = dict(changed=0, unsure=0, key_filled=0, key_disagree=0, missing=0)
for f in sorted(glob.glob(sys.argv[2] + "/out_*.json")):
    for r in rd(f):
        q = Q.get(r["qid"])
        if q is None: n["missing"] += 1; continue
        if r.get("changed"):
            q["stem"] = r["stem"]
            if isinstance(r.get("options"), dict): q["options"] = {k.upper(): v for k, v in r["options"].items()}
            q["edits"].append("text by Haiku"); n["changed"] += 1
        k = r.get("key"); have = q.get("correct_option") or q.get("answer")
        if k not in (None, "") and not have:
            ks = str(k).strip()
            if q["options"] and ks.upper() in list("ABCDEFGH"): q["correct_option"] = ks.upper()
            else: q["answer"] = ks
            q["edits"].append("key from print by Haiku"); n["key_filled"] += 1
        elif k not in (None, "") and have and str(k).strip().upper() != str(have).strip().upper(): q["flags"].append("KEY_DISAGREE_READER"); n["key_disagree"] += 1
        if r.get("unsure"): q["flags"].append("TEXT_UNSURE"); n["unsure"] += 1
        q["flags"] = sorted({f for f in q["flags"] if not f.startswith("OPTION_COUNT") or len(q["options"]) not in (0, 4)} - ({"NO_KEY"} if (q.get("correct_option") or q.get("answer")) else set()))
Path(sys.argv[3]).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"); print(n)
