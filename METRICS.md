# Result on Copy_of_0dea66c2.pdf (Disha chemistry problem book), question pages 5-106

| Metric | Value |
|---|---|
| Questions extracted | 777 |
| With answer from the book's ANSWER KEY | 775 (99.7%) |
| Questions with no open flag | 756 (97.3%) |
| Figure questions | 97; crop judged complete 81 (83.5%); 16 flagged FIGURE_CLIPPED (question runs into the next column/page) |
| Picture-option questions (options are drawings) | 35, text options replaced by "[figure option]" |
| Book key disputed by a solver (kept, flagged) | 3 |
| Key not checkable from the print (flagged) | 10 |
| Still open | 1 with 3 options, 1 non-letter key |

Method: PDF text layer (no OCR) -> page-image checks by Haiku (2 attempts) -> Sonnet for what Haiku left open.
Accuracy figures come from model readers comparing against the printed page; no human review and no strict KaTeX pass yet. Book keys are never overwritten.
Solutions for each question are in the book (pages 107-208) and are not extracted yet.

## Picture accuracy (option images + stem figures), pages tuned on and unseen

Judge: strict Sonnet reading each crop against the full printed page (no human review). 63 picture questions, 148 images, 13 pages (5 tuned on, 8 not).

| Stage | Images accepted | Questions fully accepted |
|---|---|---|
| Code only (`figs2.py`: text layer + pixel blobs, no OCR boxes) | 73 / 155 (47%) | - |
| + Sonnet reads gridded page strips, returns crop boxes (`repair_tools.py`) | 116 / 149 (78%) | 40 / 63 (63%) |
| + second round with the judge's reasons fed back | 143 / 148 (96.6%) | 60 / 63 (95%) |
| + text-edge trim, third judge | 146 / 148 (98.6%) | 61 / 63 (96.8%) |

Not proven: 99% (the judge is a model; the tuning pages overlap the test pages; 2 images still fail: a printed question number and a stray letter at the crop edge).
Per picture question the loop costs roughly 2-3 Sonnet calls (about 10k tokens). Text-only questions need none of it.
