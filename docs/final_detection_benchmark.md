# Final Detection Benchmark — Five Formats

## 1. Scope

This report presents the final detection benchmark across all five synthetic document formats used by the project:

- CSV
- DOCX
- XLSX
- PPTX
- PDF

The complete evaluated corpus contains:

- 500 documents
- English and Finnish documents
- 4,900 body ground-truth identifiers

There are 100 documents per format: 50 English and 50 Finnish.

Detection is evaluated on `body` labels only.

Metadata, PowerPoint speaker notes, Excel hidden sheets, and other non-body identifiers are excluded from the detection recall denominator because they belong to the extraction stage rather than the detection stage.

## 2. Detector Configuration

The evaluated detector configuration uses Presidio Analyzer with spaCy language models:

- English: `en_core_web_sm`
- Finnish: `fi_core_news_sm`

Versions used in the final result:

- Presidio Analyzer: 2.2.364
- spaCy: 3.8.16
- en_core_web_sm: 3.8.0
- fi_core_news_sm: 3.8.0
- Score threshold: 0.0

The project-specific configuration also includes custom pattern recognizers for:

- INVOICE
- PERSONAL_ID
- PLATE

Each ground-truth identifier is classified as:

- **Full** — the detector covers the complete identifier
- **Partial** — only part of the identifier is detected
- **Missed** — no relevant detection covers the identifier

Full recall is calculated as:

`fully detected / total ground-truth identifiers`

## 3. Final Results by Format and Language

| Format | Language | Full | Total | Full Recall | Partial | Missed |
|---|---|---:|---:|---:|---:|---:|
| CSV | English | 354 | 450 | 78.67% | 47 | 49 |
| CSV | Finnish | 318 | 450 | 70.67% | 35 | 97 |
| DOCX | English | 505 | 600 | 84.17% | 45 | 50 |
| DOCX | Finnish | 491 | 600 | 81.83% | 50 | 59 |
| XLSX | English | 346 | 400 | 86.50% | 16 | 38 |
| XLSX | Finnish | 325 | 400 | 81.25% | 13 | 62 |
| PPTX | English | 303 | 400 | 75.75% | 56 | 41 |
| PPTX | Finnish | 285 | 400 | 71.25% | 47 | 68 |
| PDF | English | 513 | 600 | 85.50% | 45 | 42 |
| PDF | Finnish | 492 | 600 | 82.00% | 39 | 69 |

## 4. Combined Final Result

Across all five formats:

- Documents: 500
- Ground-truth body identifiers: 4,900
- Fully detected: 3,932
- Partially detected: 393
- Missed: 575

Full recall:

**3,932 / 4,900 = 80.24%**

Partial:

**393 / 4,900 = 8.02%**

Missed:

**575 / 4,900 = 11.73%**

### Combined Result by Format

| Format | Full | Total | Full Recall | Partial | Missed |
|---|---:|---:|---:|---:|---:|
| CSV | 672 | 900 | 74.67% | 82 | 146 |
| DOCX | 996 | 1,200 | 83.00% | 95 | 109 |
| XLSX | 671 | 800 | 83.88% | 29 | 100 |
| PPTX | 588 | 800 | 73.50% | 103 | 109 |
| PDF | 1,005 | 1,200 | 83.75% | 84 | 111 |

### English vs Finnish

| Language | Full | Total | Full Recall | Partial | Missed |
|---|---:|---:|---:|---:|---:|
| English | 2,021 | 2,450 | 82.49% | 209 | 220 |
| Finnish | 1,911 | 2,450 | 78.00% | 184 | 355 |

English achieved higher full recall than Finnish in the final evaluated configuration.

## 5. Entity-Level Summary Across All Formats

Entity totals differ because not every format contains every entity type.

| Entity | Total | Full | Partial | Missed | Full Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 400 | 0 | 258 | 142 | 0.00% |
| COMPANY | 500 | 129 | 106 | 265 | 25.80% |
| DATE | 700 | 700 | 0 | 0 | 100.00% |
| EMAIL | 500 | 500 | 0 | 0 | 100.00% |
| IBAN | 500 | 500 | 0 | 0 | 100.00% |
| INVOICE | 300 | 300 | 0 | 0 | 100.00% |
| PERSON | 900 | 793 | 26 | 81 | 88.11% |
| PERSONAL_ID | 300 | 300 | 0 | 0 | 100.00% |
| PHONE | 500 | 410 | 3 | 87 | 82.00% |
| PLATE | 300 | 300 | 0 | 0 | 100.00% |

The strongest fully detected entity types were DATE, EMAIL, IBAN, INVOICE, PERSONAL_ID, and PLATE.

