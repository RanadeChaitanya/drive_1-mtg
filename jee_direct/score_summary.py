"""Summarise score_out.json: per-route accuracy on stem / options / pictures / all three. python score_summary.py <score_out.json>"""
import json, sys

R = json.load(open(sys.argv[1], encoding="utf-8")); n = len(R)
print(f"{n} questions")
for route in ("direct", "old"):
    c = {k: sum(bool(r[route][k]) for r in R) for k in ("stem_ok", "options_ok", "pictures_ok")}
    allok = sum(all(r[route][k] for k in c) for r in R)
    print(f"{route:7} stem {c['stem_ok']}/{n} ({100 * c['stem_ok'] / n:.0f}%)  options {c['options_ok']}/{n} ({100 * c['options_ok'] / n:.0f}%)  pictures {c['pictures_ok']}/{n} ({100 * c['pictures_ok'] / n:.0f}%)  ALL three {allok}/{n} ({100 * allok / n:.0f}%)")
