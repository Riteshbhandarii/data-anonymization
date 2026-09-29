# Assigned tasks: implementation and measured results

This records the work for issues #12, #13, #15, #16, #17, #18, #19, #31 and
#33, using the expanded synthetic corpus on 2026-09-29. Implementations and
measurements are separate below so an available test harness is not mistaken
for an experiment that has already been run. Issues remain open for review.

The additional synthetic corpus from Teams has now been evaluated separately;
see [Teams corpus validation](#teams-corpus-validation). The specific real PDF
referenced in issue #15 remains unavailable and is not covered by either run.

## Task status and handoff

| Issue | Delivered | Review or remaining dependency |
|---|---|---|
| [#12: Image verification](https://github.com/Riteshbhandarii/data-anonymization/issues/12) | Image-aware verification checks rendering recipes against the source hash and actual pixels; no binary image is decoded as UTF-8. The 70-document corpus verifies successfully. | Ready for review; fixture verification and OCR accuracy remain separate measurements. |
| [#13: Synthetic images](https://github.com/Riteshbhandarii/data-anonymization/issues/13) | PNG writer registered with clean and half-resolution variants, complete unwrapped lines, English/Finnish labels and saved body text. | Ready for review on Windows and CI; no Apple Silicon machine was available to validate its Tesseract installation. |
| [#15: Extraction gaps](https://github.com/Riteshbhandarii/data-anonymization/issues/15) | Metadata, Word headers/footers, image OCR on mixed PDF pages, and saved XLSX formula values are handled and tested. | The specific 8.9 MB PDF from `corpus/real` was unavailable. OCR mismatches are recorded below. |
| [#16: Full pipeline benchmark](https://github.com/Riteshbhandarii/data-anonymization/issues/16) | Actual source documents run through extraction, detection, redaction and output; reports compare the same body-label denominator and show every additional location separately. | Review measured detection gaps; this run does not change the detector's configuration to improve its score. |
| [#17: Redaction stage](https://github.com/Riteshbhandarii/data-anonymization/issues/17) | Validated character spans feed Presidio replacements or consistent pseudonyms. A caller can explicitly share an alias map across documents. The pipeline saves the returned Markdown. | Ready for integration review; detector quality is measured independently from replacement behavior. |
| [#18: Re-identification harness](https://github.com/Riteshbhandarii/data-anonymization/issues/18) | Offline-tested harness includes raw/unrelated controls, naming, attributes, linkage, web-search recording and correct/wrong/refused/error outcomes. An actual local preparation created 84 requests. | External-model execution and its results are pending; no model API requests were made. |
| [#19: Utility comparison](https://github.com/Riteshbhandarii/data-anonymization/issues/19) | The same reviewed questions are prepared for raw, redacted and pseudonymized variants, including relationship questions. | Harness and prepared inputs are available; no measured external-model utility score is claimed. |
| [#31: OCR comparison](https://github.com/Riteshbhandarii/data-anonymization/issues/31) | Local OCR benchmark and option survey cover Tesseract, EasyOCR, PaddleOCR and cloud language/deployment support. Local measurements use identical generated images. | See [OCR results](ocr-survey.md) for completed measurements and engine errors. Cloud accuracy was not measured because no billable API calls were made. |
| [#33: Corpus locations](https://github.com/Riteshbhandarii/data-anonymization/issues/33) | Generator, verifier, extractor and reports now cover header, footer, comment, tracked change and embedded image, with distinct location-only identifiers. | Expanded corpus measured below; one PDF image identifier and 11 standalone image identifiers remain OCR misses. |

The primary integration description is [pipeline.md](pipeline.md). The detector
receives exactly the normalized Markdown on which its Python character offsets
are defined. The redactor edits those spans without changing the text first;
the pipeline saves the returned Markdown. See [redact/README.md](../redact/README.md)
for replacement modes, overlap handling and alias-map lifetime.

## Corpus and environment

The canonical local input is `outputs/assigned-validation/corpus`, generated with
`--n 5 --seed 42` and Faker 40.39.0. It contains 70 documents, 960 labels, and
230 labels outside ordinary body text. Twenty documents are paired PNG quality
variants; the other 50 cover CSV, DOCX, PDF, PPTX and XLSX in English and Finnish.

The manifest label/text fingerprint is:

```text
b74cc7d0b428bbb0b1021d1f404d0c89ea8c983e4e604221e26958d0c0e85727
```

The full-pipeline report additionally records the source artifact fingerprint
`8a95749439f3884dd9564b67487c6e8ef28c22a3cfa71bfb0d8e1d545ec94838`.
This binds that run to the actual document bytes; it differs from the corpus
fingerprint, which follows the existing label-and-saved-text convention.

| Component | Recorded version or setting |
|---|---|
| Platform / Python | Windows 11 / Python 3.12.6 |
| Presidio analyzer / anonymizer | 2.2.364 / 2.2.364 |
| spaCy | 3.8.16 |
| English / Finnish model | `en_core_web_sm` 3.8.0 / `fi_core_news_sm` 3.8.0 |
| Detector threshold | 0.0, matching the existing detector baseline |
| OCR | Tesseract 5.5.0.20241111, `eng+fin` |
| PyMuPDF / pytesseract | 1.28.2 / 0.3.13 |
| python-docx / python-pptx / openpyxl | 1.1.2 / 1.0.2 / 3.1.5 |

## Extraction results

These values come from `outputs/assigned-validation/extraction/by_format.csv`.

| Format | Documents | Planted | Returned | Missing | Recall |
|---|---:|---:|---:|---:|---:|
| CSV | 10 | 90 | 90 | 0 | 100.00% |
| DOCX | 10 | 200 | 200 | 0 | 100.00% |
| PDF | 10 | 150 | 149 | 1 | 99.33% |
| PNG | 20 | 240 | 229 | 11 | 95.42% |
| PPTX | 10 | 150 | 150 | 0 | 100.00% |
| XLSX | 10 | 130 | 130 | 0 | 100.00% |
| **Total** | **70** | **960** | **948** | **12** | **98.75%** |

Extraction completed without errors. DOCX header/footer labels were each 10/10,
comments 20/20, and tracked changes 10/10. PPTX embedded-image labels were 10/10;
PDF embedded-image labels were 9/10. Standalone PNG results were 113/120 for
clean images and 116/120 for half-resolution images. Resizing happens to improve
some samples; this small printed-text corpus does not establish a general
relationship between image degradation and OCR quality.

The previous 650/650 result used an older 50-document corpus without these
locations and images. It is not a perfect-score baseline for the expanded
corpus. [Extraction validation](extraction-validation.md) describes location-aware
matching, individual report files, and the difference between verification and
measurement.

## Teams corpus validation

On 2026-09-29, the supplied `General / Datasets / anonymization-corpus` archive
was downloaded from the project's Teams group and evaluated with extraction
code at `58af1ae`. The five document-format folders and their original JSON
labels were read locally; the external detector datasets were excluded.

The archive contains **500 source documents and 6,500 labels**, with 250 English
and 250 Finnish documents. Its `DATASETS.md` still describes 50 documents and
650 labels. It contains no `index.csv` or saved body-text sidecars. The local
run derived an index only from the supplied labels and checked that every
source document had exactly one label file. It did not regenerate documents,
change labels, or manufacture missing reference text. Original file hashes
were checked again after extraction.

| Format | Documents | Supplied labels | Returned | Missing | Recall |
|---|---:|---:|---:|---:|---:|
| CSV | 100 | 900 | 900 | 0 | 100.00% |
| DOCX | 100 | 1500 | 1500 | 0 | 100.00% |
| PDF | 100 | 1400 | 1400 | 0 | 100.00% |
| PPTX | 100 | 1400 | 1400 | 0 | 100.00% |
| XLSX | 100 | 1300 | 1298 | 2 | 99.85% |
| **Total** | **500** | **6500** | **6498** | **2** | **99.97%** |

Extraction completed without errors. All 4,900 body labels, 400 speaker-note
labels and 300 hidden-sheet labels were returned. Metadata matched 898/900.
Both metadata mismatches are in `xlsx/en_xlsx_00.xlsx` and
`xlsx/en_xlsx_05.xlsx`: the expected synthetic value is absent from the original
`docProps/core.xml`, whose `lastModifiedBy` field contains a different editor
value. Independent source-location verification reports the same two
mismatches. The expected values occur in worksheet strings, but body matches
cannot satisfy metadata labels. These are source/label inconsistencies, not
evidence that the extractor omitted an existing metadata value. They remain in
the original denominator; the supplied labels do not pass a strict 100% gate.
The dataset owner should confirm the intended metadata and labels. Raw editor
metadata and mismatch evidence remain local.

This corpus exercised body text, metadata, notes and hidden worksheets. It has
no supplied labels for headers, footers, comments, tracked changes or embedded
images, and no standalone image files. The measured run made **zero OCR calls**.
It therefore does not resolve the separate image OCR misses or validate the
8.9 MB real PDF, which is absent from this archive. These results measure
extraction before anonymization, not detector or redaction quality.

Archive SHA-256:
`d22b1234e6e874731f87ea8c431a4bbf0a6b793d77c20ed3683216e265ebc106`.
The 500-document source fingerprint is
`e929fbdee512bf4acb458426f3a050822e105ffb83ef7028a82062a93c3a3981`;
its definition and per-file hashes are recorded in the local provenance.
Reports are in `outputs/assigned-validation/teams-extraction`, alongside
`provenance.json`, `source-label-verification.json`, `source-hashes.csv`, and
`xlsx-metadata-mismatch-evidence.json`. The preserved inputs are in
`outputs/assigned-validation/teams-corpus`.

To measure a local copy with the same acceptance criteria:

```bash
python -m pipeline.validation outputs/assigned-validation/teams-corpus --report-dir outputs/validation/teams --ocr-language eng+fin --require-locations body,metadata,notes,hidden_sheet --min-recall 1.0
```

## Detector-only and full pipeline results

The same Presidio configuration ran against saved body text and against text
extracted from the actual documents. The comparison below keeps the same 730
body labels in both denominators:

| Input to detector | Body labels | Whole | Partial | Missed | Whole recall |
|---|---:|---:|---:|---:|---:|
| Generator's saved body text | 730 | 452 | 62 | 216 | 61.92% |
| Markdown extracted from documents | 730 | 444 | 62 | 224 | 60.82% |

The difference is 1.10 percentage points on this run. It reflects extraction
loss and changed detector context/formatting together; it is not purely a count
of missing characters. For example, OCR loses some body identifiers, while
formatting changes can also make a detector find identifiers it missed in the
plain saved text.

Including all document locations, the full pipeline produced these results:

| Format | Labels | Whole | Partial | Missed | Whole recall |
|---|---:|---:|---:|---:|---:|
| CSV | 90 | 47 | 11 | 32 | 52.22% |
| DOCX | 200 | 136 | 16 | 48 | 68.00% |
| PDF | 150 | 98 | 8 | 44 | 65.33% |
| PNG | 240 | 141 | 18 | 81 | 58.75% |
| PPTX | 150 | 98 | 12 | 40 | 65.33% |
| XLSX | 130 | 83 | 5 | 42 | 63.85% |
| **Total** | **960** | **603** | **70** | **287** | **62.81%** |

There were no document/stage errors. These are type-aware detection coverage
scores on the text that feeds redaction. A whole result requires complete
coverage of every observed occurrence, together with the minimum expected
occurrence count. Partial coverage does not count as whole, and content missing
from extraction is never counted as successfully detected or redacted. Body
occurrence counts come from saved generator text; other locations have a minimum
of one occurrence per label, because the source labels do not enumerate every
repeat. Per-location, quality, type and occurrence details remain in the report.

The reader returning 948 labels and the detector fully covering 603 labels are
different measurements. They should not be presented as one anonymization
success rate or as evidence that remaining text cannot identify someone.

## Reproduce the local measurements

Install `requirements-evaluation.txt`, the two spaCy models, and Tesseract with
English/Finnish language data as described in [eval/README.md](../eval/README.md).
Then run from the repository root:

```bash
python corpus/generate.py --out outputs/validation/corpus --n 5 --seed 42
python corpus/verify.py outputs/validation/corpus
python -m pipeline.validation outputs/validation/corpus --report-dir outputs/validation/extraction --ocr-language eng+fin --min-recall 1.0 --require-locations body,metadata,notes,hidden_sheet,header,footer,comment,tracked_change,embedded_image --threshold-qualities standard --threshold-locations body,metadata,notes,hidden_sheet,header,footer,comment,tracked_change
python -m eval.pipeline_bench outputs/validation/corpus --report-dir outputs/validation/pipeline --ocr-language eng+fin
```

CI requires 100% recall for the listed non-OCR locations in `standard`
documents. Image recognition results are reported without assuming perfect OCR.
All required locations, including embedded images, must have labels; all
extraction errors remain fatal. Image-routing tests and real known-text OCR
regressions for standalone PNG and embedded PDF/PPTX pixels also run. Omitting
the two threshold-selection flags
instead gates all quality/location groups and fails on this run's 12 OCR misses.

Generated reports are ignored by Git. The recorded local directories are
`outputs/assigned-validation/extraction` and `outputs/assigned-validation/pipeline`.
CI publishes extraction CSV/JSON and summary artifacts. Corpus fingerprints,
model versions and matching rules must agree before comparing another run.

## Model study preparation

`outputs/assigned-validation/study-v2` contains the current fictional study and
locally prepared plan: three Markdown documents, two organisations, and 84
requests across raw, redacted and pseudonymized variants. Local preparation used
the real Presidio detector. The dry run printed the request count and made no API
calls. Fixture document IDs are excluded from their content so ID prefixes do
not reveal the intended same-organisation linkage answer.

Offline tests verify controls, exact answer scoring, refusals, malformed results,
request limits, and the distinction between attempted and completed web search.
They establish that the harness handles those cases; they do not measure an
external model's re-identification ability or utility. Actual experiment
execution and scores for #18/#19 remain pending. See
[model-evaluation.md](model-evaluation.md) for the experiment schema and execution
workflow, and [ocr-survey.md](ocr-survey.md) for the separate OCR comparison.
