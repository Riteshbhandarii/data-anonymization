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
    r"\b(?:ISO|IEC|EN|SFS)(?:[ /-]+(?:ISO|IEC|EN))*[ -]+\d{3,6}"
    r"(?:-\d{1,4})*(?::\d{4})?(?![\w:/-])|"
    r"\bASTM[ ]+[A-G]\d{1,5}M?(?:/[A-G]\d{1,5}M?)?"
    r"(?:-\d{2}[a-z]?(?:\(\d{4}\))?)?(?![\w:/-])", re.IGNORECASE,
)
# Only numeric/date recognizers are corrected inside technical citations.
# Never discard PERSON, ORGANIZATION or a business/personal ID merely because
# another overlapping candidate resembles a standard number.
_STANDARD_CANDIDATE_TYPES = {"DATE_TIME", "US_DRIVER_LICENSE"}
_CALENDAR_SHAPE = re.compile(r"\b\d{4}-\d{1,2}(?:-\d{1,2})?\b")
_TECHNICAL_REFERENCE = re.compile(
    r"\b(?:standards?(?:\s+(?:number|reference|code))?|specifications?|standard\w*|"
    r"conforms?\s+to|complies\s+with)\s*[:#]?\s*$", re.IGNORECASE,
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
_AGE_CONTEXT = re.compile(
    r"\b(?:born|birth\w*|dob|aged?|turn(?:s|ed|ing)?|"
    r"synt(?:y|ym)\w*|ikä\w*|iä\w*|täyt\w*|potila\w*|hakija\w*|"
    r"patient\w*|applicant\w*|child\w*|infant\w*|doctor\w*|laps\w*|vauva\w*|lääkäri\w*|"
    r"tenure|lifespan|lived|experience|palvelusvuo\w*)\b",
    re.IGNORECASE,
)
_AGE_SUFFIX = re.compile(r"^[\s-]*(?:old(?:er)?|young(?:er)?|vanh\w*|ikä\w*)\b", re.IGNORECASE)
_HUMAN_REFERENCE = re.compile(
    r"\b(?:i|he|she|him|her|we|they|you|my|mine|your|yours|his|hers|our|ours|"
    r"their|theirs|us|them|hän|hänen|minä|minun|sinä|sinun|me|meidän|te|teidän|heidän|"
    r"person\w*|woman|man|people|parent\w*|daughter\w*|son|sister\w*|brother\w*|"
    r"henkilö\w*|tytär\w*|poika\w*|äiti\w*|isä\w*)\b|['’]s\b", re.IGNORECASE,
)
# Positive bindings end immediately before the quantity. An operational word
# elsewhere in the sentence cannot establish what that quantity describes.
_DURATION_FIELD = re.compile(
    r"\b(?:allocation|allocated(?:\s+(?:time|hours))?|duration|term|period|"
    r"varattu(?:\s+aika)?|kesto|sopimuskausi)\s*"
    r"(?:(?:is|was|on|oli)\s*|[:=]\s*)?$", re.IGNORECASE,
)
_TIME_SUBJECT_EN = (
    r"(?:contract|(?:service\s+)?agreement|lease|warranty|service|delivery|shipment|"
    r"response|retention|maintenance|project|system|software|migration|review|inspection)"
)
_TIME_SUBJECT_FI = (
    r"(?:sopimus|vuokrasopimus|takuu|huolto|projekti|järjestelmä|siirtymä|"
    r"katselmus|tarkastus|toimitus)"
)
_BOUND_DURATION = re.compile(
    rf"\b(?P<subject_en>{_TIME_SUBJECT_EN})\s+(?:"
    r"(?:lasts?|lasted|takes?|continues?|runs?)\s+(?:for\s+)?|"
    r"(?:is|was|remains?|stays?)\s+(?:active|available|valid|open|in force)\s+(?:for\s+)?)$|"
    rf"\b(?P<subject_fi>{_TIME_SUBJECT_FI})\s+(?:"
    r"(?:kestää|kesti|jatkuu|tapahtuu)\s+|"
    r"(?:on|oli|pysyy)\s+(?:voimassa|käytössä|lukutilassa)\s+)$",
    re.IGNORECASE,
)
_ALLOCATED_TIME = re.compile(r"\b(?:on\s+)?varattu\s+(?:aika\s+)?$", re.IGNORECASE)
_HOURS_FIELD = re.compile(r"^(?:hours?|allocated hours|tunnit|työtunnit)\b", re.IGNORECASE)

# This is a class of unnamed facilities, never a list of study place names.
# Only lowercase common-noun phrases in impersonal logistics clauses qualify.
_FACILITY = re.compile(
    r"(?<!\w)(?:(?i:the|a|an)\s+)?(?:(?:main|central|regional|local)\s+)?"
    r"(?:warehouse|depot|stockroom|storeroom|loading bay|storage area)(?!\w)|"
    r"(?<!\w)(?:pää|keskus)?varasto(?:ssa|sta|on|lla|lta|lle|a|n)?(?!\w)"
)
_LOGISTICS = re.compile(
    r"\b(?:stock|inventory|goods|cargo|deliver(?:y|ies)|shipments?|consignments?|pallets?|"
    r"toimit\w*|tavar\w*|lähety\w*|varastosal\w*|palaut\w*)\b", re.IGNORECASE,
)
_PERSONAL_PLACE = re.compile(
    r"\b(?:my|your|his|her|our|their|its|whose|only|sole|unique|home|private|personal|"
    r"residen\w*|live[sd]?|workplace|works?|employee\w*|supervisor\w*|contact|"
    r"minun|sinun|hänen|heidän|meidän|ainoa\w*|koti\w*|yksityi\w*|asuu|asuva\w*|"
    r"henkilö\w*|työntekij\w*|yhteyshenkil\w*|sijai\w*|osoit\w*|nimeltä|"
    r"located|situated|named|called)\b|['’]s\b", re.IGNORECASE,
)
_FACILITY_END = re.compile(
    r"^\s*(?:$|,?\s*(?:and|but|while|whereas)\s+(?:the|a|an|this|that|these|those)\b|"
    r",\s*eikä\b)", re.IGNORECASE,
)
_FACILITY_PREFIX = re.compile(
    r"(?:at|to|in|from|into|through|within|inside|"
    r"tule\w*|saapu\w*|siirr\w*|palaut\w*|toimit\w*|vied\w*|mene\w*)$", re.IGNORECASE,
)
_SAFE_SENTENCE_START = re.compile(
    r"(?:the|a|an|all|returned|incoming|outgoing|stock|inventory|goods|cargo|"
    r"deliveries|shipments|pallets|toimit\w*|tavar\w*|lähety\w*|palaut\w*)$", re.IGNORECASE,
)


def _clause(text, start, end):
    """Return sentence/field boundaries without splitting inside the candidate."""
    left = max(text.rfind(mark, 0, start) for mark in "\n.;!?") + 1
    right = min((at for mark in "\n.;!?" if (at := text.find(mark, end)) >= 0),
                default=len(text))
    return left, right


def _unnamed_logistics_facility(text, span, spans, facilities):
    for phrase in facilities:
        if not phrase.start() <= span.start < span.end <= phrase.end():
            continue
        left, right = _clause(text, phrase.start(), phrase.end())
        context = text[left:right]
        if (not _LOGISTICS.search(context) or _PERSONAL_PLACE.search(context)
                or any(char.isdigit() for char in context)
                or not _FACILITY_END.match(text[phrase.end():right])):
            continue
        # Do not exempt a common-noun substring inside an owner/locality name.
        previous = re.search(r"(\w+)\W*$", text[left:phrase.start()])
        if previous and not _FACILITY_PREFIX.fullmatch(previous.group(1)):
            continue
        words = list(re.finditer(r"[^\W\d_][\w-]*", context))
        if any(m.group()[0].isupper() and not (
                index == 0 and _SAFE_SENTENCE_START.fullmatch(m.group()))
               for index, m in enumerate(words)):
            continue
        if any(s.entity_type in {"PERSON", "ORGANIZATION", "LOCATION"}
               and s.start < right and s.end > left
               and not phrase.start() <= s.start < s.end <= phrase.end() for s in spans):
            continue
        return True
    return False


def filter_context_spans(text: str, spans) -> list:
    """Keep identifying dates/names; discard narrowly evidenced false positives."""
    spans = list(spans)
    quantities = list(_QUANTITIES.finditer(text))
    standards = list(_STANDARDS.finditer(text))
    facilities = list(_FACILITY.finditer(text))
    result = []
    for span in spans:
        if span.entity_type in _STANDARD_CANDIDATE_TYPES:
            for reference in standards:
                if not reference.start() <= span.start < span.end <= reference.end():
                    continue
                left, right = _clause(text, reference.start(), reference.end())
                context = text[left:right]
                if ((span.entity_type == "DATE_TIME" and _AGE_CONTEXT.search(context)) or (
                        _CALENDAR_SHAPE.search(reference.group())
                        and not _TECHNICAL_REFERENCE.search(text[left:reference.start()]))):
                    # EN can also be a language marker before an actual date.
                    # Calendar-shaped codes need explicit technical evidence.
                    continue
                break
            else:
                reference = None
            if reference is not None:
                continue
        if span.entity_type == "DATE_TIME":
            for quantity in quantities:
                if quantity.start() <= span.start < span.end <= quantity.end():
                    left, right = _clause(text, quantity.start(), quantity.end())
                    context = text[left:right]
                    before = text[left:quantity.start()]
                    hours_field = _HOURS_FIELD.match(quantity.group())
                    binding = _BOUND_DURATION.search(before)
                    duration_field = (_DURATION_FIELD.search(before)
                                      or _ALLOCATED_TIME.search(before) or binding)
                    # Contracts, agreements and service can describe personal
                    # history. Only unambiguous artifact heads bypass the human
                    # guard when a reporting person appears in the same clause.
                    inanimate_duration = binding and (
                        (binding.group("subject_en") or "").casefold()
                        in {"warranty", "system", "software"}
                        or (binding.group("subject_fi") or "").casefold()
                        in {"takuu", "järjestelmä"})
                    human = (_HUMAN_REFERENCE.search(context) or _JOB_TITLE.search(context)
                             or any(s.entity_type == "PERSON" and s.start < right and s.end > left
                                    for s in spans))
                    # Unknown temporal context stays masked. Positive operational
                    # evidence is required; an age-suffix blacklist alone is unsafe.
                    # A reporting person elsewhere does not change the subject
                    # of a closed phrase such as "the warranty lasts for ...".
                    # Generic fields still require the broader human guard.
                    if ((hours_field or inanimate_duration or (duration_field and not human))
                            and not _AGE_CONTEXT.search(context)
                            and not _AGE_SUFFIX.match(text[quantity.end():right])):
                        break
            else:
                quantity = None
            if quantity is not None:
                continue
        if span.entity_type == "PERSON" and _JOB_TITLE.fullmatch(
                text[span.start:span.end].strip()):
            continue
        if span.entity_type == "LOCATION" and _unnamed_logistics_facility(
                text, span, spans, facilities):
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
