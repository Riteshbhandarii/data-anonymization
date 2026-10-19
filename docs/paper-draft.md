# Anonymizing documents before public AI use: a practical evaluation of methods and tools for Finnish SMEs

Working paper. Evidence-supported draft; not a claim of safe disclosure.
Current detector evidence and archived pre-audit experiments are identified
separately. The practical decision guide is [options-map.md](options-map.md).

## Abstract

PENDING. Write after the public-AI study and human review of the remaining
utility/label limitations. Do not infer re-identification resistance from
identifier recall.

## Introduction

SME employees may need help with a document while lacking an approved route to
send its personal or business information to a public AI service. This study
examines what free local extraction, detection and replacement tools actually
remove from Finnish and English office files, what survives, and what useful
information replacement destroys. It also maps commercial alternatives and
format-specific manual review requirements.

The evaluation separates extraction, whole-identifier detection, visible-image
redaction, downstream question answering and residual re-identification.
These are different outcomes: a high text recall cannot establish that a logo,
a rare role/place combination or confidential design is safe to disclose.
The pipeline produces Markdown; it does not rebuild sanitized Office files.
The format scope and reader limits are documented in [README.md](../README.md)
and [the audit](pre-review-audit.md).

The assignment question is: **What safe and practical methods and tools are
available for anonymizing different document formats before submitting
information to publicly available AI models?**

| Research question | What this paper evaluates |
|---|---|
| RQ1: available options | Which methods/tools exist, free/paid and local/cloud, and which formats each handles. |
| RQ2: accuracy | How accurately they detect personal identifiers in English and Finnish across formats. |
| RQ3: safety | Whether public AI can still re-identify persons or organisations after anonymization. PENDING the manual study #44. |
| RQ4: practicality | Usefulness retained after anonymization, cost, setup effort and whether data leaves the machine. |

Paid and cloud tools are in scope as compared options. The current execution
constraint is local-only experimentation; it does not exclude earlier commercial
measurements or primary-source product research from the paper. No novelty
claim is made. Detection recall alone cannot answer RQ3.

## Legal background

PENDING: legislation contribution from teammate.

The contribution must cover the following; this draft asserts no unverified
legal holding:

- GDPR Recital 26: identifiability and reasonably likely means of identification.
- WP29 Opinion 05/2014: singling out, linkability and inference.
- GDPR Article 4(5): pseudonymization and separately held additional information.
- CJEU EDPS v SRB 2025: holding to verify, including recipient/context questions
  and the limits of applying it to this study.
- Finnish Trade Secrets Act: confidential business information remains a
  separate disclosure concern after personal identifiers are replaced.

## Related work: candidates to verify

Bibliographic leads below were checked against primary pages on 2026-10-19.
Full-text comparison, exact claims and final references still need review.
They do not establish novelty for this project.

