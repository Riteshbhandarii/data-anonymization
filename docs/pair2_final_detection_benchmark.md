\# Pair 2 Final Detection Benchmark



\## 1. Scope



This document reports the final Presidio detection baseline for the three document formats evaluated in this work:



\- XLSX

\- PPTX

\- PDF



The benchmark uses the team's final synthetic corpus and matching ground-truth labels.



The complete team corpus contains 500 documents and 6,500 labelled identifiers. This benchmark covers the 300 documents belonging to XLSX, PPTX, and PDF.



Detection is evaluated on `body` labels only.



Metadata, PowerPoint speaker notes, and Excel hidden-sheet identifiers are intentionally excluded from the detection recall denominator because exposing those values is part of the extraction stage rather than the detection stage.



\## 2. Benchmark Method



The detector uses Presidio Analyzer with spaCy language models for:



\- English

\- Finnish



The same entity mapping and scoring logic as the existing `eval/bench.py` baseline were retained.



Each ground-truth identifier is classified as:



\- \*\*Full\*\* – the detector covers the complete identifier

\- \*\*Partial\*\* – only part of the identifier is detected

\- \*\*Missed\*\* – no relevant detection covers the identifier



Full recall is calculated as:



`fully detected / total ground-truth identifiers`



The benchmark was run with:



```text

python eval/pair2\_final\_bench.py bench\_pair2\_final

```



\## 3. Dataset Used



The final run processed:



\- 100 XLSX documents

\- 100 PPTX documents

\- 100 PDF documents

\- 300 documents in total



The body-only detection benchmark contained:



\- 2,800 ground-truth identifiers



\## 4. Results by Format and Language



| Format | Language | Full | Total | Full Recall | Partial | Missed |

|---|---|---:|---:|---:|---:|---:|

| XLSX | English | 346 | 400 | 86.50% | 16 | 38 |

| XLSX | Finnish | 325 | 400 | 81.25% | 13 | 62 |

| PPTX | English | 253 | 400 | 63.25% | 56 | 91 |

| PPTX | Finnish | 235 | 400 | 58.75% | 47 | 118 |

| PDF | English | 363 | 600 | 60.50% | 45 | 192 |

| PDF | Finnish | 342 | 600 | 57.00% | 39 | 219 |



\## 5. Combined Result



Across XLSX, PPTX, and PDF:



\- Ground-truth body identifiers: 2,800

\- Fully detected: 1,864

\- Partially detected: 216

\- Completely missed: 720



Full detection recall:



`1864 / 2800 = 66.57%`



Partial detections:



`216 / 2800 = 7.71%`



Missed identifiers:



`720 / 2800 = 25.71%`



\## 6. XLSX Results



\### English



| Entity | Total | Full | Partial | Missed | Recall |

|---|---:|---:|---:|---:|---:|

| COMPANY | 50 | 14 | 14 | 22 | 28% |

| DATE | 100 | 100 | 0 | 0 | 100% |

| EMAIL | 50 | 50 | 0 | 0 | 100% |

| IBAN | 50 | 50 | 0 | 0 | 100% |

| PERSON | 100 | 90 | 2 | 8 | 90% |

| PHONE | 50 | 42 | 0 | 8 | 84% |



English XLSX full recall: \*\*86.50%\*\*



\### Finnish



| Entity | Total | Full | Partial | Missed | Recall |

|---|---:|---:|---:|---:|---:|

| COMPANY | 50 | 5 | 8 | 37 | 10% |

| DATE | 100 | 100 | 0 | 0 | 100% |

| EMAIL | 50 | 50 | 0 | 0 | 100% |

| IBAN | 50 | 50 | 0 | 0 | 100% |

| PERSON | 100 | 79 | 4 | 17 | 79% |

| PHONE | 50 | 41 | 1 | 8 | 82% |



Finnish XLSX full recall: \*\*81.25%\*\*



XLSX produced the strongest overall detection results among the three evaluated formats.



The main weakness was COMPANY detection, particularly in Finnish.



\## 7. PPTX Results



\### English



| Entity | Total | Full | Partial | Missed | Recall |

|---|---:|---:|---:|---:|---:|

| ADDRESS | 50 | 0 | 33 | 17 | 0% |

| COMPANY | 50 | 15 | 23 | 12 | 30% |

| DATE | 50 | 50 | 0 | 0 | 100% |

| EMAIL | 50 | 50 | 0 | 0 | 100% |

