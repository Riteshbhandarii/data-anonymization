"""Pattern recognizers for the synthetic benchmark corpus.

Presidio has no recognizer for vehicle plates or invoice numbers, and it does
not load its Finnish identity code recognizer by default. These fill those
gaps so the benchmark measures the detector and not a missing recognizer.

The formats are the ones corpus/generate.py produces, so they are stand-ins
for whatever real documents use, not a claim about real formats.
"""

from presidio_analyzer import Pattern, PatternRecognizer

# Plate: three letters, a dash, three digits. The generator uses the Finnish
# alphabet without Q, W and Ö.
PLATE_PATTERN = Pattern(
    name="synthetic_finnish_plate",
    regex=r"\b[ABCDEFGHIJKLMNOPRSTUVXYZ]{3}-\d{3}\b",
    score=0.85,
)

# Invoice: INV- and five digits, the generator's own format.
INVOICE_PATTERN = Pattern(
    name="synthetic_invoice_number",
    regex=r"\bINV-\d{5}\b",
    score=0.95,
)

# Identity code, SHAPE ONLY, NO CHECKSUM VALIDATION. The generator makes codes
# with invalid check characters on purpose, so a validating recognizer would
# reject them. Presidio does not load its own FI_PERSONAL_IDENTITY_CODE
# recognizer by default in any case.
# This pattern is a benchmark choice, not a statement about what a real
# deployment should do; see docs/open-questions.md.
# Example: 140106-800L
PERSONAL_ID_NO_CHECKSUM_PATTERN = Pattern(
    name="finnish_personal_id_shape_no_checksum",
    regex=r"\b\d{6}[-+A]\d{3}[0-9ABCDEFHJKLMNPRSTUVWXY]\b",
    score=0.85,
)


def register_project_recognizers(analyzer, languages=("en", "fi")):
    """Register the three recognizers for each language the analyzer supports."""
    for language in languages:
        for entity, name, pattern in (
            ("PLATE", "PlateRecognizer", PLATE_PATTERN),
            ("INVOICE", "InvoiceRecognizer", INVOICE_PATTERN),
            ("PERSONAL_ID", "PersonalIdNoChecksumRecognizer", PERSONAL_ID_NO_CHECKSUM_PATTERN),
        ):
            analyzer.registry.add_recognizer(PatternRecognizer(
                supported_entity=entity,
                name=f"{name}-{language}",
                patterns=[pattern],
                supported_language=language,
            ))
    return analyzer
