"""Expose the team's existing Presidio configuration as a reusable detector."""

from eval.bench import THRESHOLD, build_analyzer


class PresidioDetector:
    """Return character spans on exactly the string supplied by the caller.

    Supply an existing analyzer to reuse its models across documents. The
    default analyzer is constructed lazily from ``eval.bench.build_analyzer``;
    this keeps production and detector-only evaluation on the same settings.
    """

    def __init__(self, analyzer=None, *, score_threshold: float = THRESHOLD):
        if not 0 <= score_threshold <= 1:
            raise ValueError("score_threshold must be between 0 and 1")
        self.analyzer = analyzer
        self.score_threshold = score_threshold

    def detect(self, text: str, language: str = "en") -> list:
        if not isinstance(text, str):
            raise TypeError("The detector input must be a string")
        if self.analyzer is None:
            self.analyzer = build_analyzer()
        return list(self.analyzer.analyze(
            text=text, language=language, score_threshold=self.score_threshold,
        ))
