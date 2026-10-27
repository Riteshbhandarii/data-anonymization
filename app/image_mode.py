"""Local screenshot review and flattened PNG export."""

import base64
import hashlib
import io
import json
import uuid
import warnings

import streamlit as st
from PIL import Image, ImageOps

from detect.methods import METHODS
from pipeline.extractors import IMAGE_EXTENSIONS
from redact.core import validate_spans
from redact.image import draw_boxes, expand_to_lines, layout, ocr_words, words_in_spans


def load_image(data: bytes) -> Image.Image:
    """Load one visible frame, apply orientation, and discard source metadata."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as source:
            if getattr(source, "n_frames", 1) != 1:
                raise ValueError("Choose a single-frame image; export the required page or frame first.")
            return draw_boxes(ImageOps.exif_transpose(source), [])


def png_bytes(image: Image.Image) -> bytes:
    """Encode only visible RGB pixels, without the original metadata."""
    buffer = io.BytesIO()
    draw_boxes(image, []).save(buffer, format="PNG")
    return buffer.getvalue()


def analyze_image(image, detector, *, language="en", ocr_scale=1, whole_lines=False):
    """Create editable masks in the cropped image's original pixel coordinates."""
    words = ocr_words(image, "eng+fin" if language == "fi" else "eng", scale=ocr_scale)
    text, ranges = layout(words)
    spans = validate_spans(text, detector.detect(text, language=language)) if text else []
    automatic = words_in_spans(ranges, spans)
    if whole_lines:
        automatic = expand_to_lines(words, automatic)
    return {"image": image, "words": words, "automatic": automatic,
            "selected": list(automatic)}


def validate_selection(selected, word_count):
    """Accept a complete selection of valid OCR word indices from the browser."""
    if not isinstance(selected, list) or any(
        type(index) is not int or not 0 <= index < word_count for index in selected
    ):
        raise ValueError("Select existing OCR words.")
    return sorted(set(selected))


_EDITOR_HTML = ('<div class="editor-scroll"><div class="image-editor">'
                '<img alt="Screenshot with selectable OCR words"></div></div>')
_EDITOR_CSS = """
.editor-scroll { overflow:auto; max-height:520px; width:100%; }
.image-editor { position:relative; width:100%; line-height:0; }
.image-editor img { width:100%; display:block; }
.image-editor button { position:absolute; margin:0; padding:0; min-height:0;
  box-sizing:border-box; border:1px solid #087e8b; background:rgba(8,126,139,.08);
  cursor:pointer; border-radius:0; }
.image-editor button[aria-pressed="true"] { background:rgba(0,0,0,.8); border-color:#f59e0b; }
.image-editor button:hover, .image-editor button:focus-visible {
  outline:3px solid #f59e0b; outline-offset:2px; z-index:1; }
"""
_EDITOR_JS = """
export default function(component) {
  const { parentElement, data, setTriggerValue } = component;
  const root = parentElement.querySelector('.image-editor');
  root.style.width = `${data.zoom * 100}%`;
  root.querySelector('img').src = data.image;
  root.querySelectorAll('button').forEach(button => button.remove());
  const selected = new Set(data.selected);
  data.words.forEach((word, index) => {
    const button = document.createElement('button');
    const masked = selected.has(index);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(masked));
    button.setAttribute('aria-label', `${masked ? 'Unmask' : 'Mask'} word ${index + 1}: ${word.text}`);
    button.title = `${masked ? 'Unmask' : 'Mask'}: ${word.text}`;
    button.style.left = `${100 * word.left / data.width}%`;
    button.style.top = `${100 * word.top / data.height}%`;
    button.style.width = `${100 * word.width / data.width}%`;
    button.style.height = `${100 * word.height / data.height}%`;
    button.onclick = () => {
      if (selected.has(index)) selected.delete(index);
      else selected.add(index);
      const masked = selected.has(index);
      button.setAttribute('aria-pressed', String(masked));
      button.setAttribute('aria-label', `${masked ? 'Unmask' : 'Mask'} word ${index + 1}: ${word.text}`);
      button.title = `${masked ? 'Unmask' : 'Mask'}: ${word.text}`;
      // Streamlit may coalesce rapid events. Send the complete current selection.
      setTriggerValue('toggle', {
        selected: Array.from(selected), revision: data.revision, nonce: crypto.randomUUID()
      });
    };
    root.appendChild(button);
  });
}
"""


def _word_editor(result, zoom=1):
    # Register in the active Streamlit run; do not cache a renderer across sessions.
    editor = st.components.v2.component(
        "screenshot_word_editor", html=_EDITOR_HTML, css=_EDITOR_CSS, js=_EDITOR_JS,
    )
    image = result["image"]
    event = editor(
        data={"image": "data:image/png;base64," + base64.b64encode(png_bytes(image)).decode("ascii"),
              "width": image.width, "height": image.height, "zoom": zoom,
              "words": [{"text": word.text, "left": word.left, "top": word.top,
                         "width": word.width, "height": word.height} for word in result["words"]],
              "selected": result["selected"], "revision": result["revision"]},
        key="image-editor-" + result["revision"], on_toggle_change=lambda: None,
    )
    return event.toggle


