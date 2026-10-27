# Clean-text release cookbook

**Paste the cleaned text, never upload the original file.**

1. Start the local UI with `streamlit run app/testbench.py`. Select a supported
   file, language, detector and replacement mode. For the study's local combined
   method, select **Combined**. Install its dependencies/models as in the README.
2. Leave **Keep document metadata** unchecked. Run the document. The complete
   `Document metadata` sections are omitted before detection and redaction.
   Shared template titles, subjects and keyword codes are removed even if they
   are not recognized as personal identifiers.
3. Inspect **Extract**, **Detect** and **Clean**. Check retained body text,
   headers/footers, notes, comments, hidden-sheet content, identifiers and
   identifying context against the source. Metadata omission does not remove
   company references in prose, identifying graphics or unsupported objects.
4. Verify task-critical dates, quantities and relationships in the saved output.
   Use **Download** to obtain the reviewed Markdown, or copy the minimal needed
   cleaned text. Follow the disclosure and confidentiality decisions in the
   [options map](options-map.md#part-c-decision-flow-before-pasting).
5. Paste only that reviewed text into an approved destination. The original
   DOCX/PPTX/XLSX/PDF is unchanged and may still hold author/company properties,
   paths, attachments and unsupported content. Cleaned original-format files
   require a separate agreed implementation; this export does not provide them.

For screenshots and snips, **paste reviewed cleaned text by default**. When the
visual layout itself is needed, select **Output → Redacted image** in the local
UI. Crop away identifying letterheads/window titles, run the detector, and click
the OCR word boxes to add or remove masks. Try 2× OCR for small text; whole-line
masking can cover the remaining words of a partly detected address, but also
removes useful text. Inspect the final preview and download the flattened PNG.
Share only that reviewed image, never the original. OCR can miss text, and this
mode does not detect logos, faces, signatures or QR codes. Multi-page PDFs stay
in the cleaned-text flow; the image editor exports one screenshot at a time.

For Python integration, `run_pipeline(..., anonymizer=..., include_metadata=False)`
is the default. Set `include_metadata=True` only when the properties themselves
are needed and reviewed. `extract_to_markdown()` intentionally retains all
extracted properties for local auditing; use `remove_document_metadata()` before
releasing its result directly.

`python -m eval.make_pack --runs RUNS --pack NEW_PACK --method combined` also
omits metadata from sanitized documents before truncating the prompts. Its raw
fictional ceiling controls remain raw. `--include-metadata` creates an explicit
comparison condition; preserve the old pack and answer files. Read every actual
real-public prompt before sending it. The R01/R02 ChatGPT linkage re-test must
be recorded from actual responses; local metadata-removal tests do not establish
that document linkage has become impossible.
