"""Span-based replacement and pseudonymization for extracted Markdown."""

from .core import (
    AliasMap,
    PipelineAnonymizer,
    Span,
    redact,
    resolve_spans,
    validate_spans,
)

__all__ = ["AliasMap", "PipelineAnonymizer", "Span", "redact", "resolve_spans", "validate_spans"]
