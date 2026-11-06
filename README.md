# MSA question-extraction pipelines (scripts only)

No book content, images, model outputs or API keys are stored here (see `.gitignore`). Keys are read from environment variables only.

- `pipeline_a_scanned/` - scanned books (CET PCB 2024 test). Local `deepseek-ocr` (ollama) reads each crop (`dsocr.py`), `dsconv.py` converts the text to stem/options by code, `postproc.py` repairs Gemma 3 4B output, `score.py` scores against a reference (stem and all four options >= 0.95 similar = fully matching). Haiku is used strictly for pictures (SVG), never to back up text failures.
- `pipeline_b_digital/` - born-digital papers (Chemistry 2020). PDF text layer + page image -> DeepSeek understand-first prompt (`ds2.py`) -> Haiku proofread -> pictures drawn as SVG (`*_BRIEF.md` hold the agent briefs). `lint.py` checks KaTeX.
- `tools/` - one-off patch/prepare scripts.

Results so far (proxy score, optimistic): scanned 32/37, digital 8/11 fully matching; the 99% target is not reached. Every test must include both digital and scanned questions, reported separately.
