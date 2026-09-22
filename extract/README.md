# extract

Extract text from each supported source type and return a Markdown string. Files with a usable text layer are parsed directly; standalone images and scanned PDF pages use OCR.

The existing readers are in `pipeline/extractors.py`. A custom reader can be passed to `run_pipeline()` through `extractor=`. It receives a `pathlib.Path` and returns a Markdown string; the pipeline then normalizes that text and passes it to the anonymization module.

See [the pipeline integration guide](../docs/pipeline.md#connect-another-extraction-module) for an example, format dispatch instructions, and the OCR replacement point.
