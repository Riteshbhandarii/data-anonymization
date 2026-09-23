# extract

Extract text from each supported source type and return a Markdown string. Read available text directly, use OCR for standalone images and scanned PDF pages, and supplement text from mixed PDF pages with OCR of their image regions.

The existing readers are in `pipeline/extractors.py`. A custom reader can be passed to `run_pipeline()` through `extractor=`. It receives a `pathlib.Path` and returns a Markdown string; the pipeline then normalizes that text and passes it to the anonymization module.

The built-in document readers include core metadata, Word headers and footers, slide speaker notes, and hidden worksheets in the returned Markdown. XLSX formula cells use saved computed values; a missing or erroneous formula cache raises an extraction error with the sheet and cell to recalculate.

See [the pipeline integration guide](../docs/pipeline.md#connect-another-extraction-module) for an example, format dispatch instructions, and the OCR replacement point.

See [extraction validation](../docs/extraction-validation.md) for the labelled-corpus checks to run when changing a reader.
