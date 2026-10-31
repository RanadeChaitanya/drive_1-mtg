"""DeepSeek (deepseek-chat, image input) redraws each crop as SVG. Key from DEEPSEEK_API_KEY only.  python deepseek_svg.py <in_dir> <out_dir>"""
import base64, glob, os, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY") or sys.exit("set DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com", timeout=300)
PROMPT = ("This PNG ({w}x{h} px) is ONE figure cut from a printed exam page: a chemical structure/reaction scheme, graph, circuit or diagram. Redraw exactly that figure as a standalone SVG: "
          "every bond (single/double/triple, wedge, dashed wedge), ring, atom label with subscripts/charges, arrow, plus sign, reagent text, axis, curve, tick label. Add nothing that is not in the picture. "
          "Use <svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 {w} {h}\">, a white background rect, black strokes about 2 wide, <text> for labels (serif), positions as close to the picture as possible. "
          "Return ONLY the SVG code, no explanation, no markdown fence.")
usage = [0, 0]


def one(p):
    w, h = Image.open(p).size; b = base64.b64encode(open(p, "rb").read()).decode()
    r = client.chat.completions.create(model="deepseek-chat", max_tokens=6000, temperature=0, messages=[{"role": "user", "content": [
        {"type": "text", "text": PROMPT.format(w=w, h=h)}, {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b}}]}])
    usage[0] += r.usage.prompt_tokens; usage[1] += r.usage.completion_tokens
    t = r.choices[0].message.content or ""; m = re.search(r"<svg.*</svg>", t, re.S)
    Path(sys.argv[2], Path(p).stem + ".svg").write_text(m.group(0) if m else t, encoding="utf-8")


Path(sys.argv[2]).mkdir(parents=True, exist_ok=True)
with ThreadPoolExecutor(6) as ex: list(ex.map(one, sorted(glob.glob(sys.argv[1] + "/*.png"))))
print("tokens in/out", usage)
