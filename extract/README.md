# extract

Extract text from each supported source type and return a Markdown string. Files with a usable text layer are parsed directly; standalone images and scanned PDF pages use OCR.

The current implementation is in `pipeline/extractors.py`. See `docs/pipeline.md` for the supported formats and the extractor integration contract.
