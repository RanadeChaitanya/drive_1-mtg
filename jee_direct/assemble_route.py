"""Old-pipeline route, final assembly: code structure + images (ocr_route.py) + cleaned text (model stage) + book key.
python assemble_route.py <route.json> <text.json> <direct.json> <out.json> qid_suffix ...
text.json: [{qid, stem, options}] from the extraction/check stages; direct.json supplies only the book's answer key."""
import json, re, sys

route = {r["qid"]: r for r in json.load(open(sys.argv[1], encoding="utf-8"))}
raw = open(sys.argv[2], "rb").read().decode("utf-8")
raw = re.sub(r'\\(?:["\\/]|u[0-9a-fA-F]{4})|\\', lambda m: m.group(0) if len(m.group(0)) > 1 else "\\\\", raw)   # \ce, \times are not JSON escapes
text = {r["qid"] if r["qid"].startswith("Copy") else "Copy_of_0dea66c2_" + r["qid"]: r for r in json.loads(raw)}
keys = {q["qid"]: q for q in json.load(open(sys.argv[3], encoding="utf-8"))["questions"]}
out = []
for suf in sys.argv[5:]:
    qid = "Copy_of_0dea66c2_" + suf; r, k = route[qid], keys.get(qid, {})
    t = text.get(qid) or dict(stem=k.get("stem", r["stem_raw"]), options=k.get("options", {}))      # no model-cleaned text for this one: fall back to the extracted text
    opts = {}
    for L in "ABCD":
        v = (t.get("options") or {}).get(L, "")
        opts[L] = "" if (L in r["option_images"] and "figure option" in v) else v          # a picture option carries no placeholder text
    out.append(dict(qid=qid, chapter=k.get("chapter", ""), stem=t["stem"], options=opts, option_images=r["option_images"], images=r["stem_images"],
                    correct_option=k.get("correct_option"), answer=k.get("answer"), flags=r["flags"], source="ocr_route"))
json.dump(dict(questions=out), open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "questions;", sum(len(q["option_images"]) for q in out), "option images")
