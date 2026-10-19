# Limitations and open questions

[Docs index](README.md) › Limitations

This page lists what the evidence in this repository does not show, and the decisions that are still open. Each limitation links to the result it qualifies.

## Limits of the evidence

### Data

- No real company document was hand-labelled. Accuracy on real text comes from
  human-labelled public datasets: TAB (English court judgments) and Turku NER
  (Finnish). Format-specific accuracy on real office files is unmeasured.
  The 17 real public UK documents were processed but have no labels.
- The synthetic corpus uses generated templates, one font for images and
  identifier formats that the project's own patterns were written for. Its
  scores are optimistic. Paired resolution variants of an image are not
  independent documents.
- Datasets use different taxonomies and denominators, and some classes accept
  any detected type. Scores are never pooled into one accuracy figure.
  Matrix precision is a lower bound because annotations are incomplete
  ([dataset-audit-runs.md](dataset-audit-runs.md)).

### Detection (RQ2)

- The contextual-identifier test uses 24 synthetic documents written by the same team that wrote the
  contextual prompt, one run per configuration ([contextual-llm.md](contextual-llm.md)).
- The local-LLM comparison covers 14 documents and 146 body labels, with no
  ground truth for contextual quasi-identifiers. Added detections are not
  evidence of reduced re-identification ([local-llm-comparison.md](local-llm-comparison.md)).
- Extraction misses come from OCR character errors in images; a missed value
  is not detected afterwards ([residual-misses.md](residual-misses.md)).

### Re-identification (RQ3)

- One public model (ChatGPT Free, self-reported GPT-6), one collector, one run
  per prompt, four real public documents. Rates are not population estimates.
- Every prompt allowed the model to refuse. A best-guess or adversarial prompt
  was not tested.
- Web search was not explicitly enabled and the search-enabled condition was
  not run, against the original protocol ([evaluation.md](evaluation.md)).
  Linking residual clues to public information through search is unmeasured.
- Logos, letterheads and other image content were not tested against a public
  model ([public-ai-results.md](public-ai-results.md)).

### Usefulness (RQ4)

- Three fictional memos and nine fixed questions per language, answered by one
  local model. Exact-answer scoring credits guesses; evidence-supported counts
  are reported separately ([utility-impact.md](utility-impact.md#evidence-supported-answers)).
- Runtime is specific to one 16 GiB Mac, cached models and the stated loading
  scope. No peak memory, energy, cash cost or staff-time benchmark was run.

### Formats and content

- Tested formats: TXT/MD, CSV, DOCX, XLSX, PPTX, PDF and PNG. Scanned
  multi-page PDF, email, logs and code, CAD and audio/video have no benchmark
  here; the [options map](options-map.md) marks them NOT TESTED.
- Some Office embedded objects and PDF non-text features are not read
  ([reader audit](archive/pre-review-audit.md)). Output is Markdown, not a
  rebuilt Office file.
- Anonymization does not protect confidential business information such as
  pricing, designs, source code or strategy. A redacted design document is
  still a design document.
- No detector score is a compliance or disclosure guarantee.

## Open questions

Decisions the project has not made. Where the repository already follows a
working practice, it is stated; the decision itself stays open.

### Scope

- Is the deliverable a working tool, a research report, or both, and which is
  primary?
- How many formats must be covered? Word, Excel, PowerPoint and scanned PDF are
  four different problems.
- Do the partner organisations share a format profile, or does each need its
  own set?

### Output format

The pipeline outputs Markdown; see [the output contract](pipeline.md#output-contract)
for paths, encoding and the returned result.

- The corpus generates Finnish identity codes with invalid checksums on
  purpose. Should a real deployment validate the checksum or match the shape
  only? Validating avoids false positives on look-alike numbers but misses
  typos and malformed codes that still identify someone; matching the shape
  catches both and over-flags.

Benchmark status: `eval/bench.py --custom` uses a shape-only pattern with no
checksum validation (`detect/pattern_recognizers.py`), because the corpus codes
are invalid by design. That is a benchmark choice, not an answer to the
question above. Presidio 2.2.364 does not load its Finnish identity code
recognizer by default for `en` or `fi`, so the default run had no recognizer at
all. Whether it would accept these codes if enabled has not been measured.

### Legal

- With no provider agreement, is there any lawful basis for sending personal
  data at all, or is the answer simply that it is not sent?
- Who decides that a document is clean enough to send?
- Who carries responsibility when the tool misses something?
- Is a DPIA in scope, and who owns it?

### Data

- Real data or synthetic only? Current practice: public and synthetic data only.
- Which languages? Current practice: English and Finnish are measured; Swedish
  is not. Finnish NER quality is lower than English.
- Is any of the data special category, such as health or union membership?

### Build

- Build on Presidio, or adopt a commercial tool, and is there budget? Current
  practice: a local Presidio/GLiNER pipeline is built and commercial services
  are compared on small synthetic samples ([options map](options-map.md)).
- Is dedicated compute available, or is the GPU shared? A local LLM detector
  needs it continuously, not only for demos.
- Does this build on existing internal work in the same space, or duplicate it?

### Product

- Is the goal a tool so people stop pasting into public models on their own,
  or an outright block? Those need very different things.
- For CAD and 3D: is the whole model file ever sent, or only the metadata and
  drawings extracted from it? A language model cannot read a STEP file, so the
  real exposure is the extraction.

## Related

- [Public AI results](public-ai-results.md)
- [Utility impact](utility-impact.md)
- [Local LLM comparison](local-llm-comparison.md)
- [Options map](options-map.md)
