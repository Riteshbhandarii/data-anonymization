\# XLSX Extraction and Detection Benchmark



\## 1. Scope



The XLSX test evaluates two separate stages:



1\. Extraction – whether visible and hidden content can be read from the workbook.

2\. Detection – how well Presidio detects identifiers from the extracted body text.



Metadata and hidden-sheet identifiers are evaluated as part of extraction and are not included in the detection recall denominator.



\## 2. Test Data



The generated XLSX corpus contains:



\- 25 English XLSX files

\- 25 Finnish XLSX files

\- 50 XLSX files in total



The XLSX ground truth contains:



\- 400 body identifiers

\- 250 non-body identifiers

\- 650 identifiers in total



Non-body identifiers consist of:



\- 50 ADDRESS values in hidden sheets

\- 50 PERSONAL\_ID values in hidden sheets

\- 50 PLATE values in hidden sheets

\- 100 PERSON values in workbook metadata



\## 3. Extraction Test



The XLSX extractor reads:



\- visible worksheets

\- hidden worksheets

\- workbook metadata



A manual validation using `en\_xlsx\_00.xlsx` found all 13 labelled identifiers:



\- 8 body identifiers

\- 3 hidden-sheet identifiers

\- 2 metadata identifiers



Extraction coverage for the validation file was:



13 / 13 = 100%



This confirms that the extractor can access identifiers that are not visible in the normal spreadsheet view.



\## 4. Detection Baseline



The detection baseline used:



\- Presidio Analyzer 2.2.364

\- spaCy 3.8.16

\- en\_core\_web\_sm 3.8.0

\- fi\_core\_news\_sm 3.8.0

\- score threshold 0.0



The official detection benchmark evaluates body labels only.



\## 5. XLSX Detection Results



\### English



| Entity | Total | Full | Partial | Missed | Full Recall |

|---|---:|---:|---:|---:|---:|

| COMPANY | 25 | 4 | 8 | 13 | 16% |

| DATE | 50 | 50 | 0 | 0 | 100% |

| EMAIL | 25 | 25 | 0 | 0 | 100% |

| IBAN | 25 | 25 | 0 | 0 | 100% |

| PERSON | 50 | 42 | 1 | 7 | 84% |

| PHONE | 25 | 22 | 0 | 3 | 88% |



English total:



168 / 200 fully detected = 84%



\### Finnish



| Entity | Total | Full | Partial | Missed | Full Recall |

|---|---:|---:|---:|---:|---:|

| COMPANY | 25 | 5 | 5 | 15 | 20% |

| DATE | 50 | 50 | 0 | 0 | 100% |

| EMAIL | 25 | 25 | 0 | 0 | 100% |

| IBAN | 25 | 25 | 0 | 0 | 100% |

| PERSON | 50 | 39 | 1 | 10 | 78% |

| PHONE | 25 | 20 | 0 | 5 | 80% |



Finnish total:



164 / 200 fully detected = 82%



\## 6. Combined XLSX Result



Across English and Finnish:



\- Ground-truth body identifiers: 400

\- Fully detected: 332

\- Partially detected: 15

\- Completely missed: 53



Full detection recall:



332 / 400 = 83%



Partial detections:



15 / 400 = 3.75%



Completely missed:



53 / 400 = 13.25%



\## 7. Findings



Presidio performed very well on structured identifiers:



\- DATE: 100%

\- EMAIL: 100%

\- IBAN: 100%



Performance was lower for:



\- PERSON

\- PHONE

\- COMPANY



COMPANY was the weakest body entity type, with only 16% full recall in English and 20% in Finnish.



The results also show why extraction and detection should be evaluated separately. The XLSX extractor can access metadata and hidden worksheets, while the detection benchmark measures how well the detector recognizes identifiers after extraction.



\## 8. Conclusion



The XLSX extraction pipeline successfully accesses visible content, hidden worksheets and workbook metadata.



For body-text detection, the Presidio baseline achieved:



\- English: 84%

\- Finnish: 82%

\- Combined: 83%



The strongest baseline performance was observed for DATE, EMAIL and IBAN. COMPANY, PERSON and PHONE require further improvement or additional recognizers/models.