| IBAN | 50 | 50 | 0 | 0 | 100% |

| INVOICE | 50 | 0 | 0 | 50 | 0% |

| PERSON | 50 | 48 | 0 | 2 | 96% |

| PHONE | 50 | 40 | 0 | 10 | 80% |



English PPTX full recall: \*\*63.25%\*\*



\### Finnish



| Entity | Total | Full | Partial | Missed | Recall |

|---|---:|---:|---:|---:|---:|

| ADDRESS | 50 | 0 | 33 | 17 | 0% |

| COMPANY | 50 | 3 | 12 | 35 | 6% |

| DATE | 50 | 50 | 0 | 0 | 100% |

| EMAIL | 50 | 50 | 0 | 0 | 100% |

| IBAN | 50 | 50 | 0 | 0 | 100% |

| INVOICE | 50 | 0 | 0 | 50 | 0% |

| PERSON | 50 | 46 | 1 | 3 | 92% |

| PHONE | 50 | 36 | 1 | 13 | 72% |



Finnish PPTX full recall: \*\*58.75%\*\*



ADDRESS values were frequently detected only partially, while INVOICE values were completely missed by the baseline.



\## 8. PDF Results



\### English



| Entity | Total | Full | Partial | Missed | Recall |

|---|---:|---:|---:|---:|---:|

| ADDRESS | 50 | 0 | 35 | 15 | 0% |

| COMPANY | 50 | 30 | 8 | 12 | 60% |

| DATE | 100 | 100 | 0 | 0 | 100% |

| EMAIL | 50 | 50 | 0 | 0 | 100% |

| IBAN | 50 | 50 | 0 | 0 | 100% |

| INVOICE | 50 | 0 | 0 | 50 | 0% |

| PERSON | 100 | 94 | 2 | 4 | 94% |

| PERSONAL\_ID | 50 | 0 | 0 | 50 | 0% |

| PHONE | 50 | 39 | 0 | 11 | 78% |

| PLATE | 50 | 0 | 0 | 50 | 0% |



English PDF full recall: \*\*60.50%\*\*



\### Finnish



| Entity | Total | Full | Partial | Missed | Recall |

|---|---:|---:|---:|---:|---:|

| ADDRESS | 50 | 0 | 31 | 19 | 0% |

| COMPANY | 50 | 7 | 6 | 37 | 14% |

| DATE | 100 | 100 | 0 | 0 | 100% |

| EMAIL | 50 | 50 | 0 | 0 | 100% |

| IBAN | 50 | 50 | 0 | 0 | 100% |

| INVOICE | 50 | 0 | 0 | 50 | 0% |

| PERSON | 100 | 90 | 2 | 8 | 90% |

| PERSONAL\_ID | 50 | 0 | 0 | 50 | 0% |

| PHONE | 50 | 45 | 0 | 5 | 90% |

| PLATE | 50 | 0 | 0 | 50 | 0% |



Finnish PDF full recall: \*\*57.00%\*\*



\## 9. Main Findings



The strongest baseline entity types were:



\- DATE

\- EMAIL

\- IBAN



These achieved 100% full recall across the evaluated formats.



PERSON detection was also relatively strong, although Finnish XLSX performed lower than the other PERSON tests.



The main weaknesses were:



\- ADDRESS

\- COMPANY

\- INVOICE

\- PERSONAL\_ID

\- PLATE



ADDRESS was frequently detected only partially.



COMPANY detection was substantially weaker in Finnish than in English.



INVOICE, PERSONAL\_ID, and PLATE were not covered by the baseline recognizer configuration used in this run.



These entity types are candidates for custom recognizers or improved detection models.



\## 10. Language Comparison



Finnish generally produced lower full recall than English:



\- XLSX: 86.50% English vs 81.25% Finnish

\- PPTX: 63.25% English vs 58.75% Finnish

\- PDF: 60.50% English vs 57.00% Finnish



The largest language-specific weakness was COMPANY detection.



This indicates that Finnish organization recognition should be one of the priorities for further detector improvement.



\## 11. Limitations



This benchmark evaluates detection only after document content has been extracted.



Metadata, hidden worksheets, and speaker notes are deliberately excluded from the detection denominator because they belong to the extraction stage.



The results represent the current Presidio baseline configuration. Custom recognizers and different spaCy models may change the results.



The corpus is synthetic, which makes it safe and reproducible but does not fully represent the complexity of real company documents.



