"""Named detector configurations shared by the benchmark runs and the UI.

Each method is one way of finding identifiers. Adding a method here makes it
available everywhere that lists METHODS, so results stay comparable. The
"good" and "weak" notes come from the dataset runs (docs/dataset-runs.md) and
should be updated when a rerun changes the picture.
"""

from functools import cache

from detect.adapter import PresidioDetector
from eval.bench import MODEL_SETS, build_analyzer

METHODS = {
    "basic": {
        "label": "Presidio", "family": "Rules + spaCy NER",
        "about": "Presidio's built-in recognizers with small spaCy models.",
        "good": "Email, IBAN, phone, dates.",
        "weak": "Addresses, companies, Finnish names, anything country specific."},
    "rules": {
        "label": "Presidio + patterns", "family": "Rules + spaCy NER",
        "about": "Adds plate, invoice and shape-only identity code patterns.",
        "good": "Everything basic finds, plus plates, invoices and identity codes.",
        "weak": "The patterns were written from our generator's formats, so they "
                "score well on the fake corpus by construction."},
    "rules-lg": {
        "label": "Presidio + large models", "family": "Rules + spaCy NER",
        "about": "Our rules with large spaCy models (needs the lg downloads).",
        "good": "Finnish person names, much better than the small model.",
        "weak": "Addresses and companies barely move."},
    "gliner": {
        "label": "GLiNER + patterns", "family": "Zero-shot transformer",
        "about": "urchade/gliner_multi_pii-v1, told which entity names to look for. "
                 "Plus our three patterns.",
        "good": "Names, companies, addresses, in English and Finnish.",
        "weak": "IBAN, email and dates; slower (seconds per document)."},
    "combined": {
        "label": "Combined", "family": "Rules + transformer",
        "about": "GLiNER, plus Presidio with our rules minus its spaCy names, companies "
                 "and places.",
        "good": "GLiNER's names and addresses with Presidio's IBAN, email, dates and "
                "ID numbers.",
        "weak": "As slow as GLiNER, and more detections to review than either part."},
}


def _presidio(models: str, custom: bool) -> PresidioDetector:
    return PresidioDetector(build_analyzer(MODEL_SETS[models], custom))


def _gliner():
    # Imported here so this module loads without torch or gliner installed.
    from detect.gliner_detector import GlinerDetector
    return GlinerDetector()


def _combined():
    from detect.combined import CombinedDetector
    return CombinedDetector(get_detector("rules"), get_detector("gliner"))


BUILDERS = {
    "basic": lambda: _presidio("sm", False),
    "rules": lambda: _presidio("sm", True),
    "rules-lg": lambda: _presidio("lg", True),
    "gliner": _gliner,
    "combined": _combined,
}


@cache
def get_detector(method: str):
    """One detector per method, built once, since loading models is slow."""
    if method not in METHODS:
        raise KeyError(f"Unknown method {method!r}; choose from {sorted(METHODS)}")
    return BUILDERS[method]()
