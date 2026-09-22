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
