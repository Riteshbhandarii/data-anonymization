"""Public entry points for the local anonymization pipeline."""

from .anonymization import baseline_anonymize
from .core import PipelineResult, run_pipeline
from .errors import ExtractionError, PipelineError, UnsupportedFormatError
from .extractors import SUPPORTED_EXTENSIONS, extract_to_markdown

__all__ = [
    "ExtractionError",
    "PipelineError",
    "PipelineResult",
    "SUPPORTED_EXTENSIONS",
    "UnsupportedFormatError",
    "baseline_anonymize",
    "extract_to_markdown",
    "run_pipeline",
]
