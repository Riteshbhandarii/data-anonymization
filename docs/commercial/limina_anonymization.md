# Limina – File Anonymization Research

## Overview

Limina provides an API for detecting and anonymizing sensitive information in text and document files.

For this project, I tested the Community API because it can process files directly and return both detected entities and a processed redacted file.

Only synthetic files from the existing project corpus were used during testing.

The main test set contained 10 files covering all five file formats used by the project:

- DOCX
- PDF
- XLSX
- PPTX
- CSV

For each format, one English and one Finnish file was tested.

## Test Setup

The Community API was tested through the file-processing endpoint using Base64-encoded files.

The test workflow was:

1. Read the synthetic source file.
2. Encode the file as Base64.
3. Submit the file to the Limina Community API.
4. Save the returned JSON response.
5. Decode and save the returned redacted file.
6. Compare detected entities against the project's ground-truth labels.
7. Check whether the processed file could still be opened and whether its basic structure was preserved.

The API key was stored in an environment variable and was not hardcoded into the test scripts.

## File Processing Results

Ten files were submitted in total.

| Format | English | Finnish |
|---|---|---|
| DOCX | HTTP 500 | HTTP 500 |
| PDF | Success | Success |
| XLSX | Success | Success |
| PPTX | Success | Success |
| CSV | Success | Success |

Eight of the ten project files were processed successfully.

### DOCX issue

Both project DOCX files returned:

`HTTP 500 Internal Server Error`

To check whether this was caused by the project corpus, I created a minimal synthetic DOCX containing only a name and email address.

The minimal DOCX also returned HTTP 500.

A separate `text/plain` smoke test using the same API key and endpoint returned HTTP 200 and correctly detected a name and an email address.

This suggests that the DOCX failures observed during testing were related to document processing rather than authentication, API-key configuration, or the project corpus itself.

Because the DOCX files were not processed, they were excluded from the detection accuracy comparison below.

## Detection Evaluation

Detection scoring used the eight successfully processed files:

- PDF English
- PDF Finnish
- XLSX English
- XLSX Finnish
- PPTX English
- PPTX Finnish
- CSV English
- CSV Finnish

These files contained **74 body-level ground-truth identifiers**.

Metadata, PowerPoint notes, and hidden Excel sheets were excluded from the 74-identifier denominator so that the scoring remained consistent with the project's existing body-only benchmark.

Two metrics were calculated.

### Redaction coverage

Redaction coverage measures whether the sensitive text was covered by any Limina detection, regardless of the entity category assigned by Limina.

| Result | Count |
|---|---:|
| Full coverage | 69/74 |
| Partial coverage | 5/74 |
| Missed | 0/74 |
| Full coverage rate | **93.24%** |

This means that every planted body identifier was detected at least partially.

### Type-aware detection

The stricter metric also required Limina's entity category to correspond to the expected project entity type.

The main mapping used for scoring was:

| Project entity | Limina entity |
|---|---|
| PERSON | `NAME` |
| EMAIL | `EMAIL_ADDRESS` |
| PHONE | `PHONE_NUMBER` |
| COMPANY | `ORGANIZATION` |
| ADDRESS | `LOCATION_ADDRESS`, `LOCATION_ADDRESS_STREET` |
| IBAN | `BANK_ACCOUNT` |
| DATE | `DATE`, `DOB` |
| PERSONAL_ID | `SSN` |
| PLATE | `VEHICLE_ID` |
| INVOICE | No exact project-equivalent entity |

The type-aware results were:

| Result | Count |
|---|---:|
| Full detection | 62/74 |
| Partial detection | 5/74 |
| Missed or wrong entity type | 7/74 |
| Full detection rate | **83.78%** |

The type-aware metric is more useful for comparing Limina with the project's Presidio baseline because it requires both the sensitive text and its entity category to be detected correctly.

## Results by File Format

### Redaction coverage

| Format | Full | Partial | Missed | Full coverage rate |
|---|---:|---:|---:|---:|
| CSV | 16/18 | 2/18 | 0/18 | 88.89% |
| PDF | 22/24 | 2/24 | 0/24 | 91.67% |
| PPTX | 15/16 | 1/16 | 0/16 | 93.75% |
| XLSX | 16/16 | 0/16 | 0/16 | 100.00% |

### Type-aware detection

| Format | Full | Partial | Missed | Full detection rate |
|---|---:|---:|---:|---:|
| CSV | 13/18 | 2/18 | 3/18 | 72.22% |
| PDF | 20/24 | 2/24 | 2/24 | 83.33% |
| PPTX | 13/16 | 1/16 | 2/16 | 81.25% |
| XLSX | 16/16 | 0/16 | 0/16 | 100.00% |

