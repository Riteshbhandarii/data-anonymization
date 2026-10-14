"""GLiNER2-PII as a local detector, same interface as PresidioDetector.

fastino/gliner2-privacy-filter-PII-multi (Apache 2.0) is GLiNER2, a
205M-parameter zero-shot extractor, fine-tuned on synthetic PII in English,
French, Spanish, German, Italian, Portuguese and Dutch. Finnish is not one of
them. Like GLiNER, it is told which labels to look for, and they are mapped to
Presidio entity names. The project's three patterns are added as for GLiNER.

Needs ``pip install gliner2`` and a one-time download of about 1.2 GB of
weights. The model runs locally; gliner2's separate API client is not used.
"""

from types import SimpleNamespace

from detect.gliner_detector import pattern_spans

MODEL = "fastino/gliner2-privacy-filter-PII-multi"

# GLiNER2 label -> Presidio entity name, the same set GLiNER is given.
# "organization", "location" and "date" are not among its 42 trained labels;
# it handles them zero-shot.
LABELS = {
    "person": "PERSON",
    "organization": "ORGANIZATION",
    "address": "LOCATION",
    "location": "LOCATION",
    "email": "EMAIL_ADDRESS",
    "phone_number": "PHONE_NUMBER",
    "iban": "IBAN_CODE",
    "date": "DATE_TIME",
    "national_id_number": "PERSONAL_ID",
    "card_number": "CREDIT_CARD",
}


class Gliner2Detector:
    def __init__(self, threshold: float = 0.5, model: str = MODEL, device: str = "cpu"):
        self.threshold = threshold
        self.model_name = model
        self.device = device
        self._model = None

    def detect(self, text: str, language: str = "en") -> list:
        if not isinstance(text, str):
            raise TypeError("The detector input must be a string")
        if self._model is None:
            from gliner2 import GLiNER2
            self._model = GLiNER2.from_pretrained(self.model_name).to(self.device)
        # The long variant cuts the text into overlapping word chunks itself.
        found = self._model.extract_entities_long(
            text, list(LABELS), threshold=self.threshold,
            include_confidence=True, include_spans=True)
        spans = [SimpleNamespace(start=item["start"], end=item["end"],
                                 entity_type=LABELS[label], score=float(item["confidence"]))
                 for label, items in found["entities"].items() for item in items]
        return spans + pattern_spans(text)
