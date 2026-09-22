# Pipeline integration guide

## Processing flow

`run_pipeline()` coordinates one file from input to Markdown output:

```text
Input file path
    |
    v
Detect extension and select a reader
    |
    v
Extract text / OCR and build Markdown
    |
    v
Normalize Markdown whitespace
    |
    v
Call the anonymization module
    |
    v
Receive the returned Markdown string
    |
    v
Save outputs/<input-stem>_anonymized.md
    |
    v
Return PipelineResult to the caller
```

The extraction and anonymization modules exchange strings with the pipeline. They do not need to create output files. The pipeline handles the final filename, directory creation, and saving.

## Files and responsibilities

| File | Responsibility |
|---|---|
| `pipeline/core.py` | Implements `run_pipeline()`, calls the supplied modules, and saves their output |
| `pipeline/extractors.py` | Selects readers by extension, extracts content, calls OCR, and builds Markdown sections and tables |
| `pipeline/normalization.py` | Normalizes line endings, trailing whitespace, and repeated blank lines before anonymization |
| `pipeline/errors.py` | Defines exceptions for extraction and anonymization failures |
| `pipeline/__init__.py` | Exports the public functions and result/error types |

## Setup

Use Python 3.10 or newer and run the calling script from the repository root so Python can import `pipeline` and your modules.

The existing document readers use these packages:

```bash
python -m pip install python-docx openpyxl python-pptx pymupdf pillow pytesseract
```

They are also listed in the shared `requirements.txt`. Text, Markdown, and CSV reading use the Python standard library. Format-specific packages are imported only when that reader runs.

The existing OCR reader requires the Tesseract executable on `PATH` and installed language data. Its default language is `eng`; set `ocr_language="fin"` when using Finnish language data.

## Connect an anonymization module

The function supplied through `anonymizer` must accept one Markdown string and return one Markdown string:

```python
def anonymize_markdown(markdown: str) -> str:
    ...  # Implement detection and replacement logic here.
```

The input is the complete document, including Markdown headings and table syntax. It is text, not a file path. The return value is the complete processed document, not a list of detections, a dictionary, a saved filename, or `None`.

For example, if your function is defined in `redact/anonymizer.py`, the calling code is:

```python
from pipeline import run_pipeline
from redact.anonymizer import anonymize_markdown

result = run_pipeline(
    "documents/report.docx",
    anonymizer=anonymize_markdown,
)

print(result.output_path)
```

`redact/anonymizer.py` is an example location for the module you provide. Replace the import with your actual module path. Pass the function itself (`anonymizer=anonymize_markdown`), without calling it in the argument.

The pipeline calls the anonymization module after extraction and normalization. It then saves the returned string without further content processing. An anonymizer is required; the pipeline contains no built-in replacement algorithm.

If your module uses additional arguments or returns a different structure, provide a small wrapper. For example, a module that returns `{"markdown": ...}` can be connected as follows:

```python
from pipeline import run_pipeline
from redact.anonymizer import process_document

def anonymize_for_pipeline(markdown: str) -> str:
    response = process_document(markdown)
    return response["markdown"]

result = run_pipeline(
    "documents/report.docx",
    anonymizer=anonymize_for_pipeline,
)
```

Initialize any model or configuration required by your module before calling `run_pipeline()`. The wrapper can use those already-initialized objects.

## Function arguments

```python
def run_pipeline(
    input_path,
    output_dir=DEFAULT_OUTPUT_DIR,
    *,
    anonymizer,
    extractor=None,
    ocr_language="eng",
    progress=None,
) -> PipelineResult:
    ...
```

| Argument | Expected value | Behavior |
|---|---|---|
| `input_path` | `str` or `pathlib.Path` | Path to one existing input file |
| `anonymizer` | Required callable: `str -> str` | Receives normalized Markdown and returns processed Markdown |
| `extractor` | Optional callable: `Path -> str` | Replaces built-in format selection and extraction; receives the input path and returns Markdown |
| `output_dir` | `str` or `pathlib.Path` | Defaults to `outputs/` in the repository root |
| `ocr_language` | `str` | Tesseract language code for the built-in reader; defaults to `eng` |
| `progress` | Optional callable: `str -> None` | Receives a short message when each processing stage starts; use `print` for console output |

