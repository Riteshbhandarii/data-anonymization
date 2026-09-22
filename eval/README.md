# eval

Detection metrics and the re-identification harness. Protocol in ../docs/evaluation.md.

## Detector baseline

```bash
python3 corpus/generate.py --out ./bench --n 25
python3 eval/bench.py ./bench
```

Scores a detector against the text the generator saved beside each document, so
a miss is the detector's and not a reader that never reached the value. Body
labels only; metadata, notes and hidden sheets need the extraction pipeline.

Results land in `baselines/`, committed because every value in the synthetic
corpus is invented. Runs over real documents go in `results/`, which git
ignores. Each result carries the versions, models, threshold and corpus seed it
came from, and two runs are comparable only when those match.
