"""Local anonymization testbench. Run: streamlit run app/testbench.py

Everything runs on this machine; no document content is sent anywhere.
"""

import csv
import io
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.logic import (
    STATUS_COLOURS,
    highlight_html,
    label_intervals,
    recall_table,
    score_labels,
    split_sections,
    summarize,
    type_colours,
)
from pipeline.extractors import SUPPORTED_EXTENSIONS, extract_to_markdown
from pipeline.normalization import normalize_markdown

OUT = ROOT / "outputs"
CORPUS = OUT / "app-corpus"
REAL = Path("/Users/riteshbhandari/code/data-anonymization/corpus/real")
MODES = {"[PERSON]  (replace)": "replace", "[PERSON_1]  (pseudonymize)": "pseudonymize"}

st.set_page_config(page_title="Anonymization testbench", layout="wide")


# ---------------------------------------------------------------- cached work
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
        subprocess.run([sys.executable, str(ROOT / "corpus" / "generate.py"), "--out",
                        str(CORPUS), "--n", "2"], check=True, cwd=ROOT,
                       capture_output=True)
    return CORPUS


def corpus_docs():
    root = ensure_corpus()
    docs = {}
    for lab in sorted((root / "labels").glob("*.json")):
        meta = json.loads(lab.read_text(encoding="utf-8"))
        docs[lab.stem] = (root / meta["file"], meta)
    return docs


def timed(label, fn, *a):
    t = time.perf_counter()
    try:
        return fn(*a), time.perf_counter() - t, None
    except Exception as exc:  # noqa: BLE001 - shown per stage, never crashes the page
        return None, time.perf_counter() - t, f"{label} failed: {exc}"


# -------------------------------------------------------------------- sidebar
def sidebar():
    from detect.methods import METHODS
    st.sidebar.title("Testbench")
    st.sidebar.caption("Local only. Nothing leaves this machine.")
    source = st.sidebar.radio("Data source", ["Upload a file", "Fake corpus", "Real public file"])
    path, labels, lang_guess, is_real, stem = None, None, "en", False, None

    if source == "Upload a file":
        up = st.sidebar.file_uploader(
            "File", type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS])
        if up:
            dest = OUT / "app-uploads"
            dest.mkdir(parents=True, exist_ok=True)
            path = dest / Path(up.name).name
            path.write_bytes(up.getvalue())
            stem = path.stem
    elif source == "Fake corpus":
        try:
            docs = corpus_docs()
            pick = st.sidebar.selectbox("Document", list(docs))
            path, meta = docs[pick]
            labels, lang_guess, stem = meta["entities"], meta["language"], pick
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"Could not prepare the fake corpus: {exc}")
    else:
        files = sorted(p for p in REAL.glob("*/*") if p.is_file()) if REAL.exists() else []
        if not files:
            st.sidebar.warning("No real files found.")
        else:
            pick = st.sidebar.selectbox("File", files, format_func=lambda p: f"{p.parent.name}/{p.name}")
            path, is_real, stem = pick, True, pick.stem
            st.sidebar.info("Real document. Check output by eye before sharing anything.")

    langs = ["en", "fi"]
    lang = st.sidebar.selectbox("Language", langs, index=langs.index(lang_guess),
                                key=f"lang-{stem}")
    method = st.sidebar.radio("Method", list(METHODS),
                              format_func=lambda m: f"{m}: {METHODS[m]['label']}")
    st.sidebar.caption(METHODS[method]["about"])
    mode_label = st.sidebar.radio("Replacement", list(MODES))
    run = st.sidebar.button("Run", type="primary", disabled=path is None)
    return {"path": path, "labels": labels, "lang": lang, "method": method,
            "mode": MODES[mode_label], "is_real": is_real, "stem": stem, "run": run}


