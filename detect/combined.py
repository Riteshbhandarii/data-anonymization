"""GLiNER for names, companies and places, plus Presidio for everything else.

The dataset runs show the two families fail in opposite places: Presidio is
near perfect on IBAN, email and date but finds no addresses and few Finnish
names, while GLiNER finds names and addresses but misses most IBANs. This
detector routes every GLiNER span and every Presidio span except Presidio's
spaCy names, companies and places, the part GLiNER does better.

It is deliberately not the union. Dropping a type from one side means the
combination can still lose recall to either part, so its score is a real
comparison. Presidio's dates also come from spaCy and are kept, because they
beat GLiNER's on the fake corpus and on TAB.

After routing, explicit quantity/title contexts filter narrow false positives,
and Finnish business/VAT shapes are added. See docs/role1-fixes.md for the
paired regression measurements and remaining company-name limitation.
"""

# Presidio entity types that come from spaCy's named entity model and that
# GLiNER covers better. Presidio's NRP (nationality, religion, politics) stays:
# GLiNER has no such label, and without it TAB DEM recall (nationalities and
# occupations) falls from 44% to 26%.
from detect.context_rules import business_spans, filter_context_spans

MODEL_TYPES = {"PERSON", "ORGANIZATION", "LOCATION"}


def route(presidio_spans, model_spans) -> list:
    """Every model span, and the Presidio spans that are not of MODEL_TYPES.

    Overlaps between the two are left in place; redact.resolve_spans merges
    them into one placeholder, and the scorer only asks whether one correctly
    typed span covers the value.
    """
    return [s for s in presidio_spans if s.entity_type not in MODEL_TYPES] + list(model_spans)


class CombinedDetector:
    def __init__(self, presidio, model, *, organization_terms=()):
        self.presidio, self.model = presidio, model
        if isinstance(organization_terms, str):
            raise TypeError("organization_terms must be a sequence of company names")
        self.organization_terms = tuple(organization_terms)

    @property
    def device(self):
        return getattr(self.model, "device", "cpu")

    def detect(self, text: str, language: str = "en") -> list:
        spans = route(self.presidio.detect(text, language), self.model.detect(text, language))
        return filter_context_spans(text, spans) + business_spans(text, self.organization_terms)


def route_keep_org(presidio_spans, model_spans) -> list:
    """Keep Presidio organizations alongside all GLiNER spans."""
    excluded = {"PERSON", "LOCATION"}

    return [
        span for span in presidio_spans
        if span.entity_type not in excluded
    ] + list(model_spans)


class CombinedKeepOrgDetector(CombinedDetector):
    """Combine GLiNER with Presidio while retaining organizations."""

    def detect(self, text: str, language: str = "en") -> list:
        spans = route_keep_org(
            self.presidio.detect(text, language),
            self.model.detect(text, language),
        )
        return (
            filter_context_spans(text, spans)
            + business_spans(text, self.organization_terms)
        )

def join_organization_spans(text: str, spans: list) -> list:
    """Join organization names separated by commas and 'and'."""
    import re
    from types import SimpleNamespace

    organizations = sorted(
        (span for span in spans if span.entity_type == "ORGANIZATION"),
        key=lambda span: (span.start, span.end),
    )

    additions = []
    index = 0

    while index < len(organizations):
        group = [organizations[index]]
        next_index = index + 1

        while next_index < len(organizations):
            previous = group[-1]
            current = organizations[next_index]
            separator = text[previous.end:current.start]

            if not re.fullmatch(r"\s*,\s*|\s+and\s+|\s*,\s*and\s+", separator):
                break

            group.append(current)
            next_index += 1

        # Require a comma-separated company-name structure.
        if len(group) >= 3:
            fragment = text[group[0].start:group[-1].end]

            if "," in fragment and re.search(r"\band\b", fragment):
                additions.append(
                    SimpleNamespace(
                        start=group[0].start,
                        end=group[-1].end,
                        entity_type="ORGANIZATION",
                        score=max(span.score for span in group),
                    )
                )

        index = max(next_index, index + 1)

    return spans + additions


class CombinedKeepOrgChunkedDetector(CombinedKeepOrgDetector):
    """Keep-org detector with chunk and complete-line GLiNER passes."""

    def detect(self, text: str, language: str = "en") -> list:
        from detect.gliner_detector import windows
        from types import SimpleNamespace

        spans = super().detect(text, language)
        extra = []

        # Detect entities in overlapping text chunks.
        for offset, chunk in windows(text, size=100, overlap=30):
            for span in self.model.detect(chunk, language):
                extra.append(
                    SimpleNamespace(
                        start=offset + span.start,
                        end=offset + span.end,
                        entity_type=span.entity_type,
                        score=span.score,
                    )
                )

        # Detect entities using complete lines to preserve context.
        offset = 0

        for line in text.splitlines(keepends=True):
            line_text = line.rstrip("\r\n")

            if line_text.strip():
                for span in self.model.detect(line_text, language):
                    extra.append(
                        SimpleNamespace(
                            start=offset + span.start,
                            end=offset + span.end,
                            entity_type=span.entity_type,
                            score=span.score,
                        )
                    )

            offset += len(line)

        # Preserve the team's context filtering for extra detections.
        extra = filter_context_spans(text, extra)

        # Remove exact duplicates, keeping the highest score.
        unique = {}

        for span in spans + extra:
            key = (span.start, span.end, span.entity_type)

            if key not in unique or span.score > unique[key].score:
                unique[key] = span

        return join_organization_spans(text, list(unique.values()))
