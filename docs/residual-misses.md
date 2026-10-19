# Residual misses on e148240

Diagnosis run locally on 2026-10-19. No detector, reader or redactor fix was
made. The application files under `detect/`, `pipeline/` and `corpus/` still
match `e148240`. The compact evidence is
[residual-diagnosis-2026-10-19.json](../eval/baselines/residual-diagnosis-2026-10-19.json).
It records versions, corpus fingerprints, source-file hashes, OCR differences
and recognizer decisions. Its values are synthetic corpus labels, not the
public-AI pack's answer key. This diagnosis never opened a pack's
`ground_truth.csv`.

These are three different scopes. Keep them separate:

| Scope | What was reproduced | Source |
|---|---|---|
| English utility memos | Both allocated-hours fragments classified as `DATE_TIME` in each of three memos: six false-positive spans | `hours_wrong_type` in the evidence JSON; source templates in [eval/create_study.py](../eval/create_study.py) |
| Short synthetic corpus, `--n 1 --seed 42` | Two English PNG IBAN extraction misses on the 14-document, 146-body-label corpus; fingerprint `27934f5e…2e40ae` | `smoke_png_iban` and `smoke_corpus` in the evidence JSON |
| Extraction acceptance, `--n 5 --seed 42` | 946/960 labels returned across 70 documents; 14 OCR mismatches, zero extraction exceptions; fingerprint `6f47fe80…6ae2e1` | `acceptance` in the evidence JSON; local full report `outputs/residual-diagnosis/acceptance/` |

The Finnish company probe used the actual extracted Markdown of
`docx/fi_docx_00.docx` in the current #44 matrix corpus, before replacement.
Its source hash and corpus fingerprint are recorded under `finnish_company`.
The sanitized body retains the company in
`outputs/2026-10-19-e148240/runs/fake/combined/fi_docx_00_anonymized.md`.
This single extracted-document example is not the full set of typed company
misses in the separate native-body LLM smoke benchmark.

## Residual-miss table

Classification locates the first demonstrated failure. An OCR transcription
error is an **extraction failure** even when a later recognizer rejects the
corrupted value. **Partial span** means that extraction preserved the value
but detection covered only part of it. **Wrong type** means the detector
assigned the wrong category. A **detection miss** has no overlapping candidate.
An OCR mismatch alone is not evidence of unreadable pixels.

| Case | Evidence / classification | Root cause | General fix to evaluate; NOT RUN |
|---|---|---|---|
| (a) `hours 18` removed | **Wrong type.** `SpacyRecognizer` emits `DATE_TIME`, score 0.85, in all three full utility memos | The English NER model treats an allocation quantity as a temporal entity. This is not a regex date-pattern match. `combined` intentionally retains Presidio's date spans | Distinguish duration/allocation quantities from identifying calendar dates using context and validation. Evaluate positive date cases and negative quantity cases together; measure retained utility and missed dates |
| (a) `hours 12` removed | **Wrong type.** Same recognizer, type, score and three-memo reproduction | Same semantic error; generic replacement and numbered pseudonyms both lose the numeric quantity once detection removes it | Same context-aware date/quantity validation; changing the replacement token cannot recover a removed number |
| (b) Finnish company in `fi_docx_00.docx` | **Detection miss.** The complete single-token company is present at extracted offsets 333–338. Presidio, GLiNER and combined each produce zero overlapping spans | Organisation NER produces no candidate for this suffix-free company in this context. Combined routing did not drop an existing candidate. The model's internal reason is unmeasured | Evaluate Finnish organisation detection on short names and sparse contexts; optionally use a maintained organisation/customer/project glossary as an additional layer. Validate on independent names and measure over-redaction; never add a rule for this planted name |
| (c) English PNG, clean, `en_png_00_clean.png` | **Extraction failure.** IBAN prefix `GB05` becomes `GBO5`; original-value recognizer finds one IBAN, corrupted-value recognizer finds none | Tesseract confuses digit `0` with letter `O` before detection. The complete line reaches OCR | Preserve OCR confidence/word coordinates, flag identifier-shaped uncertain strings, and compare independent OCR readings. In image output, cover the entire suspected identifier; do not silently manufacture a corrected account number |
| (c) English PNG, half resolution, `en_png_00_low_resolution.png` | **Extraction failure.** `GB05` becomes `GBOS`; original-value recognizer finds one IBAN, corrupted-value recognizer finds none | `0`→`O` and `5`→`S` substitutions; this is the same source document at another resolution, not an independent document | Same identifier-aware OCR review and conservative masking. For text output, replace the whole uncertain field or withhold it for manual review |

