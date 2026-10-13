# Azure AI Language – Document PII Redaction

## Overview

Azure AI Language provides a PII detection and redaction service that can identify sensitive information from documents and create a redacted version of the original file.

For this project, I tested the native Document PII workflow because it is the most relevant Azure service for anonymizing files before they are sent to an AI system.

The testing was done using an Azure for Students subscription. The setup included an Azure Language resource, Azure Blob Storage, private input and output containers, and SAS URLs for temporary file access.

Only synthetic files from our existing project corpus were uploaded to Azure during testing.

This was a small representative test rather than a full benchmark. I tested 4 documents in total: one English DOCX, one Finnish DOCX, one English PDF, and one Finnish PDF. Each document contained 12 expected identifiers, giving 48 identifiers in total.

Because the sample size is small, one additional miss changes the result for a single document by about 8.3 percentage points. The percentages below should therefore be read as example test results, not as a statistically reliable benchmark of Azure performance.

## Test Setup

The test workflow was:

1. Upload a synthetic test file to the private Azure Blob Storage input container.
2. Generate a read-only SAS URL for the input file.
3. Generate a SAS URL for the output container.
4. Submit the file to the Azure Document PII API.
5. Wait for the asynchronous processing job to finish.
6. Download the redacted document and the JSON result.
7. Compare the output with the identifiers that were present in the original test file.

For supported files, Azure produced two outputs:

- a redacted copy of the original document
- a JSON file containing the detected entities, entity types, and confidence scores

The API returned model version `2025-11-01` during the tests.

## File Format Support

I tested all five file formats used in our project corpus.

| Format | Native support | Result |
|---|---|---|
| DOCX | Yes | Successfully processed |
| PDF | Yes | Successfully processed |
| PPTX | No | Rejected by API |
| XLSX | No | Rejected by API |
| CSV | No | Rejected by API |

When PPTX, XLSX, and CSV files were submitted, the API returned the following limitation:

`Supported types: .txt, .pdf, .docx`

This means that PowerPoint, Excel, and CSV files would need an additional extraction or conversion step before they could be processed with this Azure workflow.

## Detection Results

For the supported formats, I tested one English and one Finnish document for both DOCX and PDF.

The table below uses **redaction coverage**. An identifier counts as fully covered when its complete text span was redacted, even if Azure assigned the wrong entity type.

| Test file | Language | Full coverage | Partial | Missed | Full coverage rate |
|---|---|---:|---:|---:|---:|
| DOCX | English | 9/12 | 1/12 | 2/12 | 75.00% |
| DOCX | Finnish | 8/12 | 0/12 | 4/12 | 66.67% |
| PDF | English | 9/12 | 0/12 | 3/12 | 75.00% |
| PDF | Finnish | 9/12 | 0/12 | 3/12 | 75.00% |

Across the 48 expected identifiers in these four documents, Azure fully redacted 35, partially redacted 1, and missed 12.

These numbers describe whether sensitive text was covered, not whether Azure assigned the correct entity category. This distinction matters because some identifiers were redacted under the wrong type.

The service generally handled common PII well in these samples, including:

- person names
- email addresses
- phone numbers
- postal addresses
- IBAN numbers
- dates

The service also preserved the main structure of the DOCX and PDF documents after redaction.

## Like-for-like Comparison with Presidio

To provide a small like-for-like comparison, I also ran the same four documents through the project's default Presidio baseline using the same strict full/partial coverage rules.

For this comparison, the detected entity also had to match the expected entity type. This changes two Azure results:

- the personal identity code in the English DOCX was fully redacted but classified as `PhoneNumber`
- the company in the English PDF was fully covered by several `Person` detections instead of being identified as a company or organization

With entity type taken into account, the results were:

| Tool | Full | Partial | Missed | Full detection rate |
|---|---:|---:|---:|---:|
| Azure Document PII | 33/48 | 1/48 | 14/48 | 68.75% |
| Presidio default baseline | 27/48 | 5/48 | 16/48 | 56.25% |

On this four-document sample, Azure had a 12.5 percentage point higher full detection rate than the default Presidio baseline.

This is still only a small representative comparison, not a general performance benchmark. With only 48 expected identifiers, individual detections have a noticeable effect on the percentages.

## English DOCX

The English DOCX test reached a full redaction coverage rate of **75.00%**.

Azure correctly redacted names, email, company name, address, IBAN, dates, and the Finnish-style personal identity code.

