# Independent checker
Input JSON: items {qid, printed (PNG of the printed question), generated {stem, options} (LaTeX), svg_renders {part: PNG of a regenerated figure}}.
For EACH item Read the printed PNG (and svg render PNGs) and judge strictly:
- text_ok: stem and every text option match the printed words/numbers/symbols exactly (typos as printed are correct); LaTeX is valid/appropriate.
- figure_ok: true/false/null(no figure). Regenerated SVG must show the same structure/labels as printed (atoms, bonds, substituents, positions).
- issues: list of short strings (empty if none).
Output file (path given): JSON {qid: {"text_ok":bool,"figure_ok":bool|null,"issues":[...]}} for every item; verify it parses; reply with counts only.