XLSX had the strongest result in this small sample, reaching 100% full type-aware detection for the body-level identifiers.

## Results by Language

### Redaction coverage

| Language | Full | Partial | Missed | Full coverage rate |
|---|---:|---:|---:|---:|
| English | 33/37 | 4/37 | 0/37 | 89.19% |
| Finnish | 36/37 | 1/37 | 0/37 | 97.30% |

### Type-aware detection

| Language | Full | Partial | Missed | Full detection rate |
|---|---:|---:|---:|---:|
| English | 29/37 | 4/37 | 4/37 | 78.38% |
| Finnish | 33/37 | 1/37 | 3/37 | 89.19% |

In this small sample, Finnish performed better than English.

However, the sample contains only four successfully processed files per language, so these percentages should not be treated as a general language benchmark.

## Results by Entity Type

The type-aware results by expected project entity were:

| Entity type | Full | Partial | Missed | Full detection rate |
|---|---:|---:|---:|---:|
| ADDRESS | 6/6 | 0 | 0 | 100.00% |
| COMPANY | 7/8 | 1 | 0 | 87.50% |
| DATE | 10/10 | 0 | 0 | 100.00% |
| EMAIL | 8/8 | 0 | 0 | 100.00% |
| IBAN | 6/8 | 0 | 2 | 75.00% |
| INVOICE | 0/4 | 0 | 4 | 0.00% |
| PERSON | 13/14 | 1 | 0 | 92.86% |
| PERSONAL_ID | 3/4 | 0 | 1 | 75.00% |
| PHONE | 5/8 | 3 | 0 | 62.50% |
| PLATE | 4/4 | 0 | 0 | 100.00% |

The strongest categories in the tested sample were addresses, dates, email addresses, and vehicle registration plates.

Phone numbers were often detected but were sometimes split into multiple entities, which caused partial rather than full detection.

## Entity Classification Issues

The difference between the 93.24% redaction coverage rate and the 83.78% type-aware detection rate came mainly from entity classification.

Seven identifiers were not counted as full type-aware detections.

### Invoice numbers

All four invoice numbers were covered during anonymization, but they were classified as `NUMERICAL_PII` instead of a dedicated invoice entity.

Examples included:

- `INV-23154`
- `INV-89320`
- `INV-25129`
- `INV-50988`

For redaction purposes, the sensitive text was still covered.

For the project's stricter entity-aware benchmark, these were counted as type mismatches.

### IBAN classification

Two CSV IBAN values were detected but classified as `ORGANIZATION` instead of `BANK_ACCOUNT`.

### Personal identity classification

One Finnish-style personal identity code in the English CSV file was detected as `ORGANIZATION` rather than `SSN`.

These cases demonstrate why it is useful to report both redaction coverage and type-aware detection.

## Hidden and Non-Body Content

An important result was Limina's ability to detect several planted identifiers outside the visible body content.

### Excel hidden sheets

In the English XLSX hidden sheet, Limina detected:

- Finnish-style personal identity code
- vehicle registration plate
- address

In the Finnish XLSX hidden sheet, Limina detected:

- Finnish-style personal identity code
- address
- vehicle registration plate

The Finnish hidden-sheet vehicle registration plate was detected as `ORGANIZATION`, so the text was found but the category was incorrect.

### PowerPoint metadata and notes

Limina also detected planted values from PowerPoint metadata and speaker notes.

Examples included:

- a planted person name from presentation metadata
- a planted personal identity code from presentation notes

These detections were not included in the 74-identifier body benchmark because the project's benchmark intentionally evaluates body labels separately from extraction of hidden content.

For the project's anonymization use case, the ability to detect hidden sheets, notes, and metadata is potentially valuable because sensitive information may exist outside the visible document body.

## Additional Detections

A small number of additional detections did not correspond directly to planted ground-truth identifiers.

Examples included:

- `US` classified as `LOCATION_COUNTRY`
- the Finnish word `Neljännesvuosi` classified as `DATE_INTERVAL`

These may represent broad contextual or structural detections rather than planted PII.

They were not counted as ground-truth successes.

## Language Detection

Language detection was also returned by the API.

Examples included:

- English PDF detected as English
- Finnish PDF detected as Finnish
- English PPTX detected primarily as English
- Finnish PPTX detected as Finnish, with additional lower-confidence language candidates

There were also inconsistent cases:

- the Finnish XLSX returned no detected language
- the Finnish CSV returned English rather than Finnish

