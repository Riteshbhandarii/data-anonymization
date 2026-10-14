"""Named detector configurations shared by the benchmark runs and the UI.

Each method is one way of finding identifiers. Adding a method here makes it
available everywhere that lists METHODS, so results stay comparable.
"""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from detect.adapter import PresidioDetector
from eval.bench import MODEL_SETS, build_analyzer

if TYPE_CHECKING:
    from detect.gliner_detector import GlinerDetector

METHODS = {
    "basic": {"label": "Presidio", "models": "sm", "custom": False,
              "about": "Presidio's built-in recognizers with small spaCy models."},
    "rules": {"label": "Presidio + patterns", "models": "sm", "custom": True,
              "about": "Adds plate, invoice and shape-only identity code patterns."},
    "rules-lg": {"label": "Presidio + large models", "models": "lg", "custom": True,
                 "about": "Our rules with large spaCy models (needs the lg downloads)."},
    "gliner": {"label": "GLiNER + patterns",
               "about": "Local GLiNER with plate, invoice and identity code patterns."},
}


@cache
def get_detector(method: str) -> PresidioDetector | GlinerDetector:
    """Reuse one detector per method and import GLiNER only when selected."""
    if method not in METHODS:
        raise KeyError(f"Unknown method {method!r}; choose from {sorted(METHODS)}")
    if method == "gliner":
        from detect.gliner_detector import GlinerDetector
        return GlinerDetector()
    config = METHODS[method]
    analyzer = build_analyzer(MODEL_SETS[config["models"]], config["custom"])
    return PresidioDetector(analyzer)
