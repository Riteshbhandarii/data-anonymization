"""A free local GLiNER detector with the same interface as PresidioDetector.

GLiNER is a zero-shot entity model that runs on CPU. Its labels are mapped to
Presidio entity names so TYPE_MAP and the redactor treat both families alike.
The project's three regex patterns (plate, invoice, identity code) are added
because GLiNER has no reason to know those synthetic formats.

Needs ``pip install gliner`` and a one-time model download from Hugging Face.
Only model weights are fetched; no document text ever leaves the machine.
"""

import os
import re
from types import SimpleNamespace

from detect.pattern_recognizers import (
    INVOICE_PATTERN,
    PERSONAL_ID_NO_CHECKSUM_PATTERN,
    PLATE_PATTERN,
)

MODEL = "urchade/gliner_multi_pii-v1"

# GLiNER prompt label -> Presidio entity name.
LABELS = {
    "person": "PERSON",
    "organization": "ORGANIZATION",
    "address": "LOCATION",
    "location": "LOCATION",
    "email": "EMAIL_ADDRESS",
    "phone number": "PHONE_NUMBER",
    "iban": "IBAN_CODE",
    "date": "DATE_TIME",
    "national id number": "PERSONAL_ID",
    "credit card number": "CREDIT_CARD",
}

# GLiNER truncates input near 384 tokens, so long text goes in windows.
WINDOW = 700


def windows(text: str, size: int = WINDOW):
    """Yield (offset, piece) covering the text, cut at whitespace where possible."""
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            cut = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            if cut > start + size // 2:
                end = cut
        yield start, text[start:end]
        start = end


def select_device(environ=None) -> str:
    """GLINER_DEVICE wins; otherwise cuda, then Apple mps, then cpu."""
    environ = os.environ if environ is None else environ
    if environ.get("GLINER_DEVICE"):
        return environ["GLINER_DEVICE"]
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class GlinerDetector:
    def __init__(self, threshold: float = 0.4, model: str = MODEL, device: str | None = None):
        self.threshold = threshold
        self.model_name = model
        self.device = device or select_device()
        self._model = None

    def detect(self, text: str, language: str = "en") -> list:
        if not isinstance(text, str):
            raise TypeError("The detector input must be a string")
        if self._model is None:
            from gliner import GLiNER
            self._model = GLiNER.from_pretrained(self.model_name).to(self.device)
        spans = []
        for offset, piece in windows(text):
            for item in self._model.predict_entities(piece, list(LABELS), threshold=self.threshold):
                spans.append(SimpleNamespace(
                    start=offset + item["start"], end=offset + item["end"],
                    entity_type=LABELS[item["label"]], score=float(item["score"])))
        for entity, pattern in (("PLATE", PLATE_PATTERN), ("INVOICE", INVOICE_PATTERN),
                                ("PERSONAL_ID", PERSONAL_ID_NO_CHECKSUM_PATTERN)):
            for match in re.finditer(pattern.regex, text):
                spans.append(SimpleNamespace(start=match.start(), end=match.end(),
                                             entity_type=entity, score=pattern.score))
        return spans
