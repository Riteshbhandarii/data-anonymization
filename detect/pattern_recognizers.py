from presidio_analyzer import Pattern, PatternRecognizer


# --------------------------------------------------
# PLATE
# Synthetic corpus format: ABC-123
# Generator alphabet:
# ABCDEFGHIJKLMNOPRSTUVXYZ
# --------------------------------------------------

PLATE_PATTERN = Pattern(
    name="synthetic_finnish_plate",
    regex=r"\b[ABCDEFGHIJKLMNOPRSTUVXYZ]{3}-\d{3}\b",
    score=0.85,
)


# --------------------------------------------------
# INVOICE
# Synthetic corpus format: INV-12345
# --------------------------------------------------

INVOICE_PATTERN = Pattern(
    name="synthetic_invoice_number",
    regex=r"\bINV-\d{5}\b",
    score=0.95,
)


# --------------------------------------------------
# PERSONAL ID
#
# Shape-only recognizer for the synthetic benchmark.
# The generated IDs intentionally have invalid
# checksums, so Presidio's normal Finnish recognizer
# rejects them.
#
# Example:
# 140106-800L
#
# This does NOT claim that the identity code is valid.
# --------------------------------------------------

PERSONAL_ID_PATTERN = Pattern(
    name="synthetic_finnish_personal_id",
    regex=r"\b\d{6}[-+A]\d{3}[0-9ABCDEFHJKLMNPRSTUVWXY]\b",
    score=0.85,
)


def register_project_recognizers(analyzer):
    """
    Register project-specific recognizers for both
    English and Finnish benchmark documents.
    """

    for language in ("en", "fi"):

        plate_recognizer = PatternRecognizer(
            supported_entity="PLATE",
            name=f"PlateRecognizer-{language}",
            patterns=[PLATE_PATTERN],
            supported_language=language,
        )

        invoice_recognizer = PatternRecognizer(
            supported_entity="INVOICE",
            name=f"InvoiceRecognizer-{language}",
            patterns=[INVOICE_PATTERN],
            supported_language=language,
        )

        personal_id_recognizer = PatternRecognizer(
            supported_entity="PERSONAL_ID",
            name=f"SyntheticPersonalIdRecognizer-{language}",
            patterns=[PERSONAL_ID_PATTERN],
            supported_language=language,
        )

        analyzer.registry.add_recognizer(plate_recognizer)
        analyzer.registry.add_recognizer(invoice_recognizer)
        analyzer.registry.add_recognizer(personal_id_recognizer)

    return analyzer