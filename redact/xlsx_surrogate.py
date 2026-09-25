from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict

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


SURROGATE_VALUES = {

    "PERSON": [
        "Alex Morgan",
        "Jamie Taylor",
        "Casey Parker",
        "Jordan Lee",
    ],

    "EMAIL": [
        "alex.morgan@surrogate.invalid",
        "jamie.taylor@surrogate.invalid",
        "casey.parker@surrogate.invalid",
        "jordan.lee@surrogate.invalid",
    ],

    "PHONE": [
        "+999 00 900 1001",
        "+999 00 900 1002",
        "+999 00 900 1003",
        "+999 00 900 1004",
    ],

    "COMPANY": [
        "Northstar Synthetic Ltd.",
        "Bluewave Synthetic Ltd.",
        "Greenfield Synthetic Ltd.",
        "Silverline Synthetic Ltd.",
    ],

    "IBAN": [
        "ZZ00SYNTH000000000001",
        "ZZ00SYNTH000000000002",
        "ZZ00SYNTH000000000003",
        "ZZ00SYNTH000000000004",
    ],

    "PERSONAL_ID": [
        "SYN-ID-9001",
        "SYN-ID-9002",
        "SYN-ID-9003",
        "SYN-ID-9004",
    ],

    "PLATE": [
        "SYN-91",
        "SYN-92",
        "SYN-93",
        "SYN-94",
    ],

    "ADDRESS": [
        "100 Synthetic Avenue, Demo City",
        "200 Synthetic Avenue, Demo City",
        "300 Synthetic Avenue, Demo City",
        "400 Synthetic Avenue, Demo City",
    ],
}


def parse_date(value):
    """
    Convert Excel date/datetime or date string into datetime.
    """

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(
            value,
            datetime.min.time()
        )

    value = str(value)

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(
                value,
                fmt
            )
        except ValueError:
            pass

    return None


def collect_original_dates(workbook):
    """
    Collect all DATE values before anonymization.
    """

    dates = []

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

                header = headers.get(
                    cell.column
                )

                if header != "date":
                    continue

                parsed = parse_date(
                    cell.value
                )

                if parsed is not None:
                    dates.append(parsed)

    return dates


def choose_safe_date_shift(original_dates):
    """
    Find one fixed offset for the whole workbook.

    Requirements:
    - same offset for every date
    - preserves chronological order
    - preserves relative time differences
    - shifted years must not overlap original years
    """

    if not original_dates:
        return 3652

    original_years = {
        value.year
        for value in original_dates
    }

    # Try approximately +10 years, +11 years, etc.
    # until no surrogate year collides with
    # any original year in the workbook.
    for years in range(10, 121):

        shift_days = round(
            years * 365.2425
        )

        shifted_dates = []

        try:
            for original in original_dates:

                shifted = (
                    original
                    + timedelta(
                        days=shift_days
                    )
                )

                shifted_dates.append(
                    shifted
                )

        except OverflowError:
            continue

        shifted_years = {
            value.year
            for value in shifted_dates
        }

        if original_years.isdisjoint(
            shifted_years
        ):
            return shift_days

    raise ValueError(
        "Could not find a safe date shift."
    )


def shift_date(value, shift_days):
    """
    Apply the selected fixed offset.
    """

    parsed = parse_date(value)

    if parsed is None:
        return "[SURROGATE_DATE]"

    shifted = (
        parsed
        + timedelta(
            days=shift_days
        )
    )

    return shifted.date()


def get_new_surrogate(
    data_type,
    original_value,
    counters,
    date_shift_days,
):

    if data_type == "DATE":

        return shift_date(
            original_value,
            date_shift_days,
        )

    values = SURROGATE_VALUES.get(
        data_type,
        []
    )

    index = counters[data_type]

    if index < len(values):

        replacement = values[index]

    else:

        replacement = (
            f"[{data_type}_SURROGATE_"
            f"{index + 1:03d}]"
        )

    counters[data_type] += 1

    return replacement


def surrogate_xlsx(
    input_path,
    output_path,
):

    input_path = Path(input_path)
    output_path = Path(output_path)

    workbook = load_workbook(
        input_path
    )

    # Choose the date offset BEFORE modifying workbook.
    original_dates = collect_original_dates(
        workbook
    )

    date_shift_days = choose_safe_date_shift(
        original_dates
    )

    mappings = {}
    counters = defaultdict(int)

    # -------------------------------------------------
    # METADATA
    # -------------------------------------------------

    if workbook.properties.creator:

        original = str(
            workbook.properties.creator
        )

        key = (
            "PERSON",
            original,
        )

        if key not in mappings:

            mappings[key] = get_new_surrogate(
                "PERSON",
                original,
                counters,
                date_shift_days,
            )

        workbook.properties.creator = (
            mappings[key]
        )

    if workbook.properties.lastModifiedBy:

        original = str(
            workbook.properties.lastModifiedBy
        )

        key = (
            "PERSON",
            original,
        )

        if key not in mappings:

            mappings[key] = get_new_surrogate(
                "PERSON",
                original,
                counters,
                date_shift_days,
            )

        workbook.properties.lastModifiedBy = (
            mappings[key]
        )

    # -------------------------------------------------
    # WORKSHEETS
    # -------------------------------------------------

    for sheet in workbook.worksheets:

        headers = {}

        for cell in sheet[1]:

            if cell.value is not None:

                headers[cell.column] = (
                    str(cell.value)
                    .strip()
                    .lower()
                )

        for row in sheet.iter_rows(
            min_row=2
        ):

            for cell in row:

                if cell.value is None:
                    continue

                header = headers.get(
                    cell.column
                )

                if header not in FIELD_TYPES:
                    continue

                data_type = FIELD_TYPES[
                    header
                ]

                original_object = cell.value
                original_string = str(
                    original_object
                )

                key = (
                    data_type,
                    original_string,
                )

                if key not in mappings:

                    mappings[key] = (
                        get_new_surrogate(
                            data_type,
                            original_object,
                            counters,
                            date_shift_days,
                        )
                    )

                cell.value = mappings[key]

    # -------------------------------------------------
    # SAVE
    # -------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    workbook.save(
        output_path
    )

    print(
        "\nSurrogate file saved to:"
    )

    print(output_path)

    print(
        f"\nSafe date shift selected: "
        f"+{date_shift_days} days"
    )

    print(
        "\n[SURROGATE MAPPINGS]"
    )

    for (
        data_type,
        original
    ), replacement in mappings.items():

        print(
            f"{data_type:<12} | "
            f"{original} -> "
            f"{replacement}"
        )


if __name__ == "__main__":

    input_path = input(
        "Enter original XLSX file path: "
    ).strip().strip('"')

    output_path = input(
        "Enter output XLSX file path: "
    ).strip().strip('"')

    surrogate_xlsx(
        input_path,
        output_path,
    )