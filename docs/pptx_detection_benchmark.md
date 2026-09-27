\# PPTX Extraction and Detection Benchmark



\## 1. Scope



The PPTX evaluation covers two separate stages:



1\. Extraction – whether text and identifiers can be extracted from slide content, speaker notes, and document metadata.

2\. Detection – how well Presidio detects identifiers from the extracted body text.



Speaker notes and metadata are evaluated as part of extraction and are not included in the detection recall denominator.



\## 2. Test Data



The generated PPTX corpus contains:



\- 25 English PPTX files

\- 25 Finnish PPTX files

\- 50 PPTX files in total



The PPTX ground truth contains:



\- 400 body identifiers

\- 300 non-body identifiers

\- 700 identifiers in total



The 300 non-body identifiers consist of:



\### English



\- 50 PERSON values in metadata

\- 25 IBAN values in speaker notes

\- 25 PERSON values in speaker notes

\- 25 PERSONAL\_ID values in speaker notes

\- 25 PHONE values in speaker notes



\### Finnish



\- 50 PERSON values in metadata

\- 25 IBAN values in speaker notes

\- 25 PERSON values in speaker notes

\- 25 PERSONAL\_ID values in speaker notes

\- 25 PHONE values in speaker notes



\## 3. Extraction



The PPTX extractor reads:



\- visible slide text

\- tables and text shapes

\- speaker notes

\- document metadata



A manual validation was performed using `en\_pptx\_00.pptx`.



The ground truth contained:



\- 8 body identifiers

\- 4 speaker-note identifiers

\- 2 metadata identifiers



The extractor successfully retrieved all of them.



Extraction coverage:



14 / 14 = 100%



The extractor also exposed additional document metadata such as:



`Comments: generated using python-pptx`



This demonstrates that information outside the visible slide content can also be recovered from a PPTX file.



\## 4. Detection Baseline



The detection baseline uses Presidio Analyzer with spaCy language models.



The benchmark evaluates only identifiers labelled as `body`.



Speaker notes and metadata are excluded from detection recall because they belong to the extraction stage.



A detection is classified as:



\- Full – the entire ground-truth value is covered

\- Partial – only part of the value is detected

\- Missed – no relevant detection covers the value



\## 5. English PPTX Results



| Entity | Total | Full | Partial | Missed | Full Recall |

|---|---:|---:|---:|---:|---:|

| ADDRESS | 25 | 0 | 15 | 10 | 0% |

| COMPANY | 25 | 9 | 7 | 9 | 36% |

| DATE | 25 | 25 | 0 | 0 | 100% |

| EMAIL | 25 | 25 | 0 | 0 | 100% |

| IBAN | 25 | 25 | 0 | 0 | 100% |

| INVOICE | 25 | 0 | 0 | 25 | 0% |

| PERSON | 25 | 24 | 0 | 1 | 96% |

| PHONE | 25 | 21 | 0 | 4 | 84% |



English total:



\- Ground truth: 200

\- Fully detected: 129

\- Partially detected: 22

\- Completely missed: 49



Full detection recall:



129 / 200 = 64.5%



\## 6. Finnish PPTX Results



| Entity | Total | Full | Partial | Missed | Full Recall |

|---|---:|---:|---:|---:|---:|

| ADDRESS | 25 | 0 | 17 | 8 | 0% |

| COMPANY | 25 | 2 | 5 | 18 | 8% |

| DATE | 25 | 25 | 0 | 0 | 100% |

| EMAIL | 25 | 25 | 0 | 0 | 100% |

| IBAN | 25 | 25 | 0 | 0 | 100% |

| INVOICE | 25 | 0 | 0 | 25 | 0% |

| PERSON | 25 | 24 | 0 | 1 | 96% |

| PHONE | 25 | 20 | 1 | 4 | 80% |



Finnish total:



\- Ground truth: 200

\- Fully detected: 121

\- Partially detected: 23

\- Completely missed: 56



Full detection recall:



121 / 200 = 60.5%



\## 7. Combined PPTX Results



Across English and Finnish:



\- Ground-truth body identifiers: 400

\- Fully detected: 250

\- Partially detected: 45

\- Completely missed: 105



Full detection recall:



250 / 400 = 62.5%



Partial detections:



45 / 400 = 11.25%



Completely missed:



105 / 400 = 26.25%



\## 8. Findings



The strongest results were observed for:



\- DATE: 100%

\- EMAIL: 100%

\- IBAN: 100%

\- PERSON: 96% in both languages



The weakest results were observed for:



\- ADDRESS: 0% full recall

\- INVOICE: 0% full recall

\- COMPANY: 36% in English and 8% in Finnish



PHONE detection was moderate:



\- English: 84%

\- Finnish: 80%



ADDRESS values were often only partially detected. This means that some parts of the address were recognized while other parts remained exposed.



INVOICE identifiers were completely missed because the baseline did not contain an appropriate recognizer for this identifier type.



The Finnish COMPANY result was particularly weak and indicates that organization detection needs further improvement.



\## 9. Extraction vs Detection



Extraction and detection should be evaluated separately.



For PPTX, extraction must first expose information from:



\- slides

\- speaker notes

\- metadata



Only after extraction can a detector attempt to identify sensitive information.



The successful extraction of speaker notes and metadata demonstrates why reading only visible slide text is not sufficient for document anonymization.



\## 10. Conclusion



The PPTX extraction implementation successfully retrieved visible slide text, speaker notes, and document metadata.



The validation file achieved:



14 / 14 = 100% extraction coverage.



For body identifier detection, the Presidio baseline achieved:



\- English: 64.5%

\- Finnish: 60.5%

\- Combined: 62.5%



Presidio performed well for structured identifiers such as DATE, EMAIL, and IBAN and also achieved high PERSON detection.



The main weaknesses were ADDRESS, COMPANY, and INVOICE detection.



These results provide a baseline that can later be compared with improved language models or additional custom recognizers.

