# eval

Detection metrics and the re-identification harness. Protocol in ../docs/evaluation.md.

## Detector baseline

```bash
python3 -m spacy download en_core_web_sm
python3 -m spacy download fi_core_news_sm
python3 corpus/generate.py --out ./bench --n 25
python3 eval/bench.py ./bench
```

The model weights are separate packages that pip cannot resolve from
`requirements.txt`, so they are downloaded explicitly. `bench.py` records which
versions it loaded, since new weights under the same name change every number.

Scores a detector against the text the generator saved beside each document, so
a miss is the detector's and not a reader that never reached the value. Body
labels only; metadata, notes and hidden sheets are not in that text and need the
extraction pipeline.

Results land in `results/`, which git ignores. `--baseline` writes the committed
`baselines/presidio.json` instead, and is only for the synthetic corpus, whose
values are invented. Each result carries the versions, models, threshold and
corpus seed it came from, and two runs are comparable only when those match.

`results/presidio-misses.json` lists every failure with its value verbatim.
Treat that file like the documents it was made from.

## Full pipeline comparison

`pipeline_bench.py` uses the same detector configuration as `bench.py`, but reads
actual documents through extraction, normalization and redaction. Body-only
rows retain the detector baseline's denominator. Non-body locations are
reported separately; extraction losses, partial detections and complete
detections remain distinguishable.

```bash
python -m eval.pipeline_bench outputs/validation/corpus --report-dir outputs/validation/pipeline --ocr-language eng+fin
```

Use `python -m eval.pipeline_bench --help` for output options. See
[redact/README.md](../redact/README.md) for the detector/span/redactor contracts.
The existing `baselines/presidio.json` is a historical detector-only result;
do not compare it directly to a different generated corpus or model version.

## Model experiments

`create_study.py` creates fictional documents with known relationships and
answers. `study.py prepare` extracts them and creates raw, redacted and
pseudonymized requests locally. `study.py run` only inspects the request count
unless `--execute` is supplied.

See [model-evaluation.md](../docs/model-evaluation.md) for the suite schema,
controls, scoring, alias scopes and external execution commands. Actual model
evaluation is separate from offline harness tests.

## OCR comparison

`ocr_bench.py` compares local OCR engines on the same generated PNG files.
See [ocr-survey.md](../docs/ocr-survey.md) for supported engines, commands,
language configurations and measured results.
