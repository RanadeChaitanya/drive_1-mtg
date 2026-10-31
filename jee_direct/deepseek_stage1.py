"""Old-pipeline stage 1 with the REAL DeepSeek API (same client settings as claude_pipeline/cet_run.ask_deepseek: deepseek-flash, JSON mode, thinking off).
Reads only the OCR text of each page. The key comes from the DEEPSEEK_API_KEY environment variable and is never written to a file.
python deepseek_stage1.py <old_in.json> <out.json>"""
import json, os, sys
from pathlib import Path
from openai import OpenAI

key = os.environ.get("DEEPSEEK_API_KEY") or sys.exit("set DEEPSEEK_API_KEY")
client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=900)
SYSTEM = ("You extract one exam question from layout-tagged OCR text of a JEE chemistry/physics page (boxes in per-mille). "
          "Return JSON {\"stem\": str, \"options\": {\"A\":..,\"B\":..,\"C\":..,\"D\":..}}. Formulas as LaTeX inside $...$ (chemistry as \\ce{...}). "
          "Repair obvious OCR slips only when internal evidence supports it; never invent text; if the OCR text has no options for the question return an empty options object. "
          "Options printed as drawings are absent from the text: do not guess them.")
items = json.load(open(sys.argv[1], encoding="utf-8")); out = []; tin = tout = 0
for it in items:
    page = Path(it["ocr_text"]).read_text(encoding="utf-8")
    r = client.chat.completions.create(model="deepseek-flash", response_format={"type": "json_object"}, max_tokens=4000, temperature=0,
                                       messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"Question number {it['number']} on this page.\n\n{page}"}],
                                       extra_body={"thinking": {"type": "disabled"}})
    d = json.loads(r.choices[0].message.content); tin += r.usage.prompt_tokens; tout += r.usage.completion_tokens
    out.append(dict(qid=it["qid"], stem=d.get("stem", ""), options=d.get("options") or {}))
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "questions; tokens in/out", tin, tout)