# ------------------------------------------------------------------- pipeline
def run_stages(cfg):
    from redact import redact, validate_spans
    res = {"cfg": cfg, "times": {}, "errors": {}}
    path = Path(cfg["path"])
    ocr = "fin+eng" if cfg["lang"] == "fi" else "eng"

    text, dt, err = timed("Extraction", lambda: extract_cached(str(path), path.stat().st_mtime, ocr))
    res["times"]["extract"], res["text"] = dt, text
    if err:
        res["errors"]["extract"] = err
        return res

    def detect():
        return [SimpleNamespace(start=s, end=e, entity_type=t, score=sc)
                for s, e, t, sc in detect_cached(text, cfg["lang"], cfg["method"])]
    results, dt, err = timed("Detection", detect)
    res["times"]["detect"], res["results"] = dt, results
    if err:
        res["errors"]["detect"] = err
        return res
    if cfg["labels"] is not None:
        res["scored"] = score_labels(text, cfg["labels"], results)

    def clean():
        return redact(text, validate_spans(text, results), mode=cfg["mode"])
    clean_text, dt, err = timed("Redaction", clean)
    res["times"]["clean"], res["clean"] = dt, clean_text
    if err:
        res["errors"]["clean"] = err
        return res
    folder = OUT / "app-runs" / cfg["method"]
    folder.mkdir(parents=True, exist_ok=True)
    res["saved"] = folder / f"{cfg['stem']}_anonymized.md"
    res["saved"].write_text(clean_text, encoding="utf-8")
    return res


def timing(res, key):
    if key in res["times"]:
        st.caption(f"Stage time: {res['times'][key]:.2f} s")


def stage_error(res, key):
    if key in res["errors"]:
        msg = res["errors"][key]
        if "lg" in str(res["cfg"]["method"]) and key == "detect":
            msg += (" The large spaCy models may not be installed; try "
                    "`python -m spacy download en_core_web_lg fi_core_news_lg` or pick another method.")
        st.error(msg)
        return True
    return False


# ----------------------------------------------------------------------- tabs
def tab_extract(res):
    if stage_error(res, "extract"):
        return
    timing(res, "extract")
    sections = split_sections(res["text"])
    hidden = [s for s in sections if s[2]]
    st.subheader("Hidden places")
    if hidden:
        st.caption("Metadata, notes, comments, tracked changes, headers and footers. "
                   "A reader of the page never sees these, but the anonymizer must.")
        for title, body, _ in hidden:
            with st.expander(title, expanded=True):
                st.code(body or "(empty)", language="markdown")
    else:
        st.info("No hidden sections in this document.")
    st.subheader("Full Markdown")
    st.code(res["text"], language="markdown", wrap_lines=True)


def tab_detect(res):
    if "extract" in res["errors"]:
        return st.info("Extraction failed; see tab 1.")
    if stage_error(res, "detect"):
        return
    timing(res, "detect")
    text, results = res["text"], res["results"]
    colours = type_colours(r.entity_type for r in results)
    st.markdown(f"**{len(results)} detections** by "
                f"`{res['cfg']['method']}` ({res['cfg']['lang']}).")
    if colours:
        st.markdown(" ".join(
            f'<span style="background:{c};color:#111;padding:1px 6px;border-radius:3px">{t}</span>'
            for t, c in colours.items()), unsafe_allow_html=True)
    st.markdown(highlight_html(text, [(r.start, r.end, r.entity_type, r.score) for r in results],
                               colours), unsafe_allow_html=True)

    scored = res.get("scored")
    if scored is None:
        return st.caption("No labels for this source, so recall cannot be scored.")
    st.divider()
    got, total, misses = summarize(scored)
    st.subheader(f"Found {got} of {total} labelled values")
    absent = sum(s["status"] == "absent" for s in scored)
    if absent:
        st.caption(f"{absent} labelled value(s) are not in the extracted text and are not counted "
                   "(an extraction problem, not a detection one).")
    st.markdown(" ".join(
        f'<span style="background:{c};color:#111;padding:1px 6px;border-radius:3px">{s}</span>'
        for s, c in STATUS_COLOURS.items()), unsafe_allow_html=True)
    st.markdown(highlight_html(text, label_intervals(text, scored), STATUS_COLOURS,
                               lambda s: s), unsafe_allow_html=True)
    if misses:
        st.markdown("**Misses by type**")
        for t, vals in sorted(misses.items()):
            st.write(f"- **{t}** ({len(vals)}): " + "; ".join(vals))
    else:
        st.success("Every labelled value is fully covered.")


