import re
from openpyxl import load_workbook


FIELD_TYPES = {
    "name": "PERSON",
    "email": "EMAIL",
    "phone": "PHONE",
    "company": "COMPANY",
    "iban": "IBAN",
    "date": "DATE",
    "personal_id": "PERSONAL_ID",
    "plate": "PLATE",
    "address": "ADDRESS",
}


def collect_typed_values(file_path):
    """
    Collect values from XLSX together with their entity type.
    Includes metadata and hidden worksheets.
    """

    workbook = load_workbook(file_path, data_only=False)

    typed_values = []

    # Metadata
    if workbook.properties.creator:
        typed_values.append(
            ("PERSON", str(workbook.properties.creator))
        )

    if workbook.properties.lastModifiedBy:
        typed_values.append(
            ("PERSON", str(workbook.properties.lastModifiedBy))
        )

    # Worksheets
    for sheet in workbook.worksheets:

        headers = {}

        for cell in sheet[1]:
            if cell.value is not None:
                headers[cell.column] = (
                    str(cell.value)
                    .strip()
                    .lower()
                )

        for row in sheet.iter_rows(min_row=2):

            for cell in row:

                if cell.value is None:
                    continue

                header = headers.get(cell.column)

                if header in FIELD_TYPES:

                    entity_type = FIELD_TYPES[header]

                    typed_values.append(
                        (entity_type, str(cell.value))
                    )

    return typed_values


def get_original_sensitive_values(file_path):
    """
    Read original sensitive values with entity types.
    """

    return sorted(
        set(
            collect_typed_values(file_path)
        )
    )


def get_partial_fragments(entity_type, value):
    """
    Return meaningful fragments which may remain
    after masking or generalization.
    """

    fragments = []

    value = str(value)

    # -------------------------------------------------
    # EMAIL
    # -------------------------------------------------

    if entity_type == "EMAIL" and "@" in value:

        domain = value.split("@", 1)[1]

        if domain:
            fragments.append(
                ("email domain", domain)
            )

    # -------------------------------------------------
    # PHONE
    # -------------------------------------------------

    elif entity_type == "PHONE":

        cleaned = "".join(
            char for char in value
            if char.isalnum()
        )

        if len(cleaned) >= 4:
            fragments.append(
                ("phone suffix", cleaned[-4:])
            )

    # -------------------------------------------------
    # IBAN
    # -------------------------------------------------

    elif entity_type == "IBAN":

        cleaned = "".join(
            char for char in value
            if char.isalnum()
        )

        # Country code
        if len(cleaned) >= 2:
            fragments.append(
                ("IBAN country", cleaned[:2])
            )

        # Last 4 characters
        if len(cleaned) >= 4:
            fragments.append(
                ("IBAN suffix", cleaned[-4:])
            )

    # -------------------------------------------------
    # DATE
    # -------------------------------------------------

    elif entity_type == "DATE":

        match = re.search(
            r"\b(\d{4})",
            value
        )

        if match:
            fragments.append(
                ("date year", match.group(1))
            )

    # -------------------------------------------------
    # FINNISH PERSONAL ID
    # -------------------------------------------------

    elif entity_type == "PERSONAL_ID":

        cleaned = "".join(
            char for char in value
            if char.isalnum()
        )

        # Last 4 characters
        if len(cleaned) >= 4:
            fragments.append(
                (
                    "personal ID suffix",
                    cleaned[-4:]
                )
            )

        # Example:
        # 140106-800L
        # DDMMYY-century-individual/check

        match = re.match(
            r"(\d{2})(\d{2})(\d{2})([-+A])",
            value
        )

        if match:

            yy = match.group(3)
            century_marker = match.group(4)

            if century_marker == "+":
                birth_year = "18" + yy

            elif century_marker == "-":
                birth_year = "19" + yy

            elif century_marker == "A":
                birth_year = "20" + yy

            else:
                birth_year = None

            if birth_year:
                fragments.append(
                    (
                        "birth year from personal ID",
                        birth_year
                    )
                )

    # -------------------------------------------------
    # PLATE
    # -------------------------------------------------

    elif entity_type == "PLATE":

        cleaned = "".join(
            char for char in value
            if char.isalnum()
        )

        if len(cleaned) >= 2:
            fragments.append(
                ("plate suffix", cleaned[-2:])
            )

    # -------------------------------------------------
    # ADDRESS
    # -------------------------------------------------

    elif entity_type == "ADDRESS":

        # Example:
        # ..., CO 69372

        match = re.search(
            r",\s*([A-Z]{2})\s+\d{5}\b",
            value
        )

        if match:
            fragments.append(
                (
                    "address state",
                    match.group(1)
                )
            )

    return fragments


