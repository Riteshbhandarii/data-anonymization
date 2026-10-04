# Anonymization testbench

A local Streamlit page for watching the pipeline work: extract, detect, clean.
Everything runs on this machine and no document content is sent to any network
service.

```bash
export PATH="/opt/homebrew/bin:$PATH"   # macOS: a working arm64 tesseract
streamlit run app/testbench.py
```

Sidebar: pick a source (upload, the fake corpus, or a public file from
`corpus/real/`), the language, a detector method from `detect/methods.py`, and
the replacement style (`[PERSON]` or `[PERSON_1]`), then press Run.

| Tab | Shows |
|---|---|
| 1 Extract | The Markdown, with metadata, notes, comments, tracked changes, headers and footers listed separately |
| 2 Detect | Detected spans coloured by type. For the fake corpus, labelled values marked found, partial or missed, using `eval.bench.found()` |
| 3 Clean | Original beside anonymized; download, also saved to `outputs/app-runs/<method>/` |
| 4 Results | Recall tables and chart from `outputs/runs/results.csv` (made by `python -m eval.run_matrix`) |
| 5 Pack | Contents of `outputs/pack/` and a zip download |

The fake corpus is generated on first use into `outputs/app-corpus` (seed 42,
two documents per format and language). Hidden worksheets carry no marker in the
extracted Markdown, so they show up as ordinary sheets. Labelled values that are
not in the extracted text are reported as such and left out of the count.

Real documents containing people's names must be checked by eye before any
manual upload to a public AI.

`app/logic.py` holds the pure helpers; `tests/test_app_logic.py` covers them
without loading any language model.