def render_image_mode(corpus_docs, detector_factory):
    """Render a screenshot-only flow without altering the text pipeline."""
    st.sidebar.header("Screenshot")
    source = st.sidebar.radio("Image source", ["Upload image", "Synthetic screenshot"])
    data = None
    try:
        if source == "Upload image":
            uploaded = st.sidebar.file_uploader(
                "Choose an image", type=sorted(ext.lstrip(".") for ext in IMAGE_EXTENSIONS),
                key="image-upload",
            )
            if uploaded is not None:
                data = uploaded.getvalue()
        else:
            screenshots = {name: item for name, item in corpus_docs().items()
                           if item[0].suffix.lower() in IMAGE_EXTENSIONS}
            if screenshots:
                picked = st.sidebar.selectbox("Screenshot", list(screenshots))
                data = screenshots[picked][0].read_bytes()
            else:
                st.sidebar.info("No synthetic screenshots are available.")
        image = load_image(data) if data is not None else None
    except Exception as exc:  # noqa: BLE001 - input errors should stay in the UI
        st.error(f"Could not open the image: {exc}")
        return

    method = st.sidebar.selectbox("Detector", list(METHODS), index=list(METHODS).index("combined"),
                                  format_func=lambda value: METHODS[value]["label"], key="image-method")
    language = st.sidebar.selectbox("Language", ["en", "fi"], key="image-language",
                                    format_func=lambda value: {"en": "English", "fi": "Finnish"}[value])
    crop_top = 0
    if image is not None and image.height > 1:
        crop_top = st.sidebar.slider("Crop from top (pixels)", 0, image.height - 1, 0,
                                     key="image-crop-" + hashlib.sha256(data).hexdigest()[:16])
    ocr_scale = st.sidebar.selectbox("OCR scale", [1, 2, 3], key="image-scale",
                                     format_func=lambda value: f"{value}×",
                                     help="Try 2× or 3× for small text. The exported image keeps its pixel size.")
    whole_lines = st.sidebar.checkbox("Mask whole OCR lines", key="image-whole-lines",
                                      help="Initially mask every word on a line containing a detection. "
                                           "This can also hide useful text; review the result.")
    run = st.sidebar.button("Run image", type="primary", disabled=image is None, key="run-image")
    st.caption("Paste cleaned text by default. Use a redacted image when its visual layout matters.")
    # Deciding what belongs in the image is a human step; OCR cannot judge a logo or a window title.
    st.info("Crop by hand before uploading: take a new screenshot of only the document area, without "
            "window titles, browser tabs, user names, avatars or logos. Do not crop an existing "
            "screenshot in an editor that may keep the cut pixels in the file; take a fresh one.")
    if image is None:
        st.info("Choose a screenshot, then select Run image.")
        return

    cropped = image.crop((0, crop_top, image.width, image.height))
    signature = hashlib.sha256(data + json.dumps(
        [crop_top, method, language, ocr_scale, whole_lines],
    ).encode("utf-8")).hexdigest()
    if run:
        # Clear the old output before starting, including when OCR or detection fails.
        st.session_state.pop("image_result", None)
        try:
            with st.spinner("Reading screenshot text and finding identifiers…"):
                result = analyze_image(cropped, detector_factory(method), language=language,
                                       ocr_scale=ocr_scale, whole_lines=whole_lines)
            result.update(signature=signature, revision=uuid.uuid4().hex)
            st.session_state["image_result"] = result
        except Exception as exc:  # noqa: BLE001 - never offer the original as a cleaned download
            st.error(f"Image processing failed: {exc}")
            st.info("OCR needs Tesseract on PATH and the selected language data. "
                    "Check the local setup and select Run image again.")
            return

    result = st.session_state.get("image_result")
    if result is None or result["signature"] != signature:
        if result is not None:
            st.info("The image or settings changed. Select Run image to update the masks.")
        st.image(cropped, caption="Input after crop — not yet redacted", width="stretch")
        return

    st.warning("Review all visible identifiers before sharing. OCR can miss text; "
               "logos, faces, signatures and QR codes are not detected.")
    if not result["words"]:
        st.warning("OCR found no words. This image has no automatic masks; use cleaned text "
                   "or crop out identifying content before sharing.")
    restore, mask_all = st.columns(2)
    if restore.button("Restore automatic masks"):
        result["selected"] = list(result["automatic"])
        result["revision"] = uuid.uuid4().hex
    if mask_all.button("Mask all words"):
        result["selected"] = list(range(len(result["words"])))
        result["revision"] = uuid.uuid4().hex

    review, preview = st.columns(2)
    with review:
        st.subheader("Review words")
        st.caption("Click an outlined word to add or remove its mask. Tab and Enter work too.")
        zoom = st.select_slider("Review zoom", options=[1, 2, 3, 4], value=2,
                                format_func=lambda value: f"{value}×", key="image-review-zoom")
        event = _word_editor(result, zoom)
        if (isinstance(event, dict) and event.get("revision") == result["revision"]
                and event.get("nonce") and event != result.get("last_event")):
            try:
                result["selected"] = validate_selection(event.get("selected"), len(result["words"]))
            except ValueError:
                st.error("That word selection is no longer valid. Run the image again.")
            else:
                result["last_event"] = event
                st.rerun()
    with preview:
        st.subheader("Redacted image")
        redacted = draw_boxes(result["image"], [result["words"][index].box for index in result["selected"]])
        st.image(redacted, width="stretch")
        st.caption(f"{len(result['selected'])} of {len(result['words'])} OCR words masked · "
                   f"{redacted.width} × {redacted.height} pixels")
        st.download_button("Download redacted PNG", png_bytes(redacted), file_name="anonymized.png",
                           mime="image/png", key="download-image")
