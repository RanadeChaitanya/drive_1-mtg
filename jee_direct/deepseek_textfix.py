"""DeepSeek text-fix (text only, no images): same worklists as the Haiku text-fix (text_fix_prep in_N.json) -> out_N.json with the same fields.
Key from the DEEPSEEK_API_KEY environment variable only.  python deepseek_textfix.py <tf_dir> <out_dir>"""
import glob, json, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY") or sys.exit("set DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com", timeout=300)
SYSTEM = ("You repair one JEE exam question extracted from a PDF text layer. Fix garbled symbols (stray accented letters that are really arrows, x, <=, Greek), "
          "split options that were merged into the stem or into each other, and fix leftover figure-label debris words. Formulas in LaTeX inside $...$ (chemistry as \\ce{...}). "
          "Never invent content; if unsure keep the text and set unsure true. Return JSON {\"changed\": bool, \"stem\": str, \"options\": {\"A\":..,\"B\":..,\"C\":..,\"D\":..} or {}, \"key\": null, \"unsure\": bool}.")
usage = [0, 0]


def one(it):
    r = client.chat.completions.create(model="deepseek-flash", response_format={"type": "json_object"}, max_tokens=2000, temperature=0, extra_body={"thinking": {"type": "disabled"}},
                                       messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(dict(stem=it["stem"], options=it["options"]), ensure_ascii=False)}])
    usage[0] += r.usage.prompt_tokens; usage[1] += r.usage.completion_tokens
    try: d = json.loads(r.choices[0].message.content)
    except Exception: d = {"changed": False, "unsure": True}
    return dict(qid=it["qid"], changed=bool(d.get("changed")), stem=d.get("stem", it["stem"]), options=d.get("options") or it["options"], key=None, unsure=bool(d.get("unsure")))


out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
for f in sorted(glob.glob(sys.argv[1] + "/in_[0-9]*.json")):
    items = json.load(open(f, encoding="utf-8"))
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(one, items))
    Path(out / f"out_{Path(f).stem.split('_')[1]}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("tokens in/out", usage)