def evaluate_leakage(original_path, anonymized_path):

    original_sensitive = (
        get_original_sensitive_values(
            original_path
        )
    )

    anonymized_values = (
        collect_typed_values(
            anonymized_path
        )
    )

    full_leaks = []
    partial_leaks = []

    # -------------------------------------------------
    # FULL LEAKAGE
    # -------------------------------------------------

    for entity_type, original_value in original_sensitive:

        for output_type, output_value in anonymized_values:

            # Compare only same entity type
            if entity_type != output_type:
                continue

            if (
                original_value.lower()
                in output_value.lower()
            ):

                full_leaks.append(
                    (
                        entity_type,
                        original_value,
                        output_value,
                    )
                )

                break

    # -------------------------------------------------
    # PARTIAL LEAKAGE
    # -------------------------------------------------

    for entity_type, original_value in original_sensitive:

        fragments = get_partial_fragments(
            entity_type,
            original_value,
        )

        for fragment_type, fragment in fragments:

            for output_type, output_value in anonymized_values:

                # Compare only same entity type
                if entity_type != output_type:
                    continue

                # Ignore if full original value exists
                if (
                    original_value.lower()
                    in output_value.lower()
                ):
                    continue

                if fragment.lower() in output_value.lower():

                    partial_leaks.append(
                        (
                            entity_type,
                            fragment_type,
                            fragment,
                            output_value,
                        )
                    )

                    break

    # Remove duplicates
    full_leaks = sorted(
        set(full_leaks)
    )

    partial_leaks = sorted(
        set(partial_leaks)
    )

    # -------------------------------------------------
    # PRINT RESULTS
    # -------------------------------------------------

    print("=" * 70)
    print("XLSX LEAKAGE EVALUATION")
    print("=" * 70)

    print(
        f"\nOriginal sensitive values: "
        f"{len(original_sensitive)}"
    )

    print(
        f"Full sensitive values found: "
        f"{len(full_leaks)}"
    )

    print(
        f"Partial sensitive fragments found: "
        f"{len(partial_leaks)}"
    )

    if full_leaks:

        print("\n[FULL LEAKS]")

        for (
            entity_type,
            original,
            output,
        ) in full_leaks:

            print(
                f"- {entity_type}: "
                f"{original} "
                f"-> found in: {output}"
            )

    else:

        print(
            "\nNo full sensitive values found."
        )

    if partial_leaks:

        print("\n[PARTIAL LEAKS]")

        for (
            entity_type,
            fragment_type,
            fragment,
            output,
        ) in partial_leaks:

            print(
                f"- {entity_type} | "
                f"{fragment_type}: "
                f"{fragment} "
                f"-> found in: {output}"
            )

    else:

        print(
            "\nNo partial sensitive fragments found."
        )

    # -------------------------------------------------
    # SCORE
    # -------------------------------------------------

    if len(full_leaks) > 0:

        if len(full_leaks) == 1:
            score = 2

        elif len(full_leaks) <= 3:
            score = 1

        else:
            score = 0

    else:

        if len(partial_leaks) == 0:
            score = 4

        elif len(partial_leaks) <= 2:
            score = 3

        elif len(partial_leaks) <= 5:
            score = 2

        elif len(partial_leaks) <= 8:
            score = 1

        else:
            score = 0

    print("\n[RESULT]")
    print(
        f"Data Leakage Score: {score}/4"
    )

    if score >= 3:
        print(
            "Technical leakage test: PASS"
        )
    else:
        print(
            "Technical leakage test: FAIL"
        )

    return (
        score,
        full_leaks,
        partial_leaks,
    )


if __name__ == "__main__":

    original_path = input(
        "Enter ORIGINAL XLSX file path: "
    ).strip().strip('"')

    anonymized_path = input(
        "Enter ANONYMIZED XLSX file path: "
    ).strip().strip('"')

    evaluate_leakage(
        original_path,
        anonymized_path,
    )