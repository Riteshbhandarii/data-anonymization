# Extraction validation

This check measures which labelled identifiers reach extracted Markdown before
detection and redaction. It evaluates actual documents from `corpus/generate.py`;
saved generator text and rendering evidence are never substituted for extractor
output. The current pipeline outputs Markdown.

## Current measured results

The 2026-09-29 run used `--n 5 --seed 42`, Faker 40.39.0, English and Finnish,
and Tesseract 5.5.0.20241111 with `eng+fin`. The expanded corpus contains 70
documents and 960 labels. Its label/text fingerprint is
`b74cc7d0b428bbb0b1021d1f404d0c89ea8c983e4e604221e26958d0c0e85727`.

| Format | Documents | Planted | Returned | Missing | Recall |
|---|---:|---:|---:|---:|---:|
| CSV | 10 | 90 | 90 | 0 | 100.00% |
| DOCX | 10 | 200 | 200 | 0 | 100.00% |
| PDF | 10 | 150 | 149 | 1 | 99.33% |
| PNG | 20 | 240 | 229 | 11 | 95.42% |
| PPTX | 10 | 150 | 150 | 0 | 100.00% |
| XLSX | 10 | 130 | 130 | 0 | 100.00% |
| **Total** | **70** | **960** | **948** | **12** | **98.75%** |

There were no extraction errors. All 12 missing labels were OCR mismatches:
one inside a PDF image and 11 in standalone PNG documents. The new locations
requested in issue #33 are measured separately:

| Format | Location | Planted | Returned | Recall |
|---|---|---:|---:|---:|
| DOCX | Header | 10 | 10 | 100.00% |
| DOCX | Footer | 10 | 10 | 100.00% |
| DOCX | Review comment | 20 | 20 | 100.00% |
| DOCX | Tracked change | 10 | 10 | 100.00% |
| PPTX | Embedded image | 10 | 10 | 100.00% |
| PDF | Embedded image | 10 | 9 | 90.00% |
| PNG | Body, clean | 120 | 113 | 94.17% |
| PNG | Body, low resolution | 120 | 116 | 96.67% |

The earlier 50-document result of 650/650 covered a smaller corpus without the
new review locations or image fixtures. It remains a historical result for that
corpus; it is not evidence of complete extraction on the expanded dataset. The
two totals should not be treated as a before/after comparison on identical data.

See [assigned-task-results.md](assigned-task-results.md) for the complete task
status, detector/full-pipeline comparison, environment, and remaining checks.
See [ocr-survey.md](ocr-survey.md) for the separate local OCR comparison.

## What is counted

- **Planted:** one entity entry in a document's label JSON. The same value at two
  labelled locations counts separately.
- **Returned:** the complete label value occurs in the Markdown region for its
  source location. A body match cannot satisfy a metadata or header label.
- **Recall:** returned labels divided by planted labels. This measures extraction
  of labelled values, not detection, redaction, or every repeated occurrence.
- **Matching:** normalize Unicode to NFC, collapse whitespace, and decode Markdown
  table breaks and escaped pipes. Preserve spelling, case and punctuation.
- **Errors:** retain all labels from a failed document in the denominator and
  record its error. An empty or invalid corpus cannot pass.
- **Coverage:** locations with no labels are shown as `N/A — no labels; not
  tested`. A location explicitly required by the command must have labels.

`location_ranges()` in `pipeline/validation.py` recognizes the extractor's
metadata, sheet, header/footer, review-comment, tracked-change, speaker-note,
and embedded-image section headings. It reads XLSX sheet names and visibility
only to classify sections. Label values are matched exclusively against extracted
Markdown. Update its tests when changing the reader's section conventions.

The verifier and evaluator have separate purposes. `corpus/verify.py` confirms
that the generator really planted its labels. For image fixtures it compares
actual pixels with a recorded rendering recipe and checks the document hash.
Passing this fixture check does not establish OCR accuracy.

## Reproduce

From the repository root:

```bash
python -m pip install -r requirements-validation.txt
```

Install Tesseract with English and Finnish language data and put `tesseract` on
`PATH`. For Ubuntu:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-fin
```

Run the checks and generate reports:

```bash
python -m ruff check corpus/ pipeline/ detect/ redact/ eval/ tests/
python -m unittest discover -s tests -v
python corpus/generate.py --out outputs/validation/corpus --n 5 --seed 42
python corpus/verify.py outputs/validation/corpus
python -m pipeline.validation outputs/validation/corpus --report-dir outputs/validation/report --ocr-language eng+fin --min-recall 1.0 --require-locations body,metadata,notes,hidden_sheet,header,footer,comment,tracked_change,embedded_image --threshold-qualities standard --threshold-locations body,metadata,notes,hidden_sheet,header,footer,comment,tracked_change
```

This is the CI acceptance configuration: deterministic text locations in
`standard` documents require 100% recall. Embedded-image OCR and standalone PNG
accuracy remain in every report, but their recognition scores do not gate the
build. Any extraction error or missing required location still fails, including
in a quality or location excluded from the recall threshold. Routing tests and
a real OCR regression separately check that image content reaches the OCR path.

To require 100% recall for every measured quality and location, omit both
`--threshold-qualities` and `--threshold-locations`. That stricter command fails
on the recorded corpus because it exposes the 12 OCR mismatches above. Neither
configuration removes difficult fixtures or changes their denominator.

An anonymizer implementation is not needed for extraction validation. Faker is
pinned; keep the generator revision, seed, versions and corpus fingerprint with
any reported comparison.

## Report files and CI

| Report file | Contents |
|---|---|
| `summary.md` | Format, location and quality tables, coverage, thresholds and errors |
| `by_format.csv` | Documents, planted, returned, missing and recall per format |
| `by_location.csv` | Counts per format and labelled location |
| `by_quality.csv` | Counts per format, image quality and location |
| `details.json` | Every document and label, returned flags, errors and acceptance settings |

Generated inputs and reports live under Git-ignored `outputs/`. The command
writes reports even when recall fails and exits with status 1 for failed
acceptance criteria. Invalid input, invalid threshold selections or an unusable
report destination return status 2.

GitHub Actions verifies generation separately from extraction. The pipeline job
installs Tesseract language data, lints code, runs regression tests, generates
and verifies the corpus, and applies the acceptance configuration above. It
publishes the Markdown summary and all five report files, including on failure.
The CI result says whether those declared checks passed; it does not mean OCR
or anonymization is perfect.

## Regression coverage

| Test file | Main coverage |
|---|---|
| `tests/test_corpus_locations.py` | Real generated locations, paired PNG qualities, reproducibility, stale/missing files, removed Word content, corrupted image evidence and unclipped Finnish text |
| `tests/test_extraction_gaps.py` | Metadata, header/footer stories, comments and revisions, speaker notes, hidden worksheets, mixed/scanned PDF OCR, image routing, and XLSX formula caches |
| `tests/test_validation.py` | Actual corpus extraction, location separation, required coverage, quality/location thresholds, and failures retained in reports |
| `tests/test_output_names.py` | Source-extension preservation, repeated filenames and concurrent saves |
| `tests/test_normalization.py` | Markdown hard breaks, indentation, trailing spaces and preservation through output |

Formula tests provide saved computed values, as a spreadsheet application does.
The reader does not calculate formulas; missing or erroneous caches produce an
explicit error with recalculation instructions. The real 8.9 MB PDF mentioned in
issue #15 was not available for this run, so the synthetic mixed-page checks do
not stand in for a result on that file.
