"""Named detector configurations shared by the benchmark runs and the UI.

Each method is one way of finding identifiers. Adding a method here makes it
available everywhere that lists METHODS, so results stay comparable.
"""

from functools import cache

from detect.adapter import PresidioDetector
from eval.bench import MODEL_SETS, build_analyzer

METHODS = {
    "basic": {"label": "Presidio basic", "models": "sm", "custom": False,
              "about": "Presidio's built-in recognizers with small spaCy models."},
    "rules": {"label": "+ our rules", "models": "sm", "custom": True,
              "about": "Adds plate, invoice and shape-only identity code patterns."},
    "rules-lg": {"label": "+ large models", "models": "lg", "custom": True,
                 "about": "Our rules with large spaCy models (needs the lg downloads)."},
}


@cache
def get_detector(method: str) -> PresidioDetector:
    """One analyzer per method, built once, since loading spaCy models is slow."""
    if method not in METHODS:
        raise KeyError(f"Unknown method {method!r}; choose from {sorted(METHODS)}")
    config = METHODS[method]
    analyzer = build_analyzer(MODEL_SETS[config["models"]], config["custom"])
    return PresidioDetector(analyzer)