The two PNGs above are from the 14-document corpus. The two IBAN entries in
the 70-document table below are different generated values. Do not add these
counts or describe them as four misses in one experiment.

All 14 acceptance misses are listed here. Every row is an **extraction
failure**: the pixels/image region reaches Tesseract, but the returned string
differs from its planted value. There is no demonstrated unreadable/clipped
source, detection miss, partial detection span or wrong-type detection in
this extraction-only test. Source PNG inspection confirms the text exists;
the table does not establish how a human or vision model would score it.
The exact expected and returned substrings are in `acceptance.missing` in
the evidence JSON.

| Source file | Location / type | OCR difference | Root cause / general fix to evaluate |
|---|---|---|---|
| `pdf/en_pdf_00.pdf` | Embedded image / EMAIL | Initial `l`→`I`, `@`→`e` | Rasterized-image OCR character confusion; compare source-resolution/alternate OCR and require manual review of uncertain identifiers |
| `png/en_png_00_clean.png` | Body / EMAIL | Initial `l`→`I` | Letter confusion; uncertainty review and whole-field masking |
| `png/en_png_00_low_resolution.png` | Body / EMAIL | Initial `l`→`I` | Same source at another quality; same fix |
| `png/en_png_02_low_resolution.png` | Body / IBAN | Internal `I`→`l` | Letter confusion inside an identifier; inspect field shape and OCR disagreement, do not rely on checksum rejection as a privacy control |
| `png/en_png_04_clean.png` | Body / IBAN | Prefix `GB02`→`GBO2` | Digit/letter confusion; same identifier-aware review |
| `pptx/fi_pptx_03.pptx` | Embedded image / EMAIL | `17`→`l7` | Embedded-image OCR letter/digit confusion; preserve full image review and compare alternate OCR |
| `png/fi_png_01_clean.png` | Body / EMAIL | Initial `zl`→`zZl` | OCR inserts a letter; conservative whole-field masking and uncertainty review |
| `png/fi_png_01_clean.png` | Body / PERSONAL_ID | Final `J`→`)` | Glyph/punctuation confusion; do not treat a failed exact pattern/checksum as evidence of no identifier |
| `png/fi_png_01_low_resolution.png` | Body / PERSONAL_ID | Final `J`→`)` | Same source and confusion at another quality; same fix |
| `png/fi_png_02_clean.png` | Body / PERSON | `ä`→`a` in surname | Diacritic loss despite `eng+fin`; compare Finnish-capable OCR and review complete names, without assuming ASCII variants are harmless |
| `png/fi_png_03_clean.png` | Body / PERSON | `q`→`g` in surname | Glyph substitution; compare OCR readings and inspect uncertain names |
| `png/fi_png_03_clean.png` | Body / EMAIL | `@`→`&` | Symbol confusion prevents literal email recognition; flag uncertain contact fields and mask the complete field |
| `png/fi_png_03_low_resolution.png` | Body / PERSON | `q`→`g` in surname | Paired source repeats the substitution; same fix |
| `png/fi_png_03_low_resolution.png` | Body / EMAIL | `@`→`&` | Paired source repeats the substitution; same fix |

The current acceptance totals are PNG 228/240, PDF 149/150 and PPTX 149/150;
CSV 90/90, DOCX 200/200 and XLSX 130/130. The 100% gate covers deterministic
standard-text locations and excludes these OCR groups. Passing that gate
does not mean all identifiers were extracted. The historical Windows OCR
study's 948/960 and the current host's 946/960 remain separate runs; see
[extraction-validation.md](extraction-validation.md),
[ocr-survey.md](ocr-survey.md) and
[pre-review-audit.md](archive/pre-review-audit.md). No proposed OCR fix was applied
or measured in this diagnosis.

