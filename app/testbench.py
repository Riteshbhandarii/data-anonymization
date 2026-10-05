"""Local document testbench. Run with ``streamlit run app/testbench.py``."""

import csv
import html
import io
import json
import subprocess
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Streamlit also runs this file directly, so set the project path before imports.
from app.logic import (
    STATUS_COLOURS,
    changed_intervals,
    highlight_html,
    label_intervals,
    recall_table,
    score_labels,
    split_sections,
    type_colours,
)
from detect.methods import METHODS
from pipeline.extractors import SUPPORTED_EXTENSIONS, extract_to_markdown
from pipeline.normalization import normalize_markdown

OUT = ROOT / "outputs"
CORPUS = OUT / "app-corpus"
REAL = ROOT / "corpus" / "real"
MODES = {"Replace with type": "replace", "Use consistent pseudonyms": "pseudonymize"}
PREVIEW_HEIGHT = 520

st.set_page_config(page_title="Document anonymization", layout="wide")


@st.cache_data(show_spinner=False)
def extract_cached(path: str, mtime: float, ocr_language: str) -> str:
    return normalize_markdown(extract_to_markdown(path, ocr_language=ocr_language))


@st.cache_resource(show_spinner=False)
def detector_cached(method: str):
    from detect.methods import get_detector
    return get_detector(method)


@st.cache_data(show_spinner=False)
def detect_cached(text: str, language: str, method: str):
    results = detector_cached(method).detect(text, language)
    return [(r.start, r.end, r.entity_type, float(r.score)) for r in results]


def ensure_corpus():
    if not (CORPUS / "corpus.json").exists():
        subprocess.run(
            [sys.executable, str(ROOT / "corpus" / "generate.py"), "--out", str(CORPUS), "--n", "2"],
            check=True, cwd=ROOT, capture_output=True,
        )
    return CORPUS


def corpus_docs():
    docs = {}
    for lab in sorted((ensure_corpus() / "labels").glob("*.json")):
        meta = json.loads(lab.read_text(encoding="utf-8"))
        docs[lab.stem] = (CORPUS / meta["file"], meta)
    return docs


def timed(label, fn):
    started = time.perf_counter()
    try:
        return fn(), time.perf_counter() - started, None
    except Exception as exc:  # noqa: BLE001 - display failures at their pipeline stage
        return None, time.perf_counter() - started, f"{label} failed: {exc}"


def sidebar():
    st.sidebar.header("Document")
    source = st.sidebar.radio("Source", ["Upload a file", "Synthetic corpus", "Real public file"])
    path, labels, lang_guess, is_real, stem = None, None, "en", False, None
    if source == "Upload a file":
        uploaded = st.sidebar.file_uploader("Choose a file", type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS])
        if uploaded is not None:
            folder = OUT / "app-uploads"
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / Path(uploaded.name).name
            path.write_bytes(uploaded.getvalue())
            stem = path.stem
    elif source == "Synthetic corpus":
        try:
            docs = corpus_docs()
            picked = st.sidebar.selectbox("Document", list(docs))
            path, meta = docs[picked]
            labels, lang_guess, stem = meta["entities"], meta["language"], picked
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"Could not prepare the corpus: {exc}")
    else:
        files = sorted(p for p in REAL.glob("*/*") if p.is_file()) if REAL.exists() else []
        if files:
            path = st.sidebar.selectbox("Document", files, format_func=lambda p: f"{p.parent.name}/{p.name}")
            is_real, stem = True, path.stem
        else:
            st.sidebar.info("Add public test files to corpus/real/ to use this source.")

    lang = st.sidebar.selectbox("Language", ["en", "fi"], index=["en", "fi"].index(lang_guess),
                               format_func=lambda value: {"en": "English", "fi": "Finnish"}[value],
                               key=f"lang-{stem}")
    st.sidebar.divider()
    method = st.sidebar.radio("Detector", list(METHODS), format_func=lambda value: METHODS[value]["label"])
    mode = st.sidebar.radio("Replacement", list(MODES))
    run = st.sidebar.button("Run document", type="primary", disabled=path is None, width="stretch")
    if path is None:
        st.sidebar.caption("Choose a document to enable Run.")
    return {"path": path, "labels": labels, "lang": lang, "method": method,
            "mode": MODES[mode], "is_real": is_real, "stem": stem, "run": run}


