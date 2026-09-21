"""Streamlit demo for the local file-to-Markdown anonymization pipeline."""

from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

from pipeline import PipelineError, SUPPORTED_EXTENSIONS, run_pipeline

st.set_page_config(page_title="Data Anonymization", page_icon="🔒", layout="centered")
st.title("Local Data Anonymization")
st.write(
    "Upload a supported file. The application extracts its text locally, "
    "runs anonymization twice, and creates a Markdown file."
)
st.warning(
    "The built-in anonymizer is a demonstration baseline for structured "
    "identifiers. Connect the team's anonymization function before processing real data."
)

uploaded_file = st.file_uploader(
    "Choose a file",
    type=[extension.removeprefix(".") for extension in SUPPORTED_EXTENSIONS],
)
ocr_language = st.text_input(
    "OCR language",
    value="eng",
    help="Use a Tesseract language code such as eng or fin.",
)

if uploaded_file is not None and st.button("Create anonymized Markdown", type="primary"):
    for state_key in ("output_markdown", "output_name", "saved_path"):
        st.session_state.pop(state_key, None)

    with TemporaryDirectory(prefix="data-anonymization-") as temporary_dir:
        input_path = Path(temporary_dir) / Path(uploaded_file.name).name
        input_path.write_bytes(uploaded_file.getbuffer())

        status = st.status("Processing file", expanded=True)

        def show_progress(message: str) -> None:
            status.write(message)

        try:
            result = run_pipeline(
                input_path,
                ocr_language=ocr_language.strip() or "eng",
                progress=show_progress,
            )
        except PipelineError as exc:
            status.update(label="Processing failed", state="error", expanded=True)
            st.error(str(exc))
        except Exception as exc:
            status.update(label="Processing failed", state="error", expanded=True)
            st.exception(exc)
        else:
            status.update(label="Markdown created", state="complete", expanded=False)
            st.session_state["output_markdown"] = result.markdown
            st.session_state["output_name"] = result.output_path.name
            st.session_state["saved_path"] = str(result.output_path)

if "output_markdown" in st.session_state:
    st.success(f"Saved locally to {st.session_state['saved_path']}")
    st.subheader("Markdown preview")
    st.text_area(
        "Generated content",
        value=st.session_state["output_markdown"],
        height=360,
        label_visibility="collapsed",
    )
    st.download_button(
        "Download Markdown",
        data=st.session_state["output_markdown"],
        file_name=st.session_state["output_name"],
        mime="text/markdown",
    )