The main remaining weaknesses were ADDRESS and COMPANY.

Although ADDRESS often received a partial detection, no full address was completely covered under the strict benchmark scoring rule.

## 6. CSV Results

### English

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 50 | 0 | 35 | 15 | 0% |
| COMPANY | 50 | 17 | 10 | 23 | 34% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| PERSON | 100 | 91 | 2 | 7 | 91% |
| PERSONAL_ID | 50 | 50 | 0 | 0 | 100% |
| PHONE | 50 | 46 | 0 | 4 | 92% |
| PLATE | 50 | 50 | 0 | 0 | 100% |

CSV English full recall: **78.67%**

### Finnish

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 50 | 0 | 21 | 29 | 0% |
| COMPANY | 50 | 4 | 7 | 39 | 8% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| PERSON | 100 | 76 | 7 | 17 | 76% |
| PERSONAL_ID | 50 | 50 | 0 | 0 | 100% |
| PHONE | 50 | 38 | 0 | 12 | 76% |
| PLATE | 50 | 50 | 0 | 0 | 100% |

CSV Finnish full recall: **70.67%**

The largest CSV weaknesses were ADDRESS and COMPANY. Finnish PERSON and PHONE detection were also weaker than their English equivalents.

## 7. DOCX Results

### English

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 50 | 0 | 36 | 14 | 0% |
| COMPANY | 50 | 25 | 8 | 17 | 50% |
| DATE | 100 | 100 | 0 | 0 | 100% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| INVOICE | 50 | 50 | 0 | 0 | 100% |
| PERSON | 100 | 91 | 1 | 8 | 91% |
| PERSONAL_ID | 50 | 50 | 0 | 0 | 100% |
| PHONE | 50 | 39 | 0 | 11 | 78% |
| PLATE | 50 | 50 | 0 | 0 | 100% |

DOCX English full recall: **84.17%**

### Finnish

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 50 | 0 | 34 | 16 | 0% |
| COMPANY | 50 | 9 | 10 | 31 | 18% |
| DATE | 100 | 100 | 0 | 0 | 100% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| INVOICE | 50 | 50 | 0 | 0 | 100% |
| PERSON | 100 | 88 | 5 | 7 | 88% |
| PERSONAL_ID | 50 | 50 | 0 | 0 | 100% |
| PHONE | 50 | 44 | 1 | 5 | 88% |
| PLATE | 50 | 50 | 0 | 0 | 100% |

DOCX Finnish full recall: **81.83%**

DOCX achieved relatively strong overall results, with the main weaknesses again concentrated in ADDRESS and COMPANY.

## 8. XLSX Results

### English

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| COMPANY | 50 | 14 | 14 | 22 | 28% |
| DATE | 100 | 100 | 0 | 0 | 100% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| PERSON | 100 | 90 | 2 | 8 | 90% |
| PHONE | 50 | 42 | 0 | 8 | 84% |

XLSX English full recall: **86.50%**

### Finnish

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| COMPANY | 50 | 5 | 8 | 37 | 10% |
| DATE | 100 | 100 | 0 | 0 | 100% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| PERSON | 100 | 79 | 4 | 17 | 79% |
| PHONE | 50 | 41 | 1 | 8 | 82% |

XLSX Finnish full recall: **81.25%**

XLSX produced strong overall results, although COMPANY recognition remained weak, particularly in Finnish.

## 9. PPTX Results

### English

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 50 | 0 | 33 | 17 | 0% |
| COMPANY | 50 | 15 | 23 | 12 | 30% |
| DATE | 50 | 50 | 0 | 0 | 100% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| INVOICE | 50 | 50 | 0 | 0 | 100% |
| PERSON | 50 | 48 | 0 | 2 | 96% |
| PHONE | 50 | 40 | 0 | 10 | 80% |

PPTX English full recall: **75.75%**

### Finnish

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 50 | 0 | 33 | 17 | 0% |
| COMPANY | 50 | 3 | 12 | 35 | 6% |
| DATE | 50 | 50 | 0 | 0 | 100% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| INVOICE | 50 | 50 | 0 | 0 | 100% |
| PERSON | 50 | 46 | 1 | 3 | 92% |
| PHONE | 50 | 36 | 1 | 13 | 72% |

PPTX Finnish full recall: **71.25%**

The custom INVOICE recognizer provides full coverage for the synthetic invoice-number pattern used in the corpus.

ADDRESS and Finnish COMPANY remain major weaknesses.

## 10. PDF Results

