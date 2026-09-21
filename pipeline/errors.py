"""Errors raised by the document processing pipeline."""


class PipelineError(Exception):
    """Base class for errors that can be shown directly in the demo UI."""


class UnsupportedFormatError(PipelineError):
    """Raised when no extractor is available for the input file type."""


class ExtractionError(PipelineError):
    """Raised when text extraction or OCR cannot be completed."""


class AnonymizationError(PipelineError):
    """Raised when an anonymizer fails or returns an invalid value."""
