\# PDF Extraction and Detection Benchmark



\## 1. Scope



The PDF evaluation covers two separate stages:



1\. Extraction – whether visible PDF text and document metadata can be extracted.

2\. Detection – how well Presidio detects identifiers from the extracted body text.



Metadata identifiers are evaluated as part of extraction and are not included in the detection recall denominator.



The current corpus contains native-text PDFs. Scanned PDFs requiring OCR are not evaluated in this benchmark.



\## 2. Test Data



The generated PDF corpus contains:



\- 25 English PDF files

\- 25 Finnish PDF files

\- 50 PDF files in total



The PDF ground truth contains:



\- 600 body identifiers

\- 100 metadata identifiers

\- 700 identifiers in total



The metadata identifiers consist of:



\### English



\- 25 PERSON values

\- 25 EMAIL values



\### Finnish



\- 25 PERSON values

\- 25 EMAIL values



\## 3. Extraction



The PDF extractor uses PyMuPDF and extracts:



\- native page text

\- title

\- author

\- subject

\- keywords

\- creator

\- producer

\- creation date

\- modification date



A manual validation was performed using `en\_pdf\_00.pdf`.



The ground truth contained:



\- 12 body identifiers

\- 2 metadata identifiers



The extractor successfully retrieved all 14 identifiers.



Extraction coverage:



14 / 14 = 100%



The extractor also exposed additional metadata such as:



\- Title: Quarterly operations review

\- Creator: anonymous

\- Producer: ReportLab PDF Library - (opensource)

\- creation and modification timestamps



This demonstrates that sensitive or identifying information may exist outside the visible PDF text.



\## 4. Detection Baseline



The detection baseline uses Presidio Analyzer with spaCy language models.



Only identifiers labelled as `body` are included in detection recall.



Metadata identifiers are excluded because discovering metadata belongs to the extraction stage.



Detection results are classified as:



\- Full – the whole ground-truth value was detected

\- Partial – only part of the value was detected

\- Missed – the value was not detected



\## 5. English PDF Results



| Entity | Total | Full | Partial | Missed | Full Recall |

|---|---:|---:|---:|---:|---:|

| ADDRESS | 25 | 0 | 16 | 9 | 0% |

| COMPANY | 25 | 15 | 5 | 5 | 60% |

| DATE | 50 | 50 | 0 | 0 | 100% |

| EMAIL | 25 | 25 | 0 | 0 | 100% |

| IBAN | 25 | 25 | 0 | 0 | 100% |

| INVOICE | 25 | 0 | 0 | 25 | 0% |

| PERSON | 50 | 44 | 2 | 4 | 88% |

| PERSONAL\_ID | 25 | 0 | 0 | 25 | 0% |

| PHONE | 25 | 21 | 0 | 4 | 84% |

| PLATE | 25 | 0 | 0 | 25 | 0% |



English totals:



\- Ground truth: 300

\- Fully detected: 180

\- Partially detected: 23

\- Completely missed: 97



Full detection recall:



180 / 300 = 60%



Partial detections:



23 / 300 = 7.67%



Completely missed:



97 / 300 = 32.33%



\## 6. Finnish PDF Results



| Entity | Total | Full | Partial | Missed | Full Recall |

|---|---:|---:|---:|---:|---:|

| ADDRESS | 25 | 0 | 16 | 9 | 0% |

| COMPANY | 25 | 5 | 1 | 19 | 20% |

| DATE | 50 | 50 | 0 | 0 | 100% |

| EMAIL | 25 | 25 | 0 | 0 | 100% |

| IBAN | 25 | 25 | 0 | 0 | 100% |

| INVOICE | 25 | 0 | 0 | 25 | 0% |

| PERSON | 50 | 45 | 3 | 2 | 90% |

| PERSONAL\_ID | 25 | 0 | 0 | 25 | 0% |

| PHONE | 25 | 22 | 0 | 3 | 88% |

| PLATE | 25 | 0 | 0 | 25 | 0% |



Finnish totals:



\- Ground truth: 300

\- Fully detected: 172

\- Partially detected: 20

\- Completely missed: 108



Full detection recall:



172 / 300 = 57.33%



Partial detections:



20 / 300 = 6.67%



Completely missed:



108 / 300 = 36%



\## 7. Combined PDF Results



Across English and Finnish:



\- Ground-truth body identifiers: 600

\- Fully detected: 352

\- Partially detected: 43

\- Completely missed: 205



Full detection recall:



352 / 600 = 58.67%



Partial detections:



43 / 600 = 7.17%



Completely missed:



205 / 600 = 34.17%



\## 8. Findings



The strongest baseline results were:



\- DATE: 100%

\- EMAIL: 100%

\- IBAN: 100%



PERSON and PHONE also achieved relatively high detection:



\- PERSON: 88% English and 90% Finnish

\- PHONE: 84% English and 88% Finnish



The weakest results were:



\- ADDRESS: 0% full detection

\- INVOICE: 0%

\- PERSONAL\_ID: 0%

\- PLATE: 0%



Addresses were often partially detected, meaning some address information remained outside the detected span.



INVOICE, PERSONAL\_ID and PLATE received 0% full recall in this baseline because suitable recognizers were not available in the baseline configuration used on this branch.



COMPANY detection also showed a large language difference:



\- English: 60%

\- Finnish: 20%



This indicates that organization detection requires further improvement, especially for Finnish.



\## 9. Extraction vs Detection



Extraction and detection measure different parts of the pipeline.



The extractor must first expose information stored in:



\- page text

\- document metadata



After extraction, the detector determines whether those values contain sensitive information.



For this reason, metadata identifiers are reported under extraction and are not added to the detection recall denominator.



\## 10. Limitations



The current PDF corpus contains native-text PDFs.



Scanned PDFs and image-only PDFs would require an OCR stage before the same detection process could be applied. OCR performance is therefore outside the scope of this benchmark.



The results also represent the current Presidio baseline. Custom recognizers or different language models may change the detection results.



\## 11. Conclusion



The PDF extraction implementation successfully retrieved native page text and document metadata.



The validation file achieved:



14 / 14 = 100% extraction coverage.



For body identifier detection, the Presidio baseline achieved:



\- English: 60%

\- Finnish: 57.33%

\- Combined: 58.67%



The baseline performed very well for DATE, EMAIL and IBAN, while ADDRESS, COMPANY, INVOICE, PERSONAL\_ID and PLATE require further improvement.



These results provide a baseline for comparison with improved detection models and custom recognizers.