def run_stages(cfg):
    from redact import redact, validate_spans
    res = {"cfg": cfg, "times": {}, "errors": {}}
    path = Path(cfg["path"])
    ocr = "fin+eng" if cfg["lang"] == "fi" else "eng"
    text, duration, error = timed("Extraction", lambda: extract_cached(str(path), path.stat().st_mtime, ocr))
    res["times"]["extract"], res["text"] = duration, text
    if error:
        res["errors"]["extract"] = error
        return res

    def detect():
        return [SimpleNamespace(start=s, end=e, entity_type=t, score=score)
                for s, e, t, score in detect_cached(text, cfg["lang"], cfg["method"])]

    results, duration, error = timed("Detection", detect)
    res["times"]["detect"], res["results"] = duration, results
    if error:
        res["errors"]["detect"] = error
        return res
    if cfg["labels"] is not None:
        res["scored"] = score_labels(text, cfg["labels"], results)
    cleaned, duration, error = timed(
        "Redaction", lambda: redact(text, validate_spans(text, results), mode=cfg["mode"]),
    )
    res["times"]["clean"], res["clean"] = duration, cleaned
    if error:
        res["errors"]["clean"] = error
        return res
    folder = OUT / "app-runs" / cfg["method"]
    folder.mkdir(parents=True, exist_ok=True)
    res["saved"] = folder / f"{cfg['stem']}_anonymized.md"
    res["saved"].write_text(cleaned, encoding="utf-8")
    return res


def stage_error(res, key):
    if key not in res["errors"]:
        return False
    message = res["errors"][key]
    if key == "detect" and res["cfg"]["method"] == "rules-lg":
        message += " Install the large English/Finnish spaCy models or choose another detector."
    elif key == "detect" and res["cfg"]["method"] == "gliner":
        message += " Install requirements-app.txt; the first GLiNER run downloads model weights."
    st.error(message)
    return True


def document_view(text, intervals=(), colours=None, *, height=PREVIEW_HEIGHT):
    with st.container(height=height, border=True):
        st.html(highlight_html(text or "(empty)", intervals, colours or {}))


def summary_row(res):
    results, scored = res["results"], res.get("scored")
    columns = st.columns(4)
    columns[0].metric("Detections", len(results), border=True)
    if scored is not None:
        counts = Counter(item["status"] for item in scored)
        columns[1].metric("Found labels", f"{counts['covered']} / {len(scored)}", border=True)
        columns[2].metric("Missed labels", counts["missed"] + counts["absent"], border=True)
        columns[3].metric("Partial labels", counts["partial"], border=True)
    else:
        columns[1].metric("Entity types", len({item.entity_type for item in results}), border=True)
        columns[2].metric("Detection time", f"{res['times']['detect']:.2f} s", border=True)
        columns[3].metric("Label coverage", "Unlabelled", border=True)


def tab_extract(res):
    if stage_error(res, "extract"):
        return
    sections = split_sections(res["text"])
    hidden = [(title, body) for title, body, is_hidden in sections if is_hidden]
    cols = st.columns(3)
    cols[0].metric("Characters", f"{len(res['text']):,}", border=True)
    cols[1].metric("Hidden sections", len(hidden), border=True)
    cols[2].metric("Extraction time", f"{res['times']['extract']:.2f} s", border=True)
    if Path(res["cfg"]["path"]).suffix.lower() == ".csv":
        with Path(res["cfg"]["path"]).open(encoding="utf-8-sig", newline="") as stream:
            st.dataframe(list(csv.DictReader(stream)), hide_index=True, width="stretch")
    else:
        document_view(res["text"])
    if hidden:
        with st.expander(f"Metadata and other hidden content ({len(hidden)})"):
            title = st.selectbox("Section", range(len(hidden)), format_func=lambda i: hidden[i][0])
            document_view(hidden[title][1], height=320)


