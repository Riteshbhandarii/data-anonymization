"""Conservative corrections for quantity/title false positives in combined.

Only spans wholly inside an explicit non-identifier expression are removed.
Mixed spans containing a calendar date or a person's name are retained.
Business identifiers use documented Finnish shapes, not a registry lookup or
checksum gate: a mistyped identifier can still disclose the source company.
"""

import re
from types import SimpleNamespace

_NUMBER = r"\d+(?:[.,]\d+)?"
_AMOUNT = (rf"(?:{_NUMBER}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
           r"yksi|yhden|kaksi|kahden|kolme|kolmen|neljä|neljän|viisi|viiden|kuusi|kuuden|"
           r"seitsemän|kahdeksan|yhdeksän|kymmenen)")
_UNIT = (r"hours?|months?|years?|days?|weeks?|minutes?|seconds?|"
         r"tuntia|tunti|tunnit|tunnin|kuukautta|kuukausi|kuukauden|vuotta|vuosi|vuoden|"
         r"päivää|päivän|viikkoa|viikon")
_QUANTITIES = re.compile(
    rf"(?<!\w){_AMOUNT}\s*[-–]?\s*(?:{_UNIT})(?:\s+(?:kuluttua|later))?(?!\w)|"
    rf"\b(?:hours?|allocated hours|tunnit|työtunnit)\s*[:=]?\s*{_NUMBER}(?!\w)",
    re.IGNORECASE,
)
_STANDARDS = re.compile(
    r"\b(?:ISO|IEC|EN|SFS)(?:[ /-]+(?:ISO|IEC|EN))?[ -]+\d{3,6}"
    r"(?:[-:]\d{1,4})?(?!\w)", re.IGNORECASE,
)
_JOB_TITLE = re.compile(
    r"(?:(?:chief|senior|junior|assistant|deputy)\s+)?"
    r"(?:finance|financial|operations|operational|project|programme|program|"
    r"product|sales|marketing|research|technical|human resources|hr|office|"
    r"software|engineering|managing|executive|environmental|quality|safety|"
    r"accounts payable|team|on-call)\s+"
    r"(?:director|manager|officer|engineer|coordinator|specialist|assistant|clerk|lead|representative)|"
    r"(?:talous|laatu|ohjelma|projekti|tuote|myynti|markkinointi|tutkimus|henkilöstö|"
    r"ympäristö|tiimi|toimitus|turvallisuus)(?:johtaja|päällikkö|asiantuntija|insinööri|koordinaattori)"
    r"(?:n|lle|llä|ltä|ssa|sta|ksi|na)?|(?:osto|myynti)reskontran hoitaja(?:n|lle)?",
    re.IGNORECASE,
)
_BUSINESS_ID = re.compile(r"(?<![\w-])\d{7}-\d(?![\w-])")
_VAT = re.compile(r"(?<!\w)FI\s?\d{8}(?!\w)", re.IGNORECASE)
_AGE_CONTEXT = re.compile(r"\b(?:born|birth|dob|aged?|syntynyt|syntymä\w*|ikä)\b", re.IGNORECASE)


def filter_context_spans(text: str, spans) -> list:
    """Keep identifying dates/names; discard narrowly evidenced false positives."""
    quantities = [(m.start(), m.end()) for pattern in (_QUANTITIES, _STANDARDS)
                  for m in pattern.finditer(text)]
    result = []
    for span in spans:
        nearby = text[max(0, span.start - 40):span.end + 12]
        if span.entity_type == "DATE_TIME" and not _AGE_CONTEXT.search(nearby) and any(
                start <= span.start < span.end <= end for start, end in quantities):
            continue
        if span.entity_type == "PERSON" and _JOB_TITLE.fullmatch(
                text[span.start:span.end].strip()):
            continue
        result.append(span)
    return result


def business_spans(text: str, organization_terms=()) -> list:
    """Find Finnish business/VAT shapes and optional operator-supplied company names.

    A glossary is explicit deployment knowledge, never a list copied from test
    labels. Its effect must be reported separately from out-of-the-box recall.
    """
    result = []
    for kind, pattern in (("FI_BUSINESS_ID", _BUSINESS_ID), ("FI_VAT_NUMBER", _VAT)):
        for match in pattern.finditer(text):
            result.append(SimpleNamespace(start=match.start(), end=match.end(),
                                          entity_type=kind, score=0.85))
    for term in organization_terms:
        if not isinstance(term, str) or not term.strip():
            raise ValueError("Organization glossary entries must be nonempty strings")
        for match in re.finditer(r"(?<!\w)" + re.escape(term.strip()) + r"(?!\w)",
                                 text, re.IGNORECASE):
            result.append(SimpleNamespace(start=match.start(), end=match.end(),
                                          entity_type="ORGANIZATION", score=1.0))
    return result
