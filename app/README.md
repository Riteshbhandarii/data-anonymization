# Anonymization testbench

A local Streamlit page for watching the pipeline work: extract, detect, clean.
Everything runs on this machine and no document content is sent to any network
service.

Install the local UI and detector dependencies, then start it from the project
root:

```bash
python -m pip install -r requirements-app.txt
python -m spacy download en_core_web_sm
python -m spacy download fi_core_news_sm
python -m streamlit run app/testbench.py
```

Tesseract must be on `PATH` for image and scanned-document extraction; see the
[pipeline setup](../docs/pipeline.md). GLiNER works on CPU and downloads its model
weights on first use. Large spaCy models are needed only for the corresponding
detector option. The other detector options remain available independently.

Sidebar: pick a source (upload, the fake corpus, or a public file from
`corpus/real/`), the language, a detector method from `detect/methods.py`, and
the replacement style (`[PERSON]` or `[PERSON_1]`), then press Run.

| Tab | Shows |
|---|---|
| Extract | A rendered document or CSV table, plus a selector for hidden content |
| Detect | Summary counts first; one view switches between entity types and labelled coverage. Type filters show detection counts; misses are in an expandable table |
| Clean | The same summary, with changes highlighted in equal-height original/anonymized previews and a Markdown download |
| Results | A 0–100% recall heatmap and an entity table sorted by lowest recall, from `outputs/runs/results.csv` |
| Pack | Groups of documents, prompts and answer sheets, with one selected-file viewer and a ZIP download |

The fake corpus is generated on first use into `outputs/app-corpus` (seed 42,
two documents per format and language). Hidden worksheets carry no marker in the
extracted Markdown, so they show up as ordinary sheets. Labelled values that are
not in the extracted text remain in the summary denominator and are shown as
"Not extracted" in the misses table. Unlabelled sources show detection counts
and type filters; they do not display an invented recall score.

Document previews use `st.html` with escaped content and original character
offsets. The renderer supports the pipeline's Markdown headings, tables, lists
and common inline formatting. Links and images show their labels without
fetching external resources. Preview formatting never changes the text sent to
detection, redaction or the downloaded Markdown. Inline mark colours and titles
are checked in the browser after Streamlit's HTML sanitization.

`.streamlit/config.toml` supplies the shared light theme and minimal local
toolbar. Summary cards appear before document previews; narrow screens use two
cards per row.

Real documents containing people's names must be checked by eye before any
manual upload to a public AI.

`app/logic.py` holds the pure helpers. `tests/test_app_logic.py`,
`tests/test_testbench.py` and `tests/test_methods.py` cover rendering, summary
denominators, filters, chart scale, pack navigation and detector routing without
downloading model weights. CI runs these tests and includes `app/` in linting.