def tab_detect(res):
    if "extract" in res["errors"]:
        st.info("Extraction failed. Open Extract for details.")
        return
    if stage_error(res, "detect"):
        return
    summary_row(res)
    results, scored = res["results"], res.get("scored")
    counts = Counter(item.entity_type for item in results)
    mode = st.segmented_control("Highlight", ["By entity type", "By coverage"],
                                default="By entity type", disabled=scored is None)
    if mode == "By coverage" and scored is not None:
        intervals, colours = label_intervals(res["text"], scored), STATUS_COLOURS
        st.html('<div class="coverage-key">'
                '<span style="background:#86efac">Found</span> '
                '<span style="background:#fde047">Partial</span> '
                '<span style="background:#fca5a5">Missed</span></div>')
    else:
        selected = st.pills("Entity types", sorted(counts), selection_mode="multi", default=sorted(counts),
                            format_func=lambda entity: f"{entity.replace('_', ' ').title()} ({counts[entity]})")
        intervals = [(item.start, item.end, item.entity_type, item.score)
                     for item in results if item.entity_type in selected]
        colours = type_colours(counts)
    document_view(res["text"], intervals, colours)
    if scored is None:
        st.info("This source has no labels, so misses and recall cannot be measured.")
    else:
        missed = [item for item in scored if item["status"] != "covered"]
        with st.expander(f"Missed and partial labels ({len(missed)})"):
            if missed:
                st.dataframe([{"Type": item["type"], "Value": item["value"],
                               "Location": item["location"],
                               "Status": "Not extracted" if item["status"] == "absent" else item["status"].title()}
                              for item in sorted(missed, key=lambda item: (item["type"], item["status"]))],
                             hide_index=True, width="stretch")
            else:
                st.success("All supplied labels are fully covered.")


def tab_clean(res):
    if "extract" in res["errors"] or "detect" in res["errors"]:
        st.info("An earlier stage failed. Open Extract or Detect for details.")
        return
    if stage_error(res, "clean"):
        return
    summary_row(res)
    original_intervals, clean_intervals = changed_intervals(res["text"], res["clean"])
    left, right = st.columns(2)
    with left:
        st.subheader("Original")
        document_view(res["text"], original_intervals, {"REPLACED": "#fde68a"})
    with right:
        st.subheader("Anonymized")
        document_view(res["clean"], clean_intervals, {"REPLACED": "#a7f3d0"})
    st.download_button("Download Markdown", res["clean"].encode("utf-8"),
                       file_name=res["saved"].name, mime="text/markdown", type="primary")


def recall_chart(recalls):
    import altair as alt
    import pandas as pd
    data = pd.DataFrame([{"Dataset": dataset, "Method": METHODS.get(method, {}).get("label", method),
                          "Recall": recall} for (dataset, method), recall in recalls.items()])
    base = alt.Chart(data).encode(
        x=alt.X("Method:N", sort=[entry["label"] for entry in METHODS.values()],
                axis=alt.Axis(title=None, labelAngle=0, labelLimit=190)),
        y=alt.Y("Dataset:N", axis=alt.Axis(title=None)),
    )
    cells = base.mark_rect(cornerRadius=4).encode(
        color=alt.Color("Recall:Q", scale=alt.Scale(domain=[0, 1], scheme="blues"),
                        legend=alt.Legend(format=".0%", values=[0, 0.25, 0.5, 0.75, 1])),
        tooltip=["Dataset:N", "Method:N", alt.Tooltip("Recall:Q", format=".1%")],
    )
    labels = base.mark_text(fontSize=15, fontWeight=600).encode(
        text=alt.Text("Recall:Q", format=".1%"),
        color=alt.condition(alt.datum.Recall > 0.55, alt.value("white"), alt.value("#183047")),
    )
    return (cells + labels).properties(height=alt.Step(58)).configure_axis(labelFontSize=13)


def show_file(path):
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            st.dataframe(list(csv.DictReader(stream)), hide_index=True, width="stretch")
    elif path.suffix.lower() in {".md", ".txt"}:
        document_view(path.read_text(encoding="utf-8", errors="replace"))
    else:
        st.info(f"{path.name} · {path.stat().st_size:,} bytes")


