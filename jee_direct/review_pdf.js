// KaTeX review page: extracted question (stem, options, key, figures) next to the printed region. node review_pdf.js <questions.json> <figs_dir> <regions_dir> <out.html> qid1 qid2 ...
const fs = require("fs"), path = require("path");
const nm = path.resolve(__dirname, "../qc/latex_tools/node_modules");
const katex = require(nm + "/katex"); require(nm + "/katex/dist/contrib/mhchem.min.js");
const [, , src, figs, regs, out, ...ids] = process.argv;
const Q = JSON.parse(fs.readFileSync(src, "utf8")).questions.filter(q => ids.includes(q.qid));
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const tex = t => (t || "").split(/(\$[^$]+\$)/).map(p => p.startsWith("$") && p.length > 1 ? katex.renderToString(p.slice(1, -1), { throwOnError: false }) : esc(p)).join("");
const url = p => "file:///" + path.resolve(p).split(path.sep).join("/");
const css = url(nm + "/katex/dist/katex.min.css");
const card = q => `<div class="q"><div class="l"><b>${q.qid}</b> &middot; ${esc(q.chapter)} &middot; key <b>${q.correct_option || q.answer || "?"}</b>${(q.flags || []).filter(f => f !== "IMAGE_OPTIONS").map(f => ` <span class="fl">${f}</span>`).join("")}${q.key_note ? `<div class="n">${esc(q.key_note)}</div>` : ""}
<p>${tex(q.stem)}</p>${Object.entries(q.options).map(([k, v]) => `<p>(${k}) ${(q.option_images || {})[k] ? `<img class="o" src="${url(path.join(figs, q.option_images[k]))}">` : tex(v)}</p>`).join("")}
${(q.images || []).map(i => `<img class="f" src="${url(path.join(figs, i))}">`).join("")}<div class="n">extracted text + cropped figure (the JSON)</div></div>
<div class="r"><img src="${url(path.join(regs, q.qid + ".png"))}"><div class="n">printed page region (original)</div></div></div>`;
fs.writeFileSync(out, `<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="${css}"><style>
body{font-family:Georgia,serif;font-size:13px;margin:14px}.q{display:flex;gap:14px;border:1px solid #888;padding:8px;margin-bottom:12px;break-inside:avoid}
.l,.r{flex:1;min-width:0}.f,.r img{max-width:100%}.n{color:#777;font-size:10px;margin-top:4px}p{margin:4px 0}.o{max-height:90px;max-width:70%;vertical-align:middle}.fl{background:#fde68a;padding:0 4px;font-size:10px}</style>
<h3>JEE OS DATA - extraction review (${Q.length} questions with figures)</h3>${Q.map(card).join("")}`);
