// printed | direct route | old pipeline (OCR -> DeepSeek -> Haiku check, OCR-box crops), with the judge's ok marks.
// node compare3.js <score_in.json> <score_out.json> <regions_dir> <out.html>
const fs = require("fs"), path = require("path");
const nm = process.env.KATEX_DIR || "D:/MSA/final-pipeline/qc/latex_tools/node_modules";
const katex = require(nm + "/katex"); require(nm + "/katex/dist/contrib/mhchem.min.js");
const [, , inp, sco, regs, out] = process.argv;
const I = JSON.parse(fs.readFileSync(inp, "utf8")), S = Object.fromEntries(JSON.parse(fs.readFileSync(sco, "utf8")).map(r => [r.qid, r]));
const esc = s => (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
const tex = t => (t || "").split(/(\$[^$]+\$)/).map(p => p.startsWith("$") && p.length > 1 ? katex.renderToString(p.slice(1, -1), { throwOnError: false }) : esc(p)).join("");
const url = p => "file:///" + path.resolve(p).split(path.sep).join("/");
const mark = (ok, label) => `<span class="${ok ? "ok" : "bad"}">${label} ${ok ? "✓" : "✗"}</span>`;
const col = (c, sc) => `<p>${tex(c.stem)}</p>${Object.entries(c.options || {}).map(([k, v]) => `<p>(${k}) ${(c.option_images || {})[k] ? `<img class="o" src="${url(c.option_images[k])}">` : tex(v)}</p>`).join("")}${Object.entries(c.option_images || {}).filter(([k]) => !(c.options || {})[k]).map(([k, v]) => `<p>(${k}) <img class="o" src="${url(v)}"></p>`).join("")}${(c.stem_images || []).map(i => `<img class="f" src="${url(i)}">`).join("")}<div class="n">${sc ? mark(sc.stem_ok, "stem") + mark(sc.options_ok, "options") + mark(sc.pictures_ok, "pictures") + (sc.note ? " " + esc(sc.note.slice(0, 140)) : "") : ""}</div>`;
const card = it => `<div class="q"><div class="h">${it.qid}</div><div class="row"><div class="c"><div class="t">printed</div><img class="r" src="${url(it.region)}"></div><div class="c"><div class="t">direct route (PDF text layer + judged pictures)</div>${col(it.direct, (S[it.qid] || {}).direct)}</div><div class="c"><div class="t">old pipeline (OCR + DeepSeek + Haiku, OCR-box crops)</div>${col(it.old, (S[it.qid] || {}).old)}</div></div></div>`;
fs.writeFileSync(out, `<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="${url(nm + "/katex/dist/katex.min.css")}"><style>
body{font-family:Georgia,serif;font-size:11px;margin:10px}.q{border:1px solid #888;padding:6px;margin-bottom:10px;break-inside:avoid}.row{display:flex;gap:8px}.c{flex:1;min-width:0}
.h{font-weight:bold;margin-bottom:3px}.t{background:#eee;font-size:10px;padding:1px 4px;margin-bottom:3px}.f,.r{max-width:100%}.o{max-height:70px;max-width:60%;vertical-align:middle}p{margin:3px 0}.n{font-size:10px;margin-top:3px}.ok{color:#166534;margin-right:6px}.bad{color:#b91c1c;margin-right:6px}</style>
<h3>Direct route vs old pipeline: ${I.length} questions, scored against the printed page</h3>${I.map(card).join("")}`);
