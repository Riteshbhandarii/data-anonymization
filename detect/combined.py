"""GLiNER for names, companies and places, plus Presidio for everything else.

The dataset runs show the two families fail in opposite places: Presidio is
near perfect on IBAN, email and date but finds no addresses and few Finnish
names, while GLiNER finds names and addresses but misses most IBANs. This
detector keeps every GLiNER span and every Presidio span except Presidio's
spaCy names, companies and places, the part GLiNER does better.

It is deliberately not the union. Dropping a type from one side means the
combination can still lose recall to either part, so its score is a real
comparison. Presidio's dates also come from spaCy and are kept, because they
beat GLiNER's on the fake corpus and on TAB.
"""

# Presidio entity types that come from spaCy's named entity model and that
# GLiNER covers better. Presidio's NRP (nationality, religion, politics) stays:
# GLiNER has no such label, and without it TAB DEM recall (nationalities and
# occupations) falls from 44% to 26%.
MODEL_TYPES = {"PERSON", "ORGANIZATION", "LOCATION"}


def route(presidio_spans, model_spans) -> list:
    """Every model span, and the Presidio spans that are not of MODEL_TYPES.

    Overlaps between the two are left in place; redact.resolve_spans merges
    them into one placeholder, and the scorer only asks whether one correctly
    typed span covers the value.
    """
    return [s for s in presidio_spans if s.entity_type not in MODEL_TYPES] + list(model_spans)


class CombinedDetector:
    def __init__(self, presidio, model):
        self.presidio, self.model = presidio, model

    @property
    def device(self):
        return getattr(self.model, "device", "cpu")

    def detect(self, text: str, language: str = "en") -> list:
        return route(self.presidio.detect(text, language), self.model.detect(text, language))