def tab_clean(res):
    if "extract" in res["errors"] or "detect" in res["errors"]:
        return st.info("An earlier stage failed; see tabs 1 and 2.")
    if stage_error(res, "clean"):
        return
    timing(res, "clean")
    a, b = st.columns(2)
    a.markdown("**Original**")
    a.code(res["text"], language="markdown", wrap_lines=True)
    b.markdown("**Anonymized**")
    b.code(res["clean"], language="markdown", wrap_lines=True)
    st.download_button("Download anonymized .md", res["clean"].encode("utf-8"),
                       file_name=res["saved"].name, mime="text/markdown")
    st.caption(f"Also saved to `{res['saved'].relative_to(ROOT)}`")


def tab_results():
    import pandas as pd
    csv_path = OUT / "runs" / "results.csv"
    if not csv_path.exists():
        st.info("No benchmark results yet. Produce them with:")
        st.code("python -m eval.run_matrix", language="bash")
    else:
        df = pd.read_csv(csv_path)
        rows = df.to_dict("records")
        rec = recall_table(rows)
        pivot = pd.Series(rec).unstack() if rec else pd.DataFrame()
        st.subheader("Recall by dataset and method")
        st.dataframe(pivot.style.format("{:.1%}"), use_container_width=True)
        if not pivot.empty:
            st.bar_chart(pivot)
        st.subheader("Per entity type")
        per = df.groupby(["entity_type", "method"])[["planted", "covered", "partial"]].sum()
        per["recall"] = (per["covered"] / per["planted"]).where(per["planted"] > 0)
        st.dataframe(per.reset_index().style.format({"recall": "{:.1%}"}),
                     use_container_width=True, hide_index=True)
    files = sorted(p for p in (OUT / "runs").rglob("*") if p.is_file() and p.suffix == ".md") \
        if (OUT / "runs").exists() else []
    if files:
        st.subheader("Anonymized files from runs")
        pick = st.selectbox("File", files, format_func=lambda p: str(p.relative_to(OUT / "runs")))
        st.code(pick.read_text(encoding="utf-8", errors="replace")[:20000], language="markdown",
                wrap_lines=True)


def tab_pack():
    st.warning("Real documents that contain people's names must be checked by eye before any "
               "manual upload to a public AI. A detector misses things; the benchmark only "
               "covers planted values.")
    pack = OUT / "pack"
    if not pack.exists():
        return st.info("No pack yet. It is built by the other worktree into `outputs/pack/` "
                       "(anonymized documents, `prompts.md`, `answers.csv`).")
    files = sorted(p for p in pack.rglob("*") if p.is_file())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(pack))
    st.download_button("Download pack (.zip)", buf.getvalue(), file_name="pack.zip",
                       mime="application/zip")
    for p in files:
        with st.expander(str(p.relative_to(pack))):
            if p.suffix == ".csv":
                st.dataframe(list(csv.DictReader(p.open(encoding="utf-8"))))
            elif p.suffix in {".md", ".txt"}:
                st.markdown(p.read_text(encoding="utf-8")) if p.name == "prompts.md" else \
                    st.code(p.read_text(encoding="utf-8"), language="markdown", wrap_lines=True)
            else:
                st.caption(f"{p.stat().st_size} bytes")


# ----------------------------------------------------------------------- main
def main():
    cfg = sidebar()
    st.title("Anonymization testbench")
    if cfg["path"] is not None and cfg["is_real"]:
        st.warning("Real document. Review the output by eye.")
    if cfg["run"]:
        with st.spinner("Running (the first run of a method loads spaCy models)..."):
            st.session_state["res"] = run_stages(cfg)
    res = st.session_state.get("res")
    t1, t2, t3, t4, t5 = st.tabs(["1 Extract", "2 Detect", "3 Clean", "4 Results", "5 Pack"])
    with t4:
        tab_results()
    with t5:
        tab_pack()
    if res is None:
        for t in (t1, t2, t3):
            t.info("Pick a source in the sidebar and press Run.")
        return
    st.caption(f"Last run: `{Path(res['cfg']['path']).name}`, method `{res['cfg']['method']}`, "
               f"language `{res['cfg']['lang']}`, replacement `{res['cfg']['mode']}`.")
    for tab, fn in ((t1, tab_extract), (t2, tab_detect), (t3, tab_clean)):
        with tab:
            fn(res)


main()
