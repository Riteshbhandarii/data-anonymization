"""Errors raised by the document processing pipeline."""


class PipelineError(Exception):
    """Base class for extraction and anonymization integration errors."""


class UnsupportedFormatError(PipelineError):
    """Raised when no extractor is available for the input file type."""


class ExtractionError(PipelineError):
    """Raised when text extraction or OCR cannot be completed."""


class AnonymizationError(PipelineError):
    """Raised when an anonymizer fails or returns an invalid value."""