## Existing readers

Extension matching is case-insensitive. All readers return Markdown strings through `extract_to_markdown()`.

| Extension | Current conversion |
|---|---|
| `.txt`, `.md` | Read UTF-8 text, accepting an optional UTF-8 byte-order mark |
| `.csv` | Read comma-separated rows and build a Markdown table; the first row becomes the header |
| `.docx` | Read body paragraphs, headings, lists, and tables in document order |
| `.xlsx` | Read worksheets, including hidden worksheets; build one section and table per sheet, including formula text |
| `.pptx` | Build a section per slide with titles, text, tables, and speaker notes |
| `.pdf` | Build a section per page; extract its text layer, or call OCR when the page has no text |
| `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp` | Read the image through OCR and return a text section |

Extraction can also be called independently:

```python
from pipeline import extract_to_markdown, normalize_markdown

markdown = extract_to_markdown("documents/report.pdf", ocr_language="eng")
markdown = normalize_markdown(markdown)
```

## Connect another extraction module

To use a custom reader without editing the pipeline, pass it as `extractor`. It receives a `pathlib.Path` and must return a Markdown string:

```python
from pathlib import Path
from pipeline import run_pipeline
from extract.reader import read_as_markdown
from redact.anonymizer import anonymize_markdown

def extract_for_pipeline(path: Path) -> str:
    return read_as_markdown(str(path))

result = run_pipeline(
    "documents/report.docx",
    extractor=extract_for_pipeline,
    anonymizer=anonymize_markdown,
)
```

The import paths above are examples; replace them with your actual module paths. This custom extractor takes over format routing, reading, and any OCR it needs. It can support extensions outside `SUPPORTED_EXTENSIONS`. The pipeline still normalizes its returned Markdown and passes it to the anonymizer. Configure OCR languages inside your custom reader or wrapper; `ocr_language` is only forwarded to the built-in reader.

To add a format to the existing dispatcher instead:

1. Implement a reader in `pipeline/extractors.py` that takes a `Path` and returns Markdown.
2. Include the lowercase extension in the set used to build `SUPPORTED_EXTENSIONS`.
3. Add a corresponding branch in `extract_to_markdown()` that calls the reader.
4. Import additional format-specific dependencies inside the reader and list them in `requirements.txt`.

The existing OCR calls share `_run_tesseract(image, ocr_language)`. An OCR developer can replace its implementation while keeping those arguments and returning recognized text as `str`. The image argument is a Pillow image. PDF rendering and Markdown section creation are handled by the surrounding readers.

## Output contract

`run_pipeline()` returns a `PipelineResult` after saving:

| Field | Type | Meaning |
|---|---|---|
| `input_path` | `pathlib.Path` | The input path supplied by the caller |
| `output_path` | `pathlib.Path` | Path to the saved Markdown file |
| `markdown` | `str` | The exact text returned by the anonymization module |

For `documents/report.docx`, the default output is `<repository>/outputs/report_anonymized.md`. The directory is created if needed. The output uses UTF-8 encoding. Repeating the same input stem in the same output directory overwrites that output file; for example, `report.docx` and `report.pdf` both produce `report_anonymized.md`. The `outputs/` directory is ignored by Git.

The caller can use `result.markdown` directly or use `result.output_path` to read the saved file. To select an output directory, pass `output_dir="results"`; relative directories are resolved against the calling process's working directory.

## Error handling

| Exception | When it is raised |
|---|---|
| `UnsupportedFormatError` | The built-in reader does not support the extension |
| `ExtractionError` | The input is missing, reading/OCR fails, or an extractor returns a non-string value |
| `AnonymizationError` | The supplied anonymizer raises an exception or returns a non-string value |

These exceptions inherit from `PipelineError`. The caller can catch `PipelineError` to report processing failures. Original module exceptions are retained as the exception cause. Filesystem errors when creating the output directory or writing the result propagate as `OSError`.

Saving happens only after the anonymizer successfully returns a string. An extraction or anonymization failure leaves any existing output file unchanged.
