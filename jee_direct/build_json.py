"""One final JSON per book: text + options + keys + pictures + per-picture verification + review queue.
python build_json.py <questions.json> <pictures.json> <verdicts_dir_or_files...> --out <book.json> [--book name]
questions.json : finalize/merge_checks output (text layer + Haiku/Sonnet fixes, flags)
pictures.json  : {qid: {stem_images:[..], option_images:{A:..}, rejected:[..], missing:[..]}}  (final crops after the box/judge rounds)
verdicts       : judge outputs [{qid, images:{name_or_letter: bool}, missing}]; an image is 'verified' only if EVERY judge file that saw it accepted it
Schema per question: qid, book, page, number, subject, chapter, section, type, stem, options{A..D}, option_images{}, stem_images[],
 correct_option | answer, key_status, pictures{status: none|verified|review}, flags[], review{needed, reasons[]}, source{}"""
import glob, json, re, sys
from pathlib import Path

args = sys.argv[1:]; out = args[args.index("--out") + 1]; book = args[args.index("--book") + 1] if "--book" in args else ""
files = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
qfile, pfile, verd = files[0], files[1], files[2:]
data = json.load(open(qfile, encoding="utf-8")); P = json.load(open(pfile, encoding="utf-8"))
votes = {}                                                         # (qid, image key) -> list of bool
for v in verd:
    for f in (glob.glob(v + "/*.json") if Path(v).is_dir() else [v]):
        for r in json.load(open(f, encoding="utf-8")):
            for k, ok in r["images"].items(): votes.setdefault((r["qid"], k), []).append(bool(ok))
res = []
for q in data["questions"]:
    p = P.get(q["qid"], {}); stem_imgs, opt_imgs = p.get("stem_images", []), p.get("option_images", {})
    keys = list(stem_imgs) + list(opt_imgs)                         # stem figures are keyed by file name, options by letter
    state = {k: votes.get((q["qid"], k), []) for k in keys}
    unver = [k for k, v in state.items() if not v or not all(v)]
    flags = sorted(set(q.get("flags", [])) - {"IMAGE_OPTIONS"})
    reasons = [f"picture {k} not accepted by every judge" for k in unver] + [f"missing picture: {m}" for m in p.get("missing", [])] + [f"flag {f}" for f in flags if f in ("NO_KEY", "KEY_DISPUTED", "KEY_UNVERIFIED", "KEY_NOT_LETTER") or f.startswith("OPTION_COUNT")]
    opts = {L: ("" if L in opt_imgs else v) for L, v in q["options"].items()}
    res.append(dict(qid=q["qid"], book=book, page=q["page"], number=q["number"], subject=q.get("subject", ""), chapter=q.get("chapter", ""), section=q.get("section", ""),
                    type="mcq" if q["options"] else "numeric", stem=q["stem"], options=opts, option_images=opt_imgs, stem_images=stem_imgs,
                    correct_option=q.get("correct_option"), answer=q.get("answer"),
                    key_status="missing" if not (q.get("correct_option") or q.get("answer")) else ("disputed" if "KEY_DISPUTED" in flags else "unverified" if "KEY_UNVERIFIED" in flags else "book"),
                    pictures=dict(status="none" if not keys else ("verified" if not unver else "review"), accepted=[k for k in keys if k not in unver], review=unver),
                    flags=flags, review=dict(needed=bool(reasons), reasons=reasons), source=dict(text="pdf text layer", edits=q.get("edits", []))))
Path(out).write_text(json.dumps(dict(book=book, questions=res), ensure_ascii=False, indent=1), encoding="utf-8")
n = len(res); pic = [r for r in res if r["pictures"]["status"] != "none"]
print(f"{n} questions | pictures: {len(pic)} questions, {sum(r['pictures']['status'] == 'verified' for r in pic)} fully verified | keyed {sum(r['key_status'] != 'missing' for r in res)} | review queue {sum(r['review']['needed'] for r in res)}")
