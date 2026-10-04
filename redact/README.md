# redact

Replace detected sensitive spans in the complete Markdown string. Detection
decides which character intervals to process; this module applies those spans
and returns text. The pipeline saves the resulting UTF-8 Markdown file.

## Run the integrated pipeline

Install `requirements.txt` and the English/Finnish model packages described in
[the evaluation guide](../eval/README.md). The adapter reuses
`eval.bench.build_analyzer()` and its score threshold, so it does not introduce
a separate detector configuration.

```python
from detect import PresidioDetector
from pipeline import run_pipeline
from redact import PipelineAnonymizer

detector = PresidioDetector()
anonymizer = PipelineAnonymizer(detector, language="en", mode="replace")
result = run_pipeline("documents/report.docx", anonymizer=anonymizer)
print(result.output_path)
```

Reuse the detector across documents to avoid loading model weights repeatedly.
Set `language="fi"` for Finnish input; language selection is explicit.

## Connect another detector

Implement `detect(text: str, language: str) -> list[span]`. A span can be a
Presidio result object, `redact.Span`, or a dictionary with these fields:

| Field | Meaning |
|---|---|
| `start` | Inclusive Python character offset in the supplied string |
| `end` | Exclusive Python character offset in that same string |
| `entity_type` | Uppercase type such as `PERSON` or `EMAIL_ADDRESS` |
| `score` | Finite confidence number between 0 and 1 |

`PipelineAnonymizer` passes exactly the same normalized Markdown to detection
and redaction. Do not edit, normalize, encode or reorder text between those
operations. Invalid offsets or malformed spans raise an error before output is
saved. Byte offsets and offsets into a separately extracted body are invalid.

To apply existing detections directly:

```python
from redact import redact

processed_markdown = redact(markdown, spans, mode="replace")
```

`replace` produces type placeholders such as `[PERSON]` and `[EMAIL_ADDRESS]`.
`pseudonymize` produces numbered placeholders such as `[PERSON_1]`, preserving
the relationship between repeated exact values of the same type. It does not
attempt to identify alternate spellings as the same person.

## Choose pseudonym scope explicitly

Without an alias map, each call starts a new mapping; repeated values remain
consistent within that document. To share identifiers across a chosen batch:

```python
from redact import AliasMap, PipelineAnonymizer

aliases = AliasMap()
anonymizer = PipelineAnonymizer(
    detector, language="en", mode="pseudonymize", aliases=aliases,
)
for source in sources:
    run_pipeline(source, anonymizer=anonymizer)
aliases.clear()
```

The map remains in memory and contains the original values. It is never written
to disk automatically or included in the output. Reuse it only for the scope
in which cross-document linking is required. Use a separate `PipelineAnonymizer`
per concurrent operation; its `last_spans` attribute belongs to its latest call.

## Overlapping detections

The redactor takes the union of connected overlapping intervals so no detected
tail survives. One placeholder covers each union. Its type is chosen by highest
confidence, then longest original span, then alphabetical type and earliest
start. Adjacent non-overlapping entities stay separate. After this resolution,
Presidio Anonymizer applies the replacement operators. Text outside the resolved
intervals remains unchanged, including Markdown hard breaks and indentation.

## Evaluate the actual file path

```bash
python -m eval.pipeline_bench outputs/validation/corpus --report-dir outputs/evaluation/pipeline
```

The command runs actual document extraction, normalization, detection, redaction
and output saving. It also runs the same detector on the generator's saved body
text for a comparison with the same body-label denominator. Reports separate
formats, locations, languages/entity types and image quality. JSON details retain
individual occurrence offsets and failed stages. Generated reports and processed
documents stay under ignored `outputs/` by default.

OCR defaults to `eng`; use `--ocr-language eng+fin` after installing both
Tesseract language data files for a bilingual run. Reports record the OCR setting,
Python/library/model versions, score threshold and actual source-file hashes.

Whole coverage requires a correctly typed detection to contain the entire
labelled value at every extracted occurrence. Partial matches are separate.
Body occurrence counts are checked against saved source text; other locations
have a known minimum of one occurrence per label. A missing extraction never
counts as successful detection. These are labelled-corpus detection measurements,
not evidence that every unlabelled identifier has been removed.

See [the pipeline integration guide](../docs/pipeline.md#connect-an-anonymization-module)
for the general callable interface.
