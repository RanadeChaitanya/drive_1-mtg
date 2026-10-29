"""Code-only clipping gate: a crop whose outer 2 px border still holds ink was cut through a drawing. python border_check.py <figs_dir> <route.json> ..."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
d = Path(sys.argv[1]); bad = tot = 0
for f in sys.argv[2:]:
    for r in json.load(open(f, encoding="utf-8")):
        for n in r["stem_images"] + list(r["option_images"].values()):
            a = np.array(Image.open(d / n).convert("L")) < 190; tot += 1
            if a[:2].any() or a[-2:].any() or a[:, :2].any() or a[:, -2:].any(): bad += 1; r.setdefault("clipped", []).append(n)
print(f"{bad} of {tot} crops touch their border with ink")
