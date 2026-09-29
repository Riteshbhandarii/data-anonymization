"""Apply validated detector spans using Presidio's replacement operators."""

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from threading import Lock


@dataclass(frozen=True)
class Span:
    """A half-open Python character interval in the original input string."""

    start: int
    end: int
    entity_type: str
    score: float


@dataclass(repr=False)
class AliasMap:
    """An explicit in-memory pseudonym scope; never persisted automatically.

    Keys use exact text and type, so distinct spellings are not assumed to be
    the same person. Reuse this object across calls only when identifiers need
    to remain linkable across those documents. The map contains original PII.
    """

    _values: dict[tuple[str, str], str] = field(default_factory=dict, init=False)
    _counts: dict[str, int] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def token(self, entity_type: str, value: str) -> str:
        """Allocate an alias once, in order of first occurrence."""
        with self._lock:
            key = (entity_type, value)
            if key not in self._values:
                number = self._counts.get(entity_type, 0) + 1
                self._counts[entity_type] = number
                self._values[key] = f"[{entity_type}_{number}]"
            return self._values[key]

    def clear(self) -> None:
        """Release all mappings at the end of the chosen processing scope."""
        with self._lock:
            self._values.clear()
            self._counts.clear()


def validate_spans(text: str, spans: Iterable) -> list[Span]:
    """Copy and validate Presidio-style objects or dictionaries before editing.

    Offsets are Python character positions, not UTF-8 bytes. A malformed span
    raises instead of quietly leaving a purportedly detected value unchanged.
    """
    if not isinstance(text, str):
        raise TypeError("Redaction input must be a string")
    validated = []
    for item in spans:
        try:
            if isinstance(item, Mapping):
                start, end, kind, score = (item[key] for key in ("start", "end", "entity_type", "score"))
            else:
                start, end, kind, score = item.start, item.end, item.entity_type, item.score
        except (KeyError, AttributeError) as exc:
            raise ValueError("Every span needs start, end, entity_type and score") from exc
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("Span offsets must satisfy 0 <= start < end <= len(text)")
        if not isinstance(kind, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", kind):
            raise ValueError("entity_type must contain uppercase letters, digits or underscores")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Span score must be a finite number between 0 and 1")
        validated.append(Span(start, end, kind, float(score)))
    return sorted(set(validated), key=lambda span: (span.start, span.end, span.entity_type, -span.score))


def resolve_spans(text: str, spans: Iterable) -> list[Span]:
    """Cover the union of overlapping spans with deterministic placeholder types.

    Connected overlaps form one interval. Its type comes from the highest
    score, then longest interval, then alphabetic type and earliest start.
    Adjacent intervals remain separate. This never discards a detected tail.
    """
    groups: list[list[Span]] = []
    right = -1
    for span in validate_spans(text, spans):
        if not groups or span.start >= right:
            groups.append([span])
            right = span.end
        else:
            groups[-1].append(span)
            right = max(right, span.end)
    resolved = []
    for group in groups:
        winner = min(group, key=lambda span: (-span.score, -(span.end - span.start), span.entity_type, span.start))
        resolved.append(Span(min(item.start for item in group), max(item.end for item in group),
                             winner.entity_type, winner.score))
    return resolved


def redact(text: str, spans: Iterable, *, mode: str = "replace", aliases: AliasMap | None = None) -> str:
    """Replace detector spans without re-normalizing the input or its offsets.

    ``replace`` uses ``[PERSON]`` style tokens. ``pseudonymize`` uses consistent
    numbered tokens such as ``[PERSON_1]``. An omitted alias map gives each call
    its own scope. Text outside the resolved intervals is left unchanged.
    """
    if mode not in ("replace", "pseudonymize"):
        raise ValueError("mode must be 'replace' or 'pseudonymize'")
    resolved = resolve_spans(text, spans)
    if not resolved:
        return text

    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig, RecognizerResult

    alias_map = aliases if aliases is not None else AliasMap()
    operators = {}
    results = []
    for index, span in enumerate(resolved):
        replacement = f"[{span.entity_type}]" if mode == "replace" else alias_map.token(
            span.entity_type, text[span.start:span.end],
        )
        # Unique internal types prevent Presidio from merging adjacent entities
        # of the same type; each previously resolved interval has one operator.
        operator_key = f"SPAN_{index}"
        operators[operator_key] = OperatorConfig("replace", {"new_value": replacement})
        results.append(RecognizerResult(operator_key, span.start, span.end, span.score))
    return AnonymizerEngine().anonymize(text, results, operators=operators).text


class PipelineAnonymizer:
    """Connect ``detector.detect`` and ``redact`` to ``run_pipeline``.

    One instance is intended for sequential calls. ``last_spans`` exposes the
    original detections for evaluation, not the expanded overlap intervals.
    The detector always receives the same normalized Markdown as the redactor.
    """

    def __init__(self, detector, *, language: str = "en", mode: str = "replace", aliases: AliasMap | None = None):
        if mode not in ("replace", "pseudonymize"):
            raise ValueError("mode must be 'replace' or 'pseudonymize'")
        self.detector = detector
        self.language = language
        self.mode = mode
        self.aliases = aliases
        self.last_spans: tuple[Span, ...] = ()

    def __call__(self, markdown: str) -> str:
        self.last_spans = ()
        spans = validate_spans(markdown, self.detector.detect(markdown, language=self.language))
        self.last_spans = tuple(spans)
        return redact(markdown, spans, mode=self.mode, aliases=self.aliases)