### English

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 50 | 0 | 35 | 15 | 0% |
| COMPANY | 50 | 30 | 8 | 12 | 60% |
| DATE | 100 | 100 | 0 | 0 | 100% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| INVOICE | 50 | 50 | 0 | 0 | 100% |
| PERSON | 100 | 94 | 2 | 4 | 94% |
| PERSONAL_ID | 50 | 50 | 0 | 0 | 100% |
| PHONE | 50 | 39 | 0 | 11 | 78% |
| PLATE | 50 | 50 | 0 | 0 | 100% |

PDF English full recall: **85.50%**

### Finnish

| Entity | Total | Full | Partial | Missed | Recall |
|---|---:|---:|---:|---:|---:|
| ADDRESS | 50 | 0 | 31 | 19 | 0% |
| COMPANY | 50 | 7 | 6 | 37 | 14% |
| DATE | 100 | 100 | 0 | 0 | 100% |
| EMAIL | 50 | 50 | 0 | 0 | 100% |
| IBAN | 50 | 50 | 0 | 0 | 100% |
| INVOICE | 50 | 50 | 0 | 0 | 100% |
| PERSON | 100 | 90 | 2 | 8 | 90% |
| PERSONAL_ID | 50 | 50 | 0 | 0 | 100% |
| PHONE | 50 | 45 | 0 | 5 | 90% |
| PLATE | 50 | 50 | 0 | 0 | 100% |

PDF Finnish full recall: **82.00%**

PDF benefits strongly from the project-specific recognizers because the PDF body labels contain INVOICE, PERSONAL_ID, and PLATE identifiers.

## 11. Custom Recognizers

Three project-specific pattern recognizers were used in the evaluated configuration:

- INVOICE
- PERSONAL_ID
- PLATE

They achieved 100% full recall for the corresponding synthetic identifier patterns present in the evaluated body labels.

These results apply specifically to the synthetic patterns used in this benchmark and should not be interpreted as 100% recall on unrestricted real-world data.

## 12. Baseline Comparison Status

A directly comparable raw Presidio baseline is available for the XLSX, PPTX, and PDF subset.

For those 300 documents and 2,800 body identifiers:

| Configuration | Full | Total | Full Recall | Partial | Missed |
|---|---:|---:|---:|---:|---:|
| Presidio baseline | 1,864 | 2,800 | 66.57% | 216 | 720 |
| Presidio + custom recognizers | 2,264 | 2,800 | 80.86% | 216 | 320 |

For this three-format subset, the custom recognizers increased full recall by:

**14.29 percentage points**

and reduced completely missed identifiers by:

**400**

The CSV and DOCX results included in the five-format final evaluation were supplied from the custom-recognizer configuration.

A raw Presidio-only CSV/DOCX result was not included in the supplied benchmark results. Therefore, this report does not claim a five-format baseline-to-custom improvement percentage.

## 13. Main Findings

The final five-format configuration fully detected 80.24% of the 4,900 evaluated body identifiers.

DATE, EMAIL, IBAN, INVOICE, PERSONAL_ID, and PLATE achieved 100% full recall for the synthetic patterns represented in the corpus.

PERSON detection was relatively strong at 88.11% full recall.

PHONE achieved 82.00% full recall.

The largest remaining weaknesses were:

- ADDRESS: 0.00% full recall, although many values were partially detected
- COMPANY: 25.80% full recall
- Finnish detection generally performed below English
- Finnish COMPANY detection remained particularly weak

These results indicate that further work should focus on complete address recognition and improved organization recognition, especially for Finnish.

## 14. Limitations

This benchmark evaluates detection after document content has been extracted.

Metadata, hidden worksheets, speaker notes, and other non-body locations are excluded from the detection denominator because they belong to extraction evaluation.

The corpus is synthetic. This improves reproducibility and privacy, but synthetic identifiers do not fully represent the complexity of real organizational data.

The custom recognizers were designed for identifier patterns represented in the project corpus. Their 100% benchmark recall must not be interpreted as 100% recall on arbitrary real-world identifiers.

Entity distributions differ between formats, so format-level recall values are not based on identical sets of entity types.

A complete raw Presidio baseline comparison for CSV and DOCX was not included in the supplied final results.

## 15. Conclusion

The final evaluated detection configuration covered all five project formats:

- CSV
- DOCX
- XLSX
- PPTX
- PDF

The evaluation processed:

- 500 documents
- 4,900 body ground-truth identifiers

Final result:

- Fully detected: **3,932 / 4,900 = 80.24%**
- Partial: **393 / 4,900 = 8.02%**
- Missed: **575 / 4,900 = 11.73%**

The benchmark demonstrates strong detection for structured identifier types and measurable benefit from project-specific recognizers.

The main remaining detection challenges are complete ADDRESS recognition and COMPANY recognition, particularly in Finnish.