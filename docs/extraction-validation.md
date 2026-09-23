# Extraction validation

This check measures whether known identifiers reach the extracted Markdown before anonymization. It uses documents from `corpus/generate.py` and their JSON labels. The current pipeline outputs Markdown.

## Recorded results

Run date: 2026-09-22. The same generated corpus was used for both measurements: `--n 5 --seed 42`, with Faker 40.39.0. This creates five documents per format per language (English and Finnish): 50 documents containing 650 labelled identifiers. The baseline reader was taken from commit `89ae121c440d4077ab6b594aaebfc17f307bf670` before the extraction fixes.

| Format | Documents | Identifiers planted | Returned before | Recall before | Returned after | Recall after |
|---|---:|---:|---:|---:|---:|---:|
| CSV | 10 | 90 | 90 | 100.00% | 90 | 100.00% |
| DOCX | 10 | 150 | 120 | 80.00% | 150 | 100.00% |
| PDF | 10 | 140 | 120 | 85.71% | 140 | 100.00% |
| PPTX | 10 | 140 | 120 | 85.71% | 140 | 100.00% |
| XLSX | 10 | 130 | 110 | 84.62% | 130 | 100.00% |
| **Total** | **50** | **650** | **560** | **86.15%** | **650** | **100.00%** |

The 90 labels missing before the fixes were all in document metadata. Speaker notes and hidden worksheets were already returned. Neither run had an extraction error.

| Format | Location | Identifiers planted | Returned before | Returned after |
|---|---|---:|---:|---:|
| CSV | Body | 90 | 90 | 90 |
| DOCX | Body | 120 | 120 | 120 |
| DOCX | Metadata | 30 | 0 | 30 |
| PDF | Body | 120 | 120 | 120 |
| PDF | Metadata | 20 | 0 | 20 |
| PPTX | Body | 80 | 80 | 80 |
| PPTX | Metadata | 20 | 0 | 20 |
| PPTX | Speaker notes | 40 | 40 | 40 |
| XLSX | Body / visible sheets | 80 | 80 | 80 |
| XLSX | Hidden worksheets | 30 | 30 | 30 |
| XLSX | Metadata | 20 | 0 | 20 |

These figures measure the labels in this generated corpus. The generator does not include Word headers/footers, mixed PDF image text, or cached formula results; separate regression fixtures cover those cases below.

## What is counted

- **Planted:** one entry in a document's JSON `entities` list. The same value labelled in both body and metadata counts separately for each location.
- **Returned:** that value occurs in the extracted Markdown section corresponding to its labelled location. A name found only in body text cannot satisfy a metadata label.
- **Recall:** returned labels divided by planted labels. Each label is counted once; this is a labelled-value check, not a count of every repeated occurrence or an anonymization score.
- **Matching:** normalize Unicode to NFC, collapse whitespace, and decode the reader's Markdown table line breaks and escaped pipes. Preserve spelling, case, and punctuation, then check for the complete label value as a substring.
- **Extraction errors:** keep the document and all its labels in the denominator with zero returned labels, and record the error in `details.json`.

The evaluator recognizes `## Document metadata`, `### Speaker notes`, and `## Sheet: <name>` headings. It reads XLSX sheet names and visibility only to classify the worksheet sections; identifier values are matched exclusively against the extracted Markdown. Other document sections count as body text. If a reader changes these headings, update `_text_by_location()` and its tests together.

## Run locally

From the repository root, install the validation dependencies:

```bash
python -m pip install -r requirements-validation.txt
```

Install Tesseract and its English language data, with `tesseract` available on `PATH`, to run the real OCR regression. On Ubuntu:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

Then run:

```bash
python -m ruff check corpus/ pipeline/ tests/
python -m unittest discover -s tests -v
python corpus/generate.py --out outputs/validation/corpus --n 5 --seed 42
python -m pipeline.validation outputs/validation/corpus --report-dir outputs/validation/report --min-recall 1.0
```

Faker is pinned in `requirements-validation.txt` because changing its version can change the generated identities even with the same seed. The generator itself is unchanged. An anonymization implementation is not required for these extraction checks.

The evaluation command writes:

| File in the report directory | Contents |
|---|---|
| `summary.md` | Readable format and location tables, plus extraction errors |
| `by_format.csv` | Document count, planted, returned, missing, and recall per format |
| `by_location.csv` | The same counts split by format and labelled location |
| `details.json` | Every document and label, its `returned` flag, and any extraction error |

Reports and generated documents are under the Git-ignored `outputs/` directory. The command exits with status 1 if any extraction fails or any format/location group is below `--min-recall`. Reports are still saved when that threshold fails. Invalid or empty label data exits with status 2.

## Regression coverage

The extraction validation run at `eac4092` passed all 20 tests in that revision, including the real OCR test with Tesseract 5.5.0 and English language data. Markdown normalization tests additionally check that hard breaks reach the anonymization module and survive output saving.

| Test file | Coverage |
|---|---|
| `tests/test_extraction_gaps.py` | Metadata in DOCX/PPTX/XLSX/PDF; Word primary, first-page, and even-page headers/footers with tables and linked sections; speaker notes and hidden worksheets; mixed PDF OCR including a real image-only identifier and rotated crop routing; scanned-page OCR; formula cached strings, empty strings, missing results, and error values |
| `tests/test_output_names.py` | Different source extensions, repeated filenames, exact saved text, and eight simultaneous writes without overwriting |
| `tests/test_normalization.py` | Space and backslash hard breaks, content-line indentation and trailing spaces, blank-line cleanup, and preservation through module handoff and output saving |
| `tests/test_validation.py` | Actual generator output in all five formats and both languages; separate body/metadata accounting; extraction errors and empty-corpus rejection; failing CLI status with reports still saved |

XLSX tests supply the cached values a spreadsheet application would save. The reader consumes those saved results; it does not recalculate formulas. Missing or erroneous caches produce an explicit error with the cell location and recalculation instructions.

## GitHub Actions

The `pipeline` job in `.github/workflows/ci.yml` runs on pull requests and pushes to `main`. It installs Tesseract, lints `corpus/`, `pipeline/`, and `tests/`, runs the regression tests, generates the 50-document corpus, and requires 100% labelled-value recall in each format/location group.

The real OCR test is skipped locally if Tesseract is missing; CI installs it so that test runs there. The recall table appears in the workflow's job summary. The four report files are available as the `extraction-validation-report` artifact, including when the recall threshold fails. Open the `pipeline` check on the pull request to view the run and its reports.
