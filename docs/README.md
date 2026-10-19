# Docs index

Every document in `docs/`, ordered the way the study is built: methods first,
then one section per research question, then limitations and the archive.
Start with the [project README](../README.md) for the overview.

## How to read these docs

- **Evidence snapshot `e148240`** is the commit the 2026-10-19 runs measured.
  Older runs name their own commit.
- **Status labels:** `NOT TESTED` means desk research only, `NOT RUN` means a
  planned condition was never executed, `PENDING` means the work is unfinished.
- **Denominators differ by dataset.** No score is pooled across datasets.
- Issue numbers such as `#44` refer to this repository's GitHub issues.

## Current numbers

| Question | Result | Date | Source |
|---|---|---|---|
| RQ2 extraction | 946/960 planted values reach the text; all 14 misses are OCR errors | 2026-10-19 | [extraction-validation](extraction-validation.md) |
| RQ2 detection, `combined` | Synthetic 1,849/1,919 · TAB 4,269/5,112 · Turku 80/100 · ai4privacy EN 1,757/1,986 · FI 1,636/1,953 | 2026-10-14 | [dataset-audit-runs](dataset-audit-runs.md) |
| RQ2 local LLM final pass | `combined` 136/146 · + Gemma 137/146 · + Qwen 136/146 | 2026-10-19 | [local-llm-comparison](local-llm-comparison.md) |
| RQ3 naming from anonymized text | 1/18 (a detector miss); real documents 0/4; raw ceiling 4/4; controls 0/6 | 2026-10-19 | [public-ai-results](public-ai-results.md) |
| RQ3 linkage | 4/4; the true pair was linked through untouched metadata | 2026-10-19 | [public-ai-results](public-ai-results.md) |
| RQ4 usefulness, evidence-supported | Redacted 0/9 · pseudonymized 3/9, in English and Finnish | 2026-10-19 | [utility-impact](utility-impact.md#evidence-supported-answers) |

## Methods

| Doc | What it covers |
|---|---|
| [pipeline.md](pipeline.md) | Pipeline stages, interfaces and the Markdown output contract |
| [techniques.md](techniques.md) | Anonymization techniques, where each breaks, and which are built here |
| [evaluation.md](evaluation.md) | Protocol for detection, re-identification and usefulness |
| [model-evaluation.md](model-evaluation.md) | Running the study helpers in `eval/study.py` |

## RQ1: which options exist

| Doc | What it covers |
|---|---|
| [options-map.md](options-map.md) | Decision guide by format and by option, with the product inventory |
| [commercial/](commercial/) | Small-sample tests of [Azure](commercial/azure_document_pii_redaction.md), [Google](commercial/google_cloud_dlp.md) and [Limina](commercial/limina_anonymization.md) |
| [ocr-survey.md](ocr-survey.md) | OCR engines compared on English and Finnish images |
| [screenshot-redaction.md](screenshot-redaction.md) | Screenshot redaction tools and measured image recall |

## RQ2: how accurate

| Doc | What it covers |
|---|---|
| [extraction-validation.md](extraction-validation.md) | Which planted values reach the extracted text, per format and location |
| [dataset-audit-runs.md](dataset-audit-runs.md) | Seven detectors on 885 labelled documents in English and Finnish |
| [local-llm-comparison.md](local-llm-comparison.md) | Five local configurations, with and without an LLM final pass |
| [residual-misses.md](residual-misses.md) | Why the remaining misses happen |

## RQ3: can public AI re-identify

| Doc | What it covers |
|---|---|
| [public-ai-results.md](public-ai-results.md) | ChatGPT Free results: naming, attributes and linkage |
| [public-ai-pack.md](public-ai-pack.md) | How the 71-prompt test pack was built |

## RQ4: is it practical

| Doc | What it covers |
|---|---|
| [utility-impact.md](utility-impact.md) | Usefulness on raw, redacted and pseudonymized text |
| [options-map.md](options-map.md#part-c-decision-flow-before-pasting) | Cost, setup and where the data goes |

## Limitations

[limitations.md](limitations.md) lists what the evidence does not show and the
open decisions.

## Archive

Earlier records, kept for provenance. Their numbers are superseded.

| Doc | Date | Superseded by |
|---|---|---|
| [dataset-runs.md](archive/dataset-runs.md) | Pre-audit | [dataset-audit-runs.md](dataset-audit-runs.md) |
| [local-model-options.md](archive/local-model-options.md) | Pre-audit | [local-llm-comparison.md](local-llm-comparison.md) |
| [utility-impact-2026-10-13.md](archive/utility-impact-2026-10-13.md) | 2026-10-13 | [utility-impact.md](utility-impact.md) |
| [assigned-task-results.md](archive/assigned-task-results.md) | 2026-09-29 | [extraction-validation.md](extraction-validation.md), [dataset-audit-runs.md](dataset-audit-runs.md) |
| [pre-review-audit.md](archive/pre-review-audit.md) | 2026-10-13 | Fixes merged; limits in [limitations.md](limitations.md) |
| [work-plan.md](archive/work-plan.md) | 2026-10-14 | Historical team plan |
| [final-evidence-run.md](archive/final-evidence-run.md) | 2026-10-19 | Execution record of the evidence run |