def tab_results():
    import pandas as pd
    csv_path = OUT / "runs" / "results.csv"
    if not csv_path.exists():
        st.info("Run the benchmark to compare detectors here.")
        st.code("python -m eval.run_matrix --out outputs/runs", language="bash")
        return
    data = pd.read_csv(csv_path)
    recalls = recall_table(data.to_dict("records"))
    st.subheader("Recall by dataset and detector")
    if recalls:
        st.altair_chart(recall_chart(recalls), width="stretch")
    st.subheader("Entity types with the largest gaps")
    per = data.groupby(["entity_type", "method"])[["planted", "covered", "partial"]].sum().reset_index()
    per["recall"] = (per["covered"] / per["planted"]).where(per["planted"] > 0)
    per = per.sort_values(["recall", "planted"], ascending=[True, False], na_position="last")
    per["method"] = per["method"].map(lambda method: METHODS.get(method, {}).get("label", method))
    st.dataframe(per, hide_index=True, width="stretch", column_config={
        "entity_type": "Entity type", "method": "Detector", "planted": "Labels", "covered": "Found",
        "partial": "Partial", "recall": st.column_config.ProgressColumn("Recall", format="percent",
                                                                       min_value=0, max_value=1),
    })
    files = sorted((OUT / "runs").rglob("*_anonymized.md"))
    if files:
        with st.expander("Inspect a benchmark output"):
            st.write("Choose a saved anonymized document from a benchmark run.")
            picked = st.selectbox("Saved document", files,
                                  format_func=lambda path: str(path.relative_to(OUT / "runs")))
            show_file(picked)


def tab_pack():
    pack = OUT / "pack"
    files = sorted(path for path in pack.rglob("*") if path.is_file()) if pack.exists() else []
    if not files:
        st.info("Build a pack to browse documents, prompts and answer sheets here.")
        st.code("python -m eval.make_pack --runs outputs/runs --pack outputs/pack", language="bash")
        return
    st.write("Browse the pack by group, or download the complete set.")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(pack))
    st.download_button("Download pack", buffer.getvalue(), file_name="pack.zip", mime="application/zip")
    groups = {}
    for path in files:
        relative = path.relative_to(pack)
        group = relative.parts[0] if len(relative.parts) > 1 else "Overview and answer sheets"
        groups.setdefault(group, []).append(path)
    names = {"docs": "Documents", "paste": "Prompts"}
    group = st.pills("Group", list(groups), default=next(iter(groups)),
                     format_func=lambda value: f"{names.get(value, value)} ({len(groups[value])})")
    if group is None:
        return
    picked = st.selectbox("Pack file", groups[group],
                          format_func=lambda path: str(path.relative_to(pack)))
    show_file(picked)


def main():
    st.html("""<style>
      .block-container { padding-top: 1.4rem; }
      .app-header { display:flex; align-items:baseline; gap:1rem; margin-bottom:1rem; }
      .app-header strong { font-size:1.55rem; color:#183047; }
      .app-header span { color:#526578; }
      .coverage-key { margin-bottom:.6rem; }
      .coverage-key span { padding:3px 10px; border-radius:5px; color:#183047; }
      [data-testid="stMetric"] { padding:.8rem 1rem; }
      [data-testid="stMetricValue"] { font-size:1.7rem; }
      @media (max-width:640px) {
        .block-container { padding-top:4.25rem; }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
          display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.6rem;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div {
          width:100% !important; min-width:0 !important;
        }
        [data-testid="stMetricValue"] { font-size:1.4rem; }
        .app-header { flex-wrap:wrap; gap:.25rem .75rem; }
        .app-header strong { font-size:1.2rem; }
        .app-header span { display:none; }
      }
    </style><div class="app-header"><strong>Document anonymization</strong><span>Local testbench</span></div>""")
    cfg = sidebar()
    if cfg["run"]:
        with st.spinner("Processing document. The first run loads the detector model."):
            st.session_state["res"] = run_stages(cfg)
    res = st.session_state.get("res")
    if res is not None:
        actual = res["cfg"]
        st.html('<div class="run-context">' + html.escape(
            f"{Path(actual['path']).name} · {METHODS[actual['method']]['label']} · "
            f"{'Finnish' if actual['lang'] == 'fi' else 'English'}"
        ) + "</div>")
        if actual["is_real"]:
            st.warning("Real document: review detected and replaced content before sharing the output.")
    extract, detect, clean, results, pack = st.tabs(["Extract", "Detect", "Clean", "Results", "Pack"])
    with results:
        tab_results()
    with pack:
        tab_pack()
    for tab, render in ((extract, tab_extract), (detect, tab_detect), (clean, tab_clean)):
        with tab:
            if res is None:
                st.info("Choose a document and select Run document.")
            else:
                render(res)


if __name__ == "__main__":
    main()