## Unsupported-content table

The reader limits below come from
[pre-review-audit.md](archive/pre-review-audit.md), with the native-format boundary
checked in [pipeline/extractors.py](../pipeline/extractors.py). They are
coverage limits, not new test results. Output is Markdown; it is not a
sanitized copy of the original Office/PDF file.

| Format | Unsupported or unestablished coverage | Consequence / required review |
|---|---|---|
| DOCX | Charts, OLE objects, external pictures | Body/table/header/comment coverage does not establish coverage of these objects; inspect or exclude them |
| XLSX | Drawings, charts, threaded comments; formula calculation is not provided | Inspect objects and workbook content; recalculate in the source application when cached values are missing. Comment extraction uses a nonstreaming view and increases memory use on large workbooks |
| PPTX | Master-slide content and charts | Slide text/notes/image extraction does not establish logo/template/master coverage |
| Native-text PDF | Attachments, XMP, link targets, vector-only lettering | Review embedded files, metadata, links and rendered pages; a text export is not PDF-file sanitization |
| Scanned PDF / images / TIFF | OCR depends on language and orientation and can miss unreadable pixels; no general handwriting guarantee | Inspect rendered output and uncertain text. Extraction cannot establish removal of faces, logos, letterheads, signatures or stamps; [screenshot-redaction.md](screenshot-redaction.md) records that visual limit |
| CSV / extracted text | No guarantee against contextual/quasi-identifier linkage | Review combinations and confidential content. Statistical table anonymization is a separate task |
| Email | No native EML/MSG/mailbox reader | Headers, signatures, quoted threads and attachments need a separate extraction and review workflow; NOT TESTED |
| Logs / code | TXT/MD input is supported; secret detection and code/log-specific coverage are not established | Add a separate local secret scanner and review internal names and confidential logic; NOT TESTED as a format-specific workflow |
| CAD | No native CAD reader or geometry anonymization | Metadata/title-block cleanup cannot establish that confidential geometry is safe; NOT TESTED |
| Audio / video | No native transcription, voice or frame-redaction workflow | Transcript redaction does not remove original voices or identifying video; NOT TESTED |

## Reproduction

Run extraction without an LLM or GLiNER loaded:

```bash
python corpus/generate.py --out outputs/residual-diagnosis/corpus --n 5 --seed 42
python corpus/verify.py outputs/residual-diagnosis/corpus
python -m pipeline.validation outputs/residual-diagnosis/corpus \
  --report-dir outputs/residual-diagnosis/acceptance --ocr-language eng+fin \
  --min-recall 1.0 \
  --require-locations body,metadata,notes,hidden_sheet,header,footer,comment,tracked_change,embedded_image \
  --threshold-qualities standard \
  --threshold-locations body,metadata,notes,hidden_sheet,header,footer,comment,tracked_change
python corpus/generate.py --out outputs/residual-diagnosis/smoke-corpus --n 1 --seed 42
```

For each `returned=false` label in `acceptance/details.json`, extract its source
again with `extract_to_markdown(path, ocr_language="eng+fin")` and compare the
complete value. For the two English smoke PNGs, compare their IBAN label with
the account token in the same extractor output. Pass the expected and OCR
tokens separately to `get_detector("rules").detect(token, "en")` to reproduce
the 1-versus-0 `IBAN_CODE` decisions.

For the utility error, generate the existing three-memo study with
`python -m eval.create_study outputs/residual-diagnosis/utility`. Analyze each
memo using `get_detector("rules").analyzer.analyze(text=text, language="en",
return_decision_process=True)` and inspect the explanation for the two hours
spans. The explanation names `SpacyRecognizer`.

For the company probe, unload all LLMs first, set `HF_HUB_OFFLINE=1
GLINER_DEVICE=cpu`, extract the current matrix corpus's Finnish DOCX, then
inspect spans overlapping offsets 333–338 from the combined detector and its
`presidio` and `model` components. All three lists are empty. Exit that
process before loading an LLM. The exact input hash is in the evidence JSON.
