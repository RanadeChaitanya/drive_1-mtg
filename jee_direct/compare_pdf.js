// Comparative review page: printed region | direct route (text layer + judged pictures) | OCR route (DeepSeek-OCR text, its own pictures).
// node compare_pdf.js <direct.json> <ocr.json> <direct_figs> <ocr_figs> <regions_dir> <out.html> qid ...
const fs = require("fs"), path = require("path");
const nm = process.env.KATEX_DIR || "D:/MSA/final-pipeline/qc/latex_tools/node_modules";
const katex = require(nm + "/katex"); require(nm + "/katex/dist/contrib/mhchem.min.js");
const [, , dj, oj, dfigs, ofigs, regs, out, ...ids] = process.argv;
const D = Object.fromEntries(JSON.parse(fs.readFileSync(dj, "utf8")).questions.map(q => [q.qid, q]));
const O = Object.fromEntries(JSON.parse(fs.readFileSync(oj, "utf8")).map(q => [q.qid, q]));
const esc = s => (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
const fix = t => (t || "").replace(/\\\(\s*/g, "$").replace(/\s*\\\)/g, "$").replace(/\\\[\s*/g, "$").replace(/\s*\\\]/g, "$");
const tex = t => fix(t).split(/(\$[^$]+\$)/).map(p => p.startsWith("$") && p.length > 1 ? katex.renderToString(p.slice(1, -1), { throwOnError: false }) : esc(p)).join("");
const url = p => "file:///" + path.resolve(p).split(path.sep).join("/");
const img = (d, n, c) => `<img class="${c || "f"}" src="${url(path.join(d, n))}">`;
const dcol = q => !q ? "<i>not in direct JSON</i>" : `<p>${tex(q.stem)}</p>${Object.entries(q.options || {}).map(([k, v]) => `<p>(${k}) ${(q.option_images || {})[k] ? img(dfigs, q.option_images[k], "o") : tex(v)}</p>`).join("")}${(q.stem_images || []).map(i => img(dfigs, i)).join("")}<div class="n">key ${q.correct_option || q.answer || "?"} ${(q.flags || []).map(f => `<span class="fl">${f}</span>`).join("")}</div>`;
const ocol = q => !q ? "<i>not found by OCR route</i>" : `<p>${tex(q.stem_raw)}</p>${Object.entries(q.options_raw || {}).map(([k, v]) => `<p>(${k}) ${(q.option_images || {})[k] ? img(ofigs, q.option_images[k], "o") : tex(v)}</p>`).join("")}${Object.entries(q.option_images || {}).filter(([k]) => !(q.options_raw || {})[k]).map(([k, v]) => `<p>(${k}) ${img(ofigs, v, "o")}</p>`).join("")}${(q.stem_images || []).map(i => img(ofigs, i)).join("")}<div class="n">options: ${q.options_status} ${(q.flags || []).map(f => `<span class="fl">${f}</span>`).join("")}</div>`;
const card = id => `<div class="q"><div class="h">${id}</div><div class="row"><div class="c"><div class="t">printed</div><img class="r" src="${url(path.join(regs, id + ".png"))}"></div><div class="c"><div class="t">direct route</div>${dcol(D[id])}</div><div class="c"><div class="t">OCR route</div>${ocol(O[id])}</div></div></div>`;
fs.writeFileSync(out, `<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="${url(nm + "/katex/dist/katex.min.css")}"><style>
body{font-family:Georgia,serif;font-size:11px;margin:10px}.q{border:1px solid #888;padding:6px;margin-bottom:10px;break-inside:avoid}.row{display:flex;gap:8px}.c{flex:1;min-width:0}
.h{font-weight:bold;margin-bottom:3px}.t{background:#eee;font-size:10px;padding:1px 4px;margin-bottom:3px}.f,.r{max-width:100%}.o{max-height:70px;max-width:60%;vertical-align:middle}p{margin:3px 0}.n{color:#777;font-size:9px;margin-top:3px}.fl{background:#fde68a;padding:0 3px}</style>
<h3>Direct route vs OCR route (${ids.length} questions)</h3>${ids.map(card).join("")}`);
