# OCR comparison for the document pipeline

This evaluates issue #31 using the generated PNG corpus from issue #13. The
comparison reads the same image bytes through each local OCR engine and measures
the text returned, before detection or redaction. It does not change the default
pipeline reader.

## Finnish support and deployment

The following support information was checked against the providers' own
documentation on 2026-09-29. Language support does not imply perfect recognition.

| Engine | Deployment | Finnish support | Evaluation configuration |
|---|---|---|---|
| Tesseract | Local executable, Python wrapper | `fin` trained data is available. [Language table](https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html) | 5.5.0.20241111, `eng+fin`, CPU |
| PaddleOCR | Local Python models | PP-OCRv5 lists `fi` in its multilingual Latin recognition model. [Model and language table](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md) | PaddleOCR 3.4.0, PaddlePaddle 3.3.1, explicit mobile detector and Finnish-capable Latin recognizer, CPU |
| EasyOCR | Local Python models | Its language list does not include `fi`. The Latin model has overlapping characters. [Official configuration](https://github.com/JaidedAI/EasyOCR/blob/master/easyocr/config.py) | 1.7.2, `sv,en`, CPU; explicitly a Latin-script approximation for Finnish |
| Google Cloud Vision | Hosted API | Finnish `fi` is listed. [OCR languages](https://docs.cloud.google.com/vision/docs/languages) | Not measured; no account credentials or billable API calls used |
| Azure Vision Read | Hosted API | Finnish printed text is listed. Finnish is not in the handwritten-language list. [OCR languages](https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/language-support) | Not measured; no account credentials or billable API calls used |
| Amazon Textract | Hosted API | Its documented detection languages do not include Finnish. [Service language limits](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html) | Not measured |

Local engines download their model files during setup and then process images on
the local machine. The benchmark has no cloud engine adapter.

PaddleOCR uses `PP-OCRv5_mobile_det` and `latin_PP-OCRv5_mobile_rec`, with document
orientation, unwarping, and text-line orientation disabled. `enable_mkldnn=False`
avoids a reproducible oneDNN runtime error in this Windows installation. The
initial default server-detector run with oneDNN failed before returning OCR text;
a native CPU server-detector attempt was stopped after more than seven minutes
without a completed result. Neither is treated as a zero-accuracy model result.
The mobile detector is selected explicitly for the measured local CPU comparison.
Both model names are supplied explicitly: PaddleOCR ignores the `lang` shortcut
when explicit model names are configured, so selecting only a detector would not
select the intended Finnish-capable recognizer.

## Corpus and metrics

The run uses seed 42, `--n 5`, Faker 40.39.0, and corpus fingerprint
`b74cc7d0b428bbb0b1021d1f404d0c89ea8c983e4e604221e26958d0c0e85727`.
There are 20 PNG files: five English and five Finnish source documents, each at
clean and half-resolution quality, with 240 labelled identifier occurrences in
total. The two quality versions contain the same text and are paired samples.

- **Identifier recall:** exact labelled values present in OCR output divided by
  planted values. Matching normalizes Unicode NFC and whitespace, while retaining
  case, punctuation, and spelling.
- **Character error rate (CER):** summed Levenshtein character edits divided by
  summed reference characters, including the image title and body. Lower is
  better. Layout whitespace is normalized; other recognition differences count.
- **Time:** average seconds per image on this Windows CPU run, excluding model
  initialization and downloads. This is an observed run time, not a controlled
  hardware performance ranking.
- **Errors:** engine failures remain in the denominator with empty returned text.
  They are also recorded separately so a runtime failure is not mistaken for an
  accuracy result.

Only the image path is passed to an OCR engine. Labels and rendering references
are used afterward for scoring. The benchmark checks the image SHA-256 against
its generated evidence and records it in the result, so reports can be checked
for use of identical images. It selects files from `index.csv`, ignoring stale
unindexed files.

## Measured results

Each row contains five images and 60 planted identifiers. All rows below are
actual local engine output; the cloud services have no measured score.

| Engine | Language | Quality | Returned / planted | Recall | CER | Seconds / image |
|---|---|---|---:|---:|---:|---:|
| Tesseract | English | clean | 58 / 60 | 96.67% | 0.11% | 0.58 |
| Tesseract | English | low_resolution | 59 / 60 | 98.33% | 0.38% | 0.48 |
| Tesseract | Finnish | clean | 55 / 60 | 91.67% | 0.79% | 0.52 |
| Tesseract | Finnish | low_resolution | 57 / 60 | 95.00% | 0.61% | 0.48 |
| PaddleOCR (mobile) | English | clean | 57 / 60 | 95.00% | 0.16% | 6.22 |
| PaddleOCR (mobile) | English | low_resolution | 56 / 60 | 93.33% | 0.33% | 6.38 |
| PaddleOCR (mobile) | Finnish | clean | 58 / 60 | 96.67% | 0.12% | 4.99 |
| PaddleOCR (mobile) | Finnish | low_resolution | 57 / 60 | 95.00% | 0.18% | 4.80 |
| EasyOCR (`sv,en`) | English | clean | 51 / 60 | 85.00% | 0.77% | 5.62 |
| EasyOCR (`sv,en`) | English | low_resolution | 53 / 60 | 88.33% | 1.15% | 2.66 |
| EasyOCR (`sv,en`) | Finnish | clean | 55 / 60 | 91.67% | 1.83% | 4.75 |
| EasyOCR (`sv,en`) | Finnish | low_resolution | 56 / 60 | 93.33% | 1.10% | 2.27 |

Some half-resolution samples score better than their clean counterparts. This
small, single-font corpus shows sensitivity to resampling and segmentation; it
does not establish that reducing image quality improves OCR generally. These
samples are generated printed text, not a handwriting or photographed-document
benchmark.

All 20 images completed without runtime errors for each of the three measured
configurations, and their recorded source-image hashes match across runs.
Overall identifier recall is 229/240 (95.42%) for Tesseract, 228/240 (95.00%) for
PaddleOCR, and 215/240 (89.58%) for the EasyOCR approximation. PaddleOCR returned
115/120 Finnish labels versus Tesseract's 112/120; Tesseract returned 117/120
English labels versus PaddleOCR's 113/120.

Character accuracy and identifier recall answer different questions: one wrong
digit in an otherwise correctly transcribed IBAN makes that whole labelled value
missing. In this run, Tesseract's 11 missed values were six IBANs, two personal
identity codes, two emails, and one name. This is why the pipeline reports both
the complete OCR text and identifier-level results.

## PDF rendering follow-up

A local follow-up on 2026-09-29 compared five rendering/segmentation settings
using Tesseract 5.5.0.20241111 with `eng+fin`. It read 20 embedded-image regions:
10 from the original seed-42 corpus and 10 from an independently generated
seed-20260929 corpus, both with `--n 5`. This produced 100 OCR calls. The new
70-document corpus passed fixture verification for all 960 labels; the OCR
comparison itself covered only its PDF image regions. Each call received image
pixels, with labels and rendering references used afterward for scoring.

| Setting | Original seed 42 | Independent seed 20260929 |
|---|---:|---:|
| Current 2× rendering | 9 / 10 | 10 / 10 |
| 3× rendering | 8 / 10 | 10 / 10 |
| 4× rendering | 8 / 10 | 10 / 10 |
| Source-resolution rendering, minimum 2× | 9 / 10 | 10 / 10 |
| 2× rendering with page segmentation mode 6 | 9 / 10 | 10 / 10 |

These denominators count embedded-image identifier labels only, separately from
all PDF labels and the full-corpus extraction results. Source-resolution
rendering derives its scale from image pixel dimensions and the placed image
bounds, clamped between 2× and 6×; these fixtures used approximately 3.37×.

The current reader returns `Ifrench@example.org` for `lfrench@example.org`.
Source-resolution rendering recovers that identifier but introduces a different
error, reading `tony10` as `tonyl10`. The higher fixed scales also introduce
errors, while segmentation mode 6 leaves the original mismatch. No setting
improved recall consistently across these samples. The image reaches OCR, but
resampling and character recognition remain sensitive to the input. The default
2× PDF rendering is unchanged, and the mismatch remains a measured OCR
limitation. The independent seed uses the same synthetic templates and does not
establish accuracy on real scans.

The ignored local evidence is
`outputs/assigned-validation/ocr-followup/pdf-render-comparison.json`; the
reproduction script is `outputs/assigned-validation/ocr-followup/pdf_experiments.py`.
The script records each OCR output, rendering scale, source hash, and score. This
follow-up did not rerun the entire corpus through extraction, detection, and
redaction, and does not replace the previously recorded full-pipeline results.

## Integration recommendation

Keep Tesseract as the existing baseline while preserving the extractor hook.
Its overall identifier recall was slightly higher on this set and its observed
local run time was lower. PaddleOCR is a useful alternative to evaluate on more
Finnish documents: its Finnish identifier recall and CER were better here, but
that finding comes from only five distinct Finnish source documents. EasyOCR's
Swedish/English approximation offered no overall recall advantage in this run.
The comparison does not establish a general winner for real scans or handwriting.

Use the existing `ocr_language="eng+fin"` option when evaluating Tesseract on mixed
English/Finnish inputs. These benchmark results do not change the pipeline's
default language or select a new OCR engine automatically.

## Reproduce the comparison

Generate and verify the corpus using the project requirements, then run the
benchmark separately for each engine:

```bash
python corpus/generate.py --out outputs/ocr-corpus --n 5 --seed 42
python corpus/verify.py outputs/ocr-corpus
python -m eval.ocr_bench outputs/ocr-corpus --engine tesseract --out outputs/ocr-tesseract
python -m eval.ocr_bench outputs/ocr-corpus --engine paddleocr --paddle-detector PP-OCRv5_mobile_det --out outputs/ocr-paddle
python -m eval.ocr_bench outputs/ocr-corpus --engine easyocr --out outputs/ocr-easy
```

Install Tesseract and its English/Finnish language data for the first command.
The Python dependencies for the alternatives are `paddleocr==3.4.0` with
`paddlepaddle==3.3.1`, and `easyocr==1.7.2`. Separate virtual environments are
recommended for these alternatives because they install different numerical and
model runtimes. They are optional research dependencies, not pipeline startup
requirements. The first local model initialization downloads model files from
the engine's configured distribution service.

Each output directory contains `summary.md`, `summary.csv`, and `details.json`.
The JSON includes per-image OCR text, image hashes, errors, exact missed labels,
engine settings, environment details, and timing. A nonzero benchmark exit status
means at least one OCR runtime failure; imperfect recall is reported rather than
hidden behind a pass/fail result.

The metric tests run without optional models:

```bash
python -m unittest discover -s tests -p test_ocr_bench.py -v
```