This suggests that file anonymization could still work even when the language-detection output was incomplete or inaccurate.

## Structure Preservation

All eight successfully processed redacted files could be reopened after anonymization.

### PDF

Both redacted PDFs opened successfully.

| File | Original pages | Redacted pages |
|---|---:|---:|
| English PDF | 1 | 1 |
| Finnish PDF | 1 | 1 |

### XLSX

Both redacted workbooks opened successfully.

Sheet names were preserved.

The original hidden worksheet remained hidden after processing.

Workbook dimensions also remained unchanged.

For both English and Finnish XLSX files:

- visible worksheet remained visible
- `internal` worksheet remained hidden
- visible sheet dimensions remained 3 rows × 6 columns
- hidden sheet dimensions remained 2 rows × 3 columns

### PPTX

Both processed presentations opened successfully.

For both English and Finnish files:

- slides: 2 → 2
- shapes per slide: `[2, 2]` → `[2, 2]`

### CSV

Both CSV files preserved their basic table structure.

For both English and Finnish files:

- rows: 3 → 3
- columns: 8 → 8

These checks confirm that the tested files remained structurally readable after anonymization.

They do not prove that every visual formatting detail was preserved exactly, because no pixel-level visual comparison was performed.

## Like-for-like Comparison with Presidio

To provide a more direct comparison, the same eight files were also evaluated using the project's default Presidio baseline.

The comparison used:

- the same eight files
- the same 74 body-level identifiers
- English and Finnish
- PDF, XLSX, PPTX, and CSV
- no custom Presidio recognizers

The results were:

| Format | Limina type-aware | Presidio default | Difference |
|---|---:|---:|---:|
| CSV | 13/18 = 72.22% | 10/18 = 55.56% | +16.67 pp |
| PDF | 20/24 = 83.33% | 13/24 = 54.17% | +29.17 pp |
| PPTX | 13/16 = 81.25% | 10/16 = 62.50% | +18.75 pp |
| XLSX | 16/16 = 100.00% | 12/16 = 75.00% | +25.00 pp |
| **Overall** | **62/74 = 83.78%** | **45/74 = 60.81%** | **+22.97 pp** |

Presidio also produced 9 partial detections, compared with 5 partial detections from Limina.

On this small eight-document test set, Limina therefore achieved a 22.97 percentage point higher full type-aware detection rate than the default Presidio baseline.

This should still be treated as a representative comparison rather than a general accuracy benchmark.

The documents are synthetic, the sample is small, and the results may not represent performance on larger or more varied real-world datasets.

DOCX was not included in this comparison because Limina returned HTTP 500 for both tested DOCX files.

## Strengths

The strongest results observed during testing were:

- high overall redaction coverage
- strong type-aware detection compared with the default Presidio baseline
- direct processing of PDF, XLSX, PPTX, and CSV
- successful Finnish processing in the tested files
- detection of hidden Excel-sheet content
- detection of PowerPoint notes and metadata
- preservation of important document structure
- structured JSON entity output
- processed redacted files returned directly by the API

The hidden-content detection is particularly relevant to this project because sensitive information may exist outside the visible body of a document.

## Limitations

The most significant issue during testing was DOCX processing.

Both project DOCX files and a minimal synthetic DOCX returned HTTP 500.

Other limitations observed included:

- some phone numbers were only partially detected
- invoice numbers did not have a matching dedicated entity category
- some IBAN and personal identity values were assigned incorrect categories
- language detection was inconsistent for some Finnish structured files
- some additional contextual values were classified as potentially sensitive
- the Community API test was limited to a small synthetic corpus

## Overall Assessment

**Overall project fit: Very good for the successfully processed formats, with an important DOCX limitation observed during testing.**

Limina performed strongly on PDF, XLSX, PPTX, and CSV.

Across the eight successfully processed files, it achieved:

- **93.24% full redaction coverage**
- **83.78% full type-aware detection**

On the same eight files, the default Presidio baseline achieved **60.81%** full detection.

Limina also demonstrated useful behavior that is particularly relevant to the project, including detection of sensitive information in Excel hidden sheets, PowerPoint notes, and PowerPoint metadata.

The processed PDF, XLSX, PPTX, and CSV files remained structurally readable after anonymization.

The main concern is DOCX reliability. During this test session, both project DOCX files and a minimal synthetic DOCX returned HTTP 500, even though other requests using the same API key and endpoint succeeded.

For this project, Limina appears promising as a commercial anonymization component, especially for structured Office documents and files containing hidden content, but the DOCX processing issue would need to be resolved or investigated before considering it a complete solution.
