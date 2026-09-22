"""Public entry points for the local anonymization pipeline."""

from .core import PipelineResult, run_pipeline
from .errors import AnonymizationError, ExtractionError, PipelineError, UnsupportedFormatError
from .extractors import SUPPORTED_EXTENSIONS, detect_format, extract_to_markdown
from .normalization import normalize_markdown

__all__ = [
    "AnonymizationError",
    "ExtractionError",
    "PipelineError",
    "PipelineResult",
    "SUPPORTED_EXTENSIONS",
    "UnsupportedFormatError",
    "detect_format",
    "extract_to_markdown",
    "normalize_markdown",
    "run_pipeline",
]
