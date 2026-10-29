# drive_1-mtg: direct extraction of born-digital JEE question books

For PDFs with a clean text layer (Google Drive "JEE OS DATA"): no OCR, no LLM for the bulk. Questions, options, chemistry formulas (mhchem), answer keys and figures come straight from the PDF.

```
python jee_direct/extract.py   <pdf> full.json            # text layer -> questions, options, keys (ANSWER KEY grids)
python jee_direct/finalize.py  full.json fix_dir out.json # question pages only + confident LLM fixes (fix_dir/out_*.json)
python jee_direct/figures.py   <pdf> out.json figs_dir    # crops figures, marks picture-options (IMAGE_OPTIONS)
node   jee_direct/review_pdf.js out.json figs regions review.html qid...   # KaTeX review: JSON vs printed page
```
Leftovers that code cannot place stay flagged; Haiku reads page images for them (2 attempts), then Sonnet (merge_checks.py). See METRICS.md.
`samples/jee_review_5q.pdf`: 5 questions with figures, extracted JSON beside the printed page.
The book text and full JSON are not committed (copyrighted source, public repo).
