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


def windows(text: str, size: int = WINDOW, *, overlap: int = 0):
    """Yield bounded windows; overlap keeps identifiers intact at a cut."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Window size must be positive and overlap in [0, size)")
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            cut = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            if cut > start + size // 2:
                end = cut
        yield start, text[start:end]
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


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
        # A punctuation character can be one word token. Cap characters too,
        # so a dense piece cannot silently exceed the model's word limit.
        limit = min(WINDOW, self._model.config.max_len)
        spans = {}
        for offset, piece in windows(text, limit, overlap=min(150, limit // 2)):
            for item in self._model.predict_entities(piece, list(LABELS), threshold=self.threshold):
                key = (offset + item["start"], offset + item["end"], LABELS[item["label"]])
                score = float(item["score"])
                if key not in spans or score > spans[key].score:
                    spans[key] = SimpleNamespace(start=key[0], end=key[1], entity_type=key[2], score=score)
        spans = list(spans.values())
        # Imported here so the module loads without presidio (CI tests only the helpers).
        from detect.pattern_recognizers import (
            INVOICE_PATTERN,
            PERSONAL_ID_NO_CHECKSUM_PATTERN,
            PLATE_PATTERN,
        )
        for entity, pattern in (("PLATE", PLATE_PATTERN), ("INVOICE", INVOICE_PATTERN),
                                ("PERSONAL_ID", PERSONAL_ID_NO_CHECKSUM_PATTERN)):
            for match in re.finditer(pattern.regex, text):
                spans.append(SimpleNamespace(start=match.start(), end=match.end(),
                                             entity_type=entity, score=pattern.score))
        return spans