| Candidate | Primary source | What to verify before citing substantively |
|---|---|---|
| Robin Staab et al., ICLR 2025, *Language Models are Advanced Anonymizers* | [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f478b2e8ad9ff0756bf5b79fb31c330f-Abstract-Conference.html) | Adversarial LLM inference setting, anonymization/utility metrics and how its attacker differs from our manual public-AI study. Do not confuse it with the earlier personal-attribute inference paper. |
| Pilán et al., 2022, Text Anonymization Benchmark (TAB) | [ACL Anthology](https://aclanthology.org/2022.cl-4.19/) | Annotation/masking policy, privacy/utility metrics and the implications of using one annotator in our runner. |
| ANOPPI | [Finnish Ministry of Justice project announcement](https://valtioneuvosto.fi/-/1410853/tekoaly-avuksi-henkilotietojen-poistamiseen-viranomaisten-paatoksista), [research paper candidate](https://wiki.media.tkk.fi/publications/2022/oksanen-et-al-anoppi-2022.pdf) | Finnish court-decision workflow, human review, tool availability and scope relative to mixed SME office documents. |
| OpenAI Privacy Filter evaluation | [Official model card](https://cdn.openai.com/pdf/c66281ed-b638-456a-8ce1-97e9f5264a90/OpenAI-Privacy-Filter-Model-Card.pdf), [independent evaluation candidate](https://arxiv.org/abs/2608.02616) | Label taxonomy, corrected annotations, language/domain selections and typed versus untyped scoring. Vendor F1 is not interchangeable with our whole-value recall. |
| LeakageBench | [Authors' preprint](https://arxiv.org/abs/2609.02207) | Spatial/document-level leakage definitions, document-image distributions and OCR/vision baselines. Publication status and final version PENDING verification. |

## Methods

### Pipeline and transformations

The local pipeline detects format, extracts text/OCR, normalizes Markdown,
detects spans and saves replaced text. Readers cover TXT/MD/CSV, DOCX, XLSX,
PPTX, PDF and common raster images. OCR uses Tesseract; office properties,
notes and selected hidden content enter the text. Unsupported embedded
features are listed in [pre-review-audit.md](pre-review-audit.md). A separate
image module fills overlapping OCR word boxes and writes new PNG pixels.

Generic replacement uses entity labels. Consistent pseudonyms use numbered
aliases with explicit document/corpus scope; the utility rerun uses document
scope. The key stays local. These transformations do not by themselves prove
anonymization. Code interfaces and the study protocol are in
[pipeline.md](pipeline.md), [model-evaluation.md](model-evaluation.md) and
[evaluation.md](evaluation.md).

### Corpora and evidence boundaries

| Corpus/study | Documents and labels | Scope and source |
|---|---|---|
| Corrected matrix: synthetic | 140 office/image files; 1,919 all-location labels, including 1,459 body labels | Seed 42, n=10; generated templates and fixed-shape project recognizers. [Matrix archive](../eval/baselines/dataset-audit-matrix.json) |
| Corrected matrix: TAB | All 127 test documents; 5,112 masked mentions, 374 DIRECT and 4,738 QUASI | Human-labelled English court judgments; first sorted annotator per document. [Runner](../eval/run_matrix.py), [report](dataset-audit-runs.md) |
| Corrected matrix: Turku | 18 test documents; 100 selected mentions | Human-labelled Finnish NER; selected name/org/place/date types. [Report](dataset-audit-runs.md) |
| Corrected matrix: ai4privacy | 300 rows per language; 1,986 EN and 1,953 FI labels | Synthetic PII; seed-42 selections. Not real-office ground truth. [Archive](../eval/baselines/dataset-audit-matrix.json) |
| Local LLM comparison | 14 documents, 146 body labels, 73 per language | Frozen seed-42 n=1 corpus, seven files per language. No extraction score. [Comparison](local-llm-comparison.md) |
| Extraction acceptance | 70 documents; 960 labels | Fresh extraction-only reproduction, separate from detector recall. [Diagnosis](residual-misses.md) |
| Earlier screenshot study | 40 PNGs; 480 planted, 467 OCR-readable values | Pre-audit study, one font and paired resolution variants. [Report](screenshot-redaction.md) |
| Earlier OCR study | 20 PNGs; 240 planted labels | Windows CPU, paired resolutions; extraction only. [Report](ocr-survey.md) |
| Utility rerun | Three EN memos/9 questions and three draft FI memos/9 questions; three text variants each | Fictional allocation tasks; Finnish NEEDS HUMAN REVIEW. [Utility report](utility-impact.md) |
| Public-AI pack | Combined-generated text, controls and manual questions | PENDING #44; preparation is not a model experiment. [Pack record](public-ai-pack.md) |

The seven-method matrix totals 885 selected documents and 11,070 labelled
values **per method**, across 28 method/dataset runs. No score pools these
corpora into a universal accuracy figure. The labelled matrix source and hashes
are preserved in [the report](dataset-audit-runs.md); it predates the current
branch and is reused as evidence rather than claimed as rerun today.

### Detectors and local LLM configuration

The registered matrix methods are basic Presidio/spaCy, rules with project
patterns, rules with larger spaCy models, GLiNER plus patterns, combined
Presidio/GLiNER, Privacy Filter plus patterns and GLiNER2 plus patterns.
Pattern formats include synthetic invoice/plate/identity values; their high
scores cannot establish arbitrary national/company identifier coverage.
Model names, devices and versions are in [local-model-options.md](local-model-options.md)
and the [matrix archive](../eval/baselines/dataset-audit-matrix.json).

The new local comparison evaluates combined alone, Qwen 3.5 9B alone, Gemma 4
E4B alone and each LLM after combined. Cached MLX 4-bit weights are served by
LM Studio on loopback. Combined detections are frozen in a separate process
before LLM loading to fit the 16 GiB host and keep GLiNER and LLMs apart.
The final pass sees base spans masked with equal-length blocks and retains
the base spans. Exact prompts, hashes, context, generation settings, model-load
scope, runtime and parser failures are in [local-llm-comparison.md](local-llm-comparison.md).
This is a staged execution change for evaluation, not a detector repair.

### Metrics

Whole-value recall requires one accepted span to contain the entire label;
partial spans are reported separately. Some dataset classes accept any type,
so acceptance policies must accompany comparisons. The matrix's lower-bound
precision counts detections overlapping any annotation and includes negative
inputs. An unlabelled detection may be legitimate missing annotation.

The short LLM trial instead records typed-overlap precision, wrong-type
matches and unlabelled detections. It has no labels for contextual
quasi-identifiers. Failed documents remain in recall denominators. OCR uses
exact-value return rate and character error rate; image redaction scores
hidden/readable separately from hidden/planted. Utility keeps correct, wrong,
refused, invalid and error outcomes and reports raw-correct paired retention.
A typed miss can still be physically masked under a different type; typed
miss counts are not counts of readable leaks. These metrics are not
interchangeable.

## Results

### RQ1: available methods, tools and format coverage

The [options map](options-map.md) inventories all nine products from the
[product survey](product-options.md): Presidio, ARX, scrubadub, DataFog Core,
Google Sensitive Data Protection, Amazon Comprehend PII, Azure AI Language PII,
Limina and Tonic Textual. It adds our detector configurations, local LLM final
passes, OCR engines and screenshot tools. The map records cost model, data
location, formats, Finnish evidence, strengths, weaknesses and use conditions.

Local extraction covers text/CSV, DOCX, XLSX, PPTX, PDF and images, with Markdown
output. Native-file handling differs: Azure's tested document endpoint accepted
DOCX/PDF but rejected PPTX/XLSX/CSV; Limina returned usable PDF/XLSX/PPTX/CSV
files but failed the two corpus DOCX files. Email, logs/code, CAD and audio/video
are desk research labelled NOT TESTED. Sources and unsupported content appear
in [Part A of the map](options-map.md) and [the reader audit](pre-review-audit.md).

### RQ2: identifier detection accuracy

#### Corrected 885-document, seven-method matrix

All entries below are whole-value accepted-type coverage, with the same
selection per method. This is the corrected-code 2026-10-14 measurement,
reused from [dataset-audit-runs.md](dataset-audit-runs.md) and its
[aggregate archive](../eval/baselines/dataset-audit-matrix.json).

| Method | Synthetic 140 files / 1,919 labels | TAB 127 texts / 5,112 mentions | Turku 18 texts / 100 mentions | ai4privacy EN 300 rows / 1,986 labels | ai4privacy FI 300 rows / 1,953 labels |
|---|---|---|---|---|---|
| basic | 1,178/1,919 (61.4%) | 3,344/5,112 (65.4%) | 51/100 (51.0%) | 1,076/1,986 (54.2%) | 756/1,953 (38.7%) |
| rules | 1,536/1,919 (80.0%) | 3,344/5,112 (65.4%) | 51/100 (51.0%) | 1,076/1,986 (54.2%) | 822/1,953 (42.1%) |
| rules-lg | 1,615/1,919 (84.2%) | 3,463/5,112 (67.7%) | 77/100 (77.0%) | 1,154/1,986 (58.1%) | 912/1,953 (46.7%) |
| gliner | 1,725/1,919 (89.9%) | 3,906/5,112 (76.4%) | 80/100 (80.0%) | 1,547/1,986 (77.9%) | 1,575/1,953 (80.6%) |
| combined | 1,849/1,919 (96.4%) | 4,269/5,112 (83.5%) | 80/100 (80.0%) | 1,757/1,986 (88.5%) | 1,636/1,953 (83.8%) |
| privacy-filter | 1,582/1,919 (82.4%) | 1,461/5,112 (28.6%) | 0/100 (0.0%) | 1,600/1,986 (80.6%) | 1,238/1,953 (63.4%) |
| gliner2 | 1,809/1,919 (94.3%) | 3,434/5,112 (67.2%) | 78/100 (78.0%) | 1,648/1,986 (83.0%) | 1,636/1,953 (83.8%) |

Combined's TAB DIRECT coverage is 232/374 (62.0%), versus QUASI 4,037/4,738
(85.2%). Thus its overall TAB recall obscures weaker DIRECT coverage.
Lower-bound precision also changes the interpretation:

| Combined dataset | Annotation-overlapping detections / all detections | Lower-bound precision |
|---|---:|---:|
| TAB EN | 9,162/14,388 | 63.7% |
| Turku FI | 104/393 | 26.5% |
| ai4privacy EN | 2,694/3,104 | 86.8% |
| ai4privacy FI | 2,059/2,341 | 88.0% |

Source: [current matrix precision/type tables](dataset-audit-runs.md). These
are detection-level overlap counts, not mention-level recall denominators.
They show substantial review burden, particularly on Turku, without proving
that every unlabelled detection is wrong.

#### Combined accuracy by office/image format and language

Current all-location synthetic results, from the same matrix; these are
generated files, not hand-labelled real-office evidence. PNG includes paired
resolution variants. Source: [matrix aggregate JSON](../eval/baselines/dataset-audit-matrix.json).

| Format | English whole-value recall | Finnish whole-value recall |
|---|---|---|
| CSV | 81/90 (90.0%) | 90/90 (100.0%) |
| DOCX | 189/200 (94.5%) | 191/200 (95.5%) |
| PDF | 147/149 (98.7%) | 148/150 (98.7%) |
| PNG | 233/240 (97.1%) | 226/240 (94.2%) |
| PPTX | 144/150 (96.0%) | 148/150 (98.7%) |
| XLSX | 125/130 (96.2%) | 127/130 (97.7%) |

Across formats, combined covers 919/959 English and 930/960 Finnish synthetic
labels. The by-format table and those language totals share the 1,919-label
synthetic denominator; they are not added together. [Full report](dataset-audit-runs.md).

#### Local LLM comparison

The complete current five-configuration table, per-language/per-type counts,
precision and model loading/runtime scope are in
[local-llm-comparison.md](local-llm-comparison.md). Earlier Qwen/Gemma results in
[local-model-options.md](local-model-options.md) are archived pre-audit evidence
and must not be substituted for this comparison. No full 885-document LLM
matrix or contextual privacy gain is claimed.

#### Screenshots and OCR

In the earlier 40-PNG screenshot study, GLiNER hid 422/467 OCR-readable values
(90.4%), versus rules 408/467 (87.4%). Against all 480 planted values those
become 87.9% and 85.0%. GLiNER left 40 readable values fully leaked, including
33 IBANs; rules left 9 fully leaked and 50 partial. The detector families fail
in complementary places. This study did not run combined and is not a current
post-audit image comparison. Source: [screenshot-redaction.md](screenshot-redaction.md).

On the earlier separate 20-PNG OCR corpus, exact-value extraction was
229/240 for Tesseract, 228/240 for PaddleOCR mobile and 215/240 for EasyOCR's
`sv,en` Finnish approximation. Finnish counts were respectively 112/120,
115/120 and 111/120. No cloud OCR was measured. The source is
[ocr-survey.md](ocr-survey.md), including configuration failures and timing scope.

The fresh extraction acceptance reproduced 946/960 returned values in 70
documents. Its 14 OCR misses and the two English PNG IBAN misses in the separate
small smoke corpus are diagnosed in [residual-misses.md](residual-misses.md).
None of these OCR scores measures logo, face or contextual identification.

#### Commercial and free tools: small samples

The following earlier contributor studies have separate corpora/configurations.
They are not a league table against the 885-document matrix.

| Study | Sample | Measurement | Result and qualification | Source |
|---|---|---|---|---|
| Azure native Document PII | 4 EN/FI DOCX/PDF, 48 identifiers | Full any-type redaction / type-aware detection | 35/48 / 33/48; 1 partial. Tested endpoint rejects PPTX/XLSX/CSV. | [Azure report](commercial/azure_document_pii_redaction.md) |
| Google content inspection | 10 files, 98 body identifiers | Full any-type / type-aware detection | 55/98 / 53/98; 8 partial; no returned-file redaction validation. | [Google report](commercial/google_cloud_dlp.md) |
| Limina hosted Community API | 8 successful of 10 corpus files, 74 body identifiers | Full any-type / type-aware detection | 69/74 / 62/74; 5 partial; two DOCX HTTP 500 failures excluded from coverage denominator. | [Limina report](commercial/limina_anonymization.md) |
| scrubadub | 6,500 labels, 6,400 extractable | Changed text, unverified removal | 1,049/6,400 changed; 100 not extracted. | [CSV](../eval/free_tools/scrubadub/results/format_language_summary_v2.csv) |
| DataFog | 6,500 labels, 6,400 extractable | Changed text, unverified removal | 2,769/6,400 changed; addresses only had postal codes replaced in manual review. | [CSV](../eval/free_tools/datafog/results/format_language_summary_v2.csv), [review](../eval/free_tools/datafog/results/datafog_address_manual_validation.csv) |
| ARX | Existing table-preparation scripts and screenshots | Tabular risk/utility configuration | No comparable verified recall/risk aggregate available. | [Artifacts](../eval/free_tools/arx/) |

Hosted commercial tests sent synthetic source files off the machine in the
earlier team work. No paid API, cloud document upload or new account was used
for the 2026-10-19 local evidence run. Untested products/format claims remain
labelled NOT TESTED/NOT RUN in [options-map.md](options-map.md).

### RQ3: residual public-AI re-identification

PENDING #44. The combined pack is prepared for manual collection with/without
web search, naming/attributes/linkage, raw fictional ceilings and unrelated
controls. [public-ai-pack.md](public-ai-pack.md) records local completeness.
No public-AI answers were collected by this work, and pack generation does not
count as a privacy result. The actual study-pack ground truth remains unopened. A full regression run did
open its own temporary synthetic fixture key; that restriction breach is
recorded in [the run report](final-evidence-run.md), separate from the blind study.

### RQ4: practicality

#### Usefulness retained

The 2026-10-19 paired local rerun and human-review status are reported in
[utility-impact.md](utility-impact.md). It compares raw, generic redaction and
consistent pseudonyms on the same nine questions per language, preserving all
error/refusal categories. The Finnish three-memo task set is a draft requiring
human review; it cannot establish validated Finnish utility yet.

The earlier pre-audit English combined trial answered 9/9 raw, 5/9 redacted and
6/9 pseudonymized questions correctly. All three total-hours questions failed
after sanitization because `hours 18` and `hours 12` were removed as dates.
These are archived results, not the new rerun. Source and detailed outcomes:
[utility-impact.md](utility-impact.md).


#### Cost, setup and data location

Free local routes require extraction/OCR dependencies, language models and
manual review; free licence cost does not remove staff effort or hardware
constraints. The 16 GiB local comparison uses one LLM at a time and serializes
the GLiNER base stage. Runtime and loading scope are reported separately in
[the comparison](local-llm-comparison.md). No cash-cost, energy or staff-time
benchmark was run, so no total-cost saving is quantified.

The completed combined/MPS pack-preparation run took 1,178.2 seconds of
detection for 17 unlabelled real-public exports totalling 2,040,231 characters,
plus 32.4 seconds extraction. Its separate synthetic stage processed 140 files
and 76,592 characters in 29.0 detection seconds. Warmup/loading is recorded
separately and is not a full cold-start measurement. These are different
workloads, not competing methods; the long-export cost matters for practical
use. Source: [pack preparation](public-ai-pack.md) and
[safe runtime archive](../eval/baselines/public-ai-pack-e148240.json).

ARX adds column classification and privacy-model/hierarchy setup. Presidio and
other detectors need language/type configuration. A screenshot editor needs
manual selection, opaque fill and a checked flattened export. These are
workflow requirements, not setup-time measurements. See [the options map](options-map.md)
for option-specific use and rejection conditions.

Google, AWS and Azure are metered cloud options; Limina and Tonic offer
proprietary hosted/deployment routes. A hosted anonymizer receives the source:
**data leaves the machine before redaction**. Self-hosted commercial deployments
need separate data-flow verification and were not tested here. Earlier team
cloud measurements used synthetic files; this local evidence run made no new
cloud uploads or paid calls. Cost models and setup requirements come from
[product-options.md](product-options.md) and its linked official sources;
prices were not benchmarked.

## Failure analysis

[residual-misses.md](residual-misses.md) classifies extraction failures,
partial spans, wrong types and detection misses. Unreadable pixels are a risk
category, but none of the reproduced 14 acceptance misses was established as
unreadable source pixels.
The date/hour false positive loses task-relevant numbers; the surviving Finnish
organization illustrates a semantic detector gap; OCR character substitutions
prevent exact identifier matching before detection starts. Proposed remedies
are general evaluation/design changes, not planted-name rules. No detector or
extractor fixes were made as part of this diagnosis.

The unsupported-content table also prevents a visible-text success from being
reported as whole-file coverage. Logos, signatures, layout and business meaning
require separate review even where OCR text is perfectly recognized.

## Limitations

- Real office documents were processed but not hand-labelled; detection quality
  on real text is from human-labelled TAB (EN) and Turku NER (FI). The remaining
  real-office annotation study #45 is PENDING; this work does not silently
  cancel it.
- Synthetic templates, one-font images and project-specific identifier formats
  make the generated results optimistic. Paired resolution variants are not
  independent real-world documents.
- Corpus taxonomies differ. Some labels accept any detected type, while typed
  smoke precision and commercial any-type coverage use different policies.
- Matrix precision is a lower bound under incomplete annotation. Utility tests
  cover only a few allocation questions and a single local answering setup;
  Finnish task validity needs human review.
- The short local LLM corpus has no contextual quasi-identifier ground truth.
  Added detections cannot establish reduced inference, linkage or naming risk.
- Runtime depends on host, device, caching and loading scope. The historical
  matrix excludes model loading; the new staged LLM report distinguishes base
  detection, model loading and LLM requests. Peak memory is not established.
- Reader support omits some Office embedded objects and PDF non-text features.
  Scanned PDFs, email, logs/code, CAD and audio/video have no dedicated project
  anonymization benchmark. Desk research is not measured support.
- Small commercial samples, service errors, configuration differences and
  unavailable raw aggregate provenance limit procurement conclusions.
- Public-AI re-identification, web-search ablation and logo/letterhead exposure
  remain PENDING #44. No detector score is a compliance or disclosure guarantee.
- Personal-data cleaning does not remove confidential geometry, source code,
  pricing, strategy or other protected business information.

## Conclusion

PENDING. Complete after #44, Finnish utility review and team agreement on how
remaining real-office labels limit the claims. The available evidence supports
a local preparation-and-review workflow and a format/options map; it does not
yet support the claim that these tools make arbitrary SME documents safe for
public AI.
