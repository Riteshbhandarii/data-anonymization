# Local Markdown pipeline

## Scope

The pipeline prepares files locally before a person sends their content to any external service. It does not call an LLM, upload a file, or reconstruct the original document format.

The current output is one UTF-8 Markdown file:

```text
input file
    -> detect format
    -> extract text or run OCR
    -> normalize as Markdown
    -> anonymization pass 1
    -> anonymization pass 2
    -> outputs/<input-name>_anonymized.md
```

Ordinary embedded images are ignored. Standalone images and PDF pages without a text layer are sent to OCR so that their visible text can be included.

## Running the pipeline

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

OCR also requires the Tesseract executable and the required language data to be installed on the computer. The default language is `eng`. For Finnish OCR, install Finnish language data and pass `fin`.

Run the command-line interface:

```bash
python -m pipeline path/to/input.pdf
python -m pipeline path/to/input.pdf --ocr-language fin
```

Run the local demo:

```bash
streamlit run app.py
```

Generated files are written to `outputs/`. The directory is ignored by Git because an anonymizer can miss sensitive data.

## Supported input

| Input | Extraction behavior |
|---|---|
| `.md`, `.txt` | Read as UTF-8 text |
| `.csv` | Convert rows to a Markdown table |
| `.docx` | Extract paragraphs, headings, lists, and tables |
| `.xlsx` | Convert each worksheet to a Markdown section and table |
| `.pptx` | Convert each slide and its speaker notes to a Markdown section |
| `.pdf` | Extract each page's text layer; use OCR for pages with no text |
| `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp` | Use OCR |

## Connecting the team's anonymizer

The integration contract is intentionally one function:

```python
def anonymize_markdown(markdown: str) -> str:
    """Return Markdown with sensitive information replaced."""
    ...
```

Pass the function to the pipeline:

```python
from pipeline import run_pipeline
from team_anonymizer import anonymize_markdown

result = run_pipeline(
    "example.docx",
    anonymizer=anonymize_markdown,
)

print(result.output_path)
```

`run_pipeline` calls the supplied function twice. The second call receives the output of the first call. The function must always return a string and should leave Markdown syntax intact where possible.

The built-in `baseline_anonymize` function exists only to keep the demo runnable while the team's detector is under development. It redacts email addresses, IPv4 addresses, Finnish personal identity codes, and IBAN-like values. It does not reliably detect names, organizations, addresses, or contextual identifiers and must not be treated as production anonymization.

To use the team's implementation in Streamlit, change the import and pass the function in `app.py`:

```python
from team_anonymizer import anonymize_markdown

result = run_pipeline(
    input_path,
    anonymizer=anonymize_markdown,
    ocr_language=ocr_language,
    progress=show_progress,
)
```

## Connecting another extractor

Every extractor returns a Markdown string. Add a function to `pipeline/extractors.py`:

```python
def _extract_new_format(path: Path) -> str:
    return "## Extracted content\n\n..."
```

Then add the extension to `SUPPORTED_EXTENSIONS` and dispatch it from `extract_to_markdown`. Keep format-specific dependencies inside the extractor function so other file types remain usable when an optional dependency is unavailable.

## Python result

`run_pipeline` returns a `PipelineResult`:

```python
result.input_path   # original local path
result.output_path  # saved Markdown path
result.markdown     # anonymized Markdown string
```

The Streamlit application uses the same function as the command-line interface. UI code should not contain extraction or anonymization logic.

## Current limitations

- Original document formatting is not preserved.
- Embedded image content is ignored unless the whole input is an image or a PDF page has no text layer.
- A PDF page containing both selectable text and an image is not OCRed.
- OCR quality depends on the scan and installed Tesseract language data.
- Running the same anonymizer twice reduces some residual misses but is not a safety guarantee.
- Output must be reviewed and tested before it is sent outside the trusted environment.