However, the telephone number was only partially redacted. The invoice number and vehicle registration plate were not detected.

The personal identity code was redacted, but Azure classified it as a `PhoneNumber` instead of a personal identity identifier. This is an important limitation because the code was caught due to matching another entity type rather than through a dedicated personal identity recognizer.

## Finnish DOCX

The Finnish DOCX test had the lowest result, with **66.67%** full redaction coverage.

Names, email, telephone number, address, IBAN, and dates were successfully redacted.

The following identifiers were missed:

- company name
- invoice number
- Finnish personal identity code
- vehicle registration plate

There was also one clear false positive. The Finnish word `laatija`, meaning approximately "author" or "prepared by", was detected as a `PersonType` and was unnecessarily redacted.

## English PDF

The English PDF reached **75.00%** full redaction coverage.

Azure successfully redacted names, email, phone number, address, IBAN, and dates.

The company name was also fully covered, although Azure interpreted its individual words as person names rather than as one organization.

For the type-aware Presidio comparison above, this therefore counts as a miss for the expected company entity even though the sensitive text itself was redacted.

The following identifiers were missed:

- invoice number
- personal identity code
- vehicle registration plate

The redacted PDF remained readable and the main document layout was preserved.

## Finnish PDF

The Finnish PDF also reached **75.00%** full redaction coverage.

Azure correctly detected:

- two person names
- email
- organization
- telephone number
- postal address
- IBAN
- dates

The following identifiers were missed:

- invoice number
- Finnish personal identity code
- vehicle registration plate

The same `laatija` false positive seen in the Finnish DOCX appeared again. Azure classified the word as `PersonType`.

## Strengths

Azure handled common PII categories reasonably well in the files tested and was able to create usable redacted DOCX and PDF files without requiring us to rebuild the documents ourselves.

Another useful feature is that the service provides both the redacted document and a structured JSON result.

The JSON includes:

- detected text
- entity category
- confidence score

This makes the output easier to inspect and could also make integration into a larger anonymization pipeline easier.

The API workflow worked consistently once the Azure resources and Blob Storage permissions were configured.

## Limitations

The biggest limitation for our project is file format coverage.

The native workflow only accepted:

- `.txt`
- `.pdf`
- `.docx`

Our project also includes:

- `.csv`
- `.xlsx`
- `.pptx`

This means Azure alone cannot directly cover the complete file-format scope.

The tests also showed weaknesses with project-specific identifiers.

Invoice numbers and vehicle registration plates were repeatedly missed.

Finnish personal identity codes were inconsistent:

- one English test document had its personal identity code redacted, but it was classified as a phone number
- the Finnish DOCX and PDF examples were not detected at all

There were also language-specific false positives.

In both Finnish document tests, the normal Finnish word `laatija` was incorrectly treated as sensitive information.

## Setup and Usability

The service itself was straightforward to call through Python, but the initial setup required several Azure components:

- Azure Language resource
- Azure Storage account
- input and output Blob containers
- SAS URLs
- Azure API endpoint
- Azure API key

The SAS URLs also needed a sufficiently long expiry time for the native document processing job.

Because of this, Azure seems more suitable for an automated backend pipeline than for a user who simply wants to upload a file and anonymize it manually.

## Overall Assessment

Azure AI Language Document PII works well as a cloud-based anonymization component for DOCX and PDF files.

In the small type-aware comparison on the same four documents, Azure reached **68.75%** full detection compared with **56.25%** for the default Presidio baseline. Because the sample contains only four documents, this should be treated as an illustrative comparison rather than evidence that Azure is generally more accurate.

Its strongest area in these tests was standard PII such as:

- names
- emails
- phone numbers
- addresses
- bank account numbers
- dates

It also preserved the original document format reasonably well and provided structured detection results.

However, it is not a complete solution for our project by itself because PPTX, XLSX, and CSV are not supported by the native document API.

The detection of Finland-specific identifiers also needs improvement, particularly Finnish personal identity codes.

Invoice numbers and vehicle registration plates would most likely require additional custom detection logic.

For our project, I would consider Azure a good option for DOCX and PDF processing, but it would need to be combined with extraction or conversion tools and additional recognizers to support the complete anonymization pipeline.

## Project Fit

**Overall fit: Good, but not complete**

Best use cases:

- DOCX redaction
- PDF redaction
- standard PII detection
- automated cloud-based workflows

Additional work required for:

- CSV
- XLSX
- PPTX
- Finnish personal identity codes
- invoice numbers
- vehicle registration plates