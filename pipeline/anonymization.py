"""Anonymization adapters used by the pipeline and the demo application."""

import re
from collections.abc import Callable

from .errors import AnonymizationError

Anonymizer = Callable[[str], str]


_BASELINE_PATTERNS = (
    (
        re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])"),
        "[EMAIL_REDACTED]",
    ),
    (
        re.compile(
            r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)"
            r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b"
        ),
        "[IP_ADDRESS_REDACTED]",
    ),
    (
        re.compile(r"\b\d{6}[+\-ABCDEFYXWVU]\d{3}[0-9A-FHJ-NPR-Y]\b", re.IGNORECASE),
        "[NATIONAL_ID_REDACTED]",
    ),
    (
        re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b", re.IGNORECASE),
        "[IBAN_REDACTED]",
    ),
)


def baseline_anonymize(markdown: str) -> str:
    """Redact a small set of structured identifiers for local demonstrations.

    This baseline intentionally does not attempt to identify names, addresses,
    organizations, or other context-dependent entities. Replace it with the
    team's anonymization function before using the pipeline with real data.
    """
    result = markdown
    for pattern, replacement in _BASELINE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def run_anonymization_passes(
    markdown: str,
    anonymizer: Anonymizer,
    passes: int = 2,
) -> str:
    """Run an anonymizer repeatedly and validate its return value."""
    if passes < 1:
        raise ValueError("passes must be at least 1")

    result = markdown
    for pass_number in range(1, passes + 1):
        try:
            result = anonymizer(result)
        except Exception as exc:
            raise AnonymizationError(
                f"Anonymization pass {pass_number} failed: {exc}"
            ) from exc

        if not isinstance(result, str):
            raise AnonymizationError(
                f"Anonymization pass {pass_number} returned "
                f"{type(result).__name__}; expected str."
            )

    return result
