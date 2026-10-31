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

## Whole-book run: Copy_of_0dea66c2.pdf, question pages 5-106 (777 questions)

Picture candidates = questions where the code found drawn art (177). Sonnet boxes every picture from gridded page strips, a second Sonnet judges each crop against the printed page, rejected ones go back with the judge's reasons (3 rounds).

| Round | Images accepted | Questions clean |
|---|---|---|
| 1 (boxes from strips, judged) | 233 / 311 (74.9%) | 129 / 177 |
| 2 (corrections from judge reasons) | 296 / 305 (97.0%) | 171 / 177 |
| 3 (code whiteout of neighbour option / printed number, edge growth) | 298 / 304 (98.0%) | 174 / 177 (98.3%) |

Of the 177 candidates, 58 turned out to have no picture (correct by default); on the 119 questions that really carry pictures, 116 are clean (97.5%).
Still failing (6 images, 3 questions): p043 q21 options C/D and p048 q28 options B/C (neighbouring options touch within 1 px), p084 q12 options C/D (bottom bond clipped).
Caveats: judge = Sonnet, not a human; only questions the code flagged as having art are judged (a picture the code missed is not counted); stem/option TEXT accuracy is measured separately.

## Final Chemistry picture result (two independent Sonnet judges, zoom-fix round included)
Images accepted by BOTH judges: 286 / 298 (96.0%); judge 1 alone 98.0%. 12 images in 9 questions are in `review.pictures` of chem_final.json for a person to check.
Tried and rejected: snapping boxes to ink (refine.py: 18/43 accepted, it erased real axis labels), blanket +3 pt margin (pulled in stray text). Kept: Sonnet nudging boxes on a 4x gridded zoom (+ clean_fragments.py for border fragments).
Direct vs OCR route (10 OCR'd pages, 61 questions): stem text similarity mean 0.90 (44/61 >= 0.9), option text 0.77, OCR found 4 text options for 37 of 57 option questions.