The results in this document supersede earlier preliminary benchmark results produced using a smaller 250-document corpus.



\## 12. Conclusion



The final baseline benchmark evaluated 2,800 body identifiers across 300 XLSX, PPTX, and PDF documents.



Presidio fully detected:



\*\*1,864 / 2,800 = 66.57%\*\*



XLSX achieved the highest recall, while PPTX and PDF were more challenging because they contained entity types such as ADDRESS and INVOICE that were poorly covered by the baseline.



The results establish a reproducible baseline for later comparison with custom recognizers and improved English/Finnish detection models.


## 13. Custom Recognizer Evaluation

After establishing the Presidio baseline, three project-specific pattern recognizers were added for entity types that were not covered by the baseline:

- INVOICE
- PERSONAL_ID
- PLATE

The custom recognizers were evaluated using the same final corpus, the same 300 XLSX/PPTX/PDF documents, the same 2,800 body ground-truth identifiers, and the same scoring method.

This makes the baseline and improved detector directly comparable.

### Baseline vs Custom Recognizers

| Configuration | Fully Detected | Full Recall | Partial | Missed |
|---|---:|---:|---:|---:|
| Presidio baseline | 1,864 / 2,800 | 66.57% | 216 | 720 |
| Presidio + custom recognizers | 2,264 / 2,800 | 80.86% | 216 | 320 |

Adding the custom recognizers increased full recall by:

**80.86% - 66.57% = 14.29 percentage points**

The number of completely missed identifiers decreased from:

**720 to 320**

This is a reduction of 400 missed identifiers.

### Improved Results by Format and Language

| Format | Language | Baseline Recall | Custom Recall | Change |
|---|---|---:|---:|---:|
| XLSX | English | 86.50% | 86.50% | 0.00 pp |
| XLSX | Finnish | 81.25% | 81.25% | 0.00 pp |
| PPTX | English | 63.25% | 75.75% | +12.50 pp |
| PPTX | Finnish | 58.75% | 71.25% | +12.50 pp |
| PDF | English | 60.50% | 85.50% | +25.00 pp |
| PDF | Finnish | 57.00% | 82.00% | +25.00 pp |

XLSX results did not change because the XLSX body benchmark does not contain INVOICE, PERSONAL_ID, or PLATE identifiers.

PPTX improved because INVOICE identifiers became fully detectable.

PDF improved the most because its body labels contain INVOICE, PERSONAL_ID, and PLATE identifiers.

### Custom Entity Results

The custom recognizers achieved full detection for the target entity types present in the evaluated body text:

| Format | Language | Entity | Full | Total | Recall |
|---|---|---|---:|---:|---:|
| PPTX | English | INVOICE | 50 | 50 | 100% |
| PPTX | Finnish | INVOICE | 50 | 50 | 100% |
| PDF | English | INVOICE | 50 | 50 | 100% |
| PDF | Finnish | INVOICE | 50 | 50 | 100% |
| PDF | English | PERSONAL_ID | 50 | 50 | 100% |
| PDF | Finnish | PERSONAL_ID | 50 | 50 | 100% |
| PDF | English | PLATE | 50 | 50 | 100% |
| PDF | Finnish | PLATE | 50 | 50 | 100% |

The custom recognizers therefore recovered all 400 identifiers belonging to these previously unsupported entity types in the evaluated body labels.

### Interpretation

The baseline already performed strongly for structured entities such as DATE, EMAIL, and IBAN.

The custom recognizers address a different problem: entity types whose syntax is specific to the project corpus and which Presidio did not recognize using the baseline configuration.

The largest improvement occurred in PDF because PDF contained all three custom entity types.

Remaining weaknesses after the custom recognizers are mainly:

- ADDRESS
- COMPANY
- some PERSON detections
- some PHONE detections

ADDRESS remains especially difficult because Presidio often detects only part of the complete address.

Finnish COMPANY detection also remains substantially weaker than English COMPANY detection.

## 14. Final Detection Result

After adding the project-specific recognizers, the final detector result across the 300 evaluated XLSX, PPTX, and PDF documents was:

- Ground-truth body identifiers: 2,800
- Fully detected: 2,264
- Partially detected: 216
- Missed: 320
- Full recall: 80.86%

Compared with the original Presidio baseline, full recall increased by 14.29 percentage points.

The benchmark therefore demonstrates both the limitations of the default Presidio configuration and the measurable benefit of adding recognizers for project-specific identifier formats.
