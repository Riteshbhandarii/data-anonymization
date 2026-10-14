\# Google Cloud Sensitive Data Protection



\## Overview



Google Cloud Sensitive Data Protection is a commercial tool for detecting and protecting sensitive information such as names, email addresses, phone numbers, and other personal data.



For this research, I tested its ability to detect sensitive information in different document formats using the Google Cloud DLP API.



\## Testing setup



I used a Google Cloud Free Trial project with the Sensitive Data Protection API enabled.



The tests were performed using Python and the google-cloud-dlp library.



I tested 10 synthetic documents:



\- 2 DOCX files

\- 2 PDF files

\- 2 XLSX files

\- 2 PPTX files

\- 2 CSV files



Each format included one English and one Finnish document.



The documents contained 98 labeled sensitive information items in total.



I used the default detection configuration with minimum likelihood set to POSSIBLE.



The tests used the content inspection API. I did not test automatic document redaction or file reconstruction.



\## File format support



| Format | English | Finnish |

|---|---|---|

| DOCX | Success | Success |

| PDF | Success | Success |

| XLSX | Success | Success |

| PPTX | Success | Success |

| CSV | Success | Success |



All 10 files were processed successfully without API errors.



\## Detection results



| Format | Total | Full | Partial | Missed | Coverage | Type-aware |

|---|---:|---:|---:|---:|---:|---:|

| DOCX | 24 | 14 | 1 | 9 | 58.33% | 54.17% |

| PDF | 24 | 10 | 4 | 10 | 41.67% | 41.67% |

| XLSX | 16 | 12 | 1 | 3 | 75.00% | 75.00% |

| PPTX | 16 | 10 | 0 | 6 | 62.50% | 56.25% |

| CSV | 18 | 9 | 2 | 7 | 50.00% | 50.00% |

| Total | 98 | 55 | 8 | 35 | 56.12% | 54.08% |



Full means the complete sensitive value was detected.



Partial means only part of the value was detected.



Missed means the value was not detected.



Type-aware detection also requires the detected information type to match the ground truth.



\## Results by information type



| Type | Full | Partial | Missed |

|---|---:|---:|---:|

| PERSON | 17 | 1 | 0 |

| EMAIL | 10 | 0 | 0 |

| PHONE | 9 | 0 | 1 |

| ADDRESS | 3 | 4 | 1 |

| COMPANY | 2 | 3 | 5 |

| DATE | 14 | 0 | 0 |

| IBAN | 0 | 0 | 10 |

| PERSONAL\_ID | 0 | 0 | 6 |

| PLATE | 0 | 0 | 6 |

| INVOICE | 0 | 0 | 6 |



Google performed well with common information types such as names, email addresses, phone numbers, and dates.



It performed less well with addresses and company names.



It did not detect the tested IBANs, personal IDs, license plates, or invoice numbers using this configuration.



These results do not prove that Google cannot detect these categories. Additional configuration or custom detectors may improve the results.



\## English and Finnish



English detection coverage was 61.22%.



Finnish detection coverage was 51.02%.



The English documents performed better in this small test set.



\## Comparison with other tools



For a fairer comparison, I used the eight files that were also successfully tested with Limina. DOCX files were excluded from this comparison.



| Tool | Total PII | Full | Coverage |

|---|---:|---:|---:|

| Google Cloud | 74 | 41 | 55.41% |

| Limina | 74 | 69 | 93.24% |

| Presidio | 74 | 45 | 60.81% |



Limina achieved the highest full detection coverage in this test.



The results are based on a small synthetic dataset. The tools also use different processing methods and configurations, so the comparison is not a general performance benchmark.



\## Strengths



\- Successfully inspected all five tested file formats.

\- Worked with both English and Finnish documents.

\- Detected common personal information well.

\- Provides an API that can be integrated into a Python workflow.

\- Supports configurable sensitive information detection.



\## Limitations



\- Some sensitive information types were missed using the tested configuration.

\- Company names and addresses were not always detected completely.

\- Detection results sometimes contained duplicate or overlapping findings.

\- The test did not evaluate anonymized output files or whether document formatting was preserved.

\- No detailed cost benchmark was performed.



\## Evaluation method



The evaluation compared Google DLP findings with labeled sensitive values in the test documents.



Text matching was case-insensitive and ignored whitespace differences.



Each labeled value was counted once, even if the API returned duplicate findings.



Only entities labeled as body content were included in the score. Hidden sheets, notes, and metadata were not included in the main metric.



The evaluation used normalized substring matching rather than exact text offsets. The reported scores should therefore be treated as approximate detection coverage on this test set.



\## Conclusion



Google Cloud Sensitive Data Protection was easy to integrate with Python and successfully processed all tested formats.



Its strongest results were for common personal information such as names, emails, dates, and phone numbers.



However, the default configuration missed several specialized identifiers that are important for our anonymization project.



Based on these tests, Google Cloud is a possible option for sensitive information detection, but additional configuration and redaction testing would be needed before using it as a complete document anonymization solution.

