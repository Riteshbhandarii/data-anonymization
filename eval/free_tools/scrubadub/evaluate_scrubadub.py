from pathlib import Path
from collections import defaultdict
import csv
import json
import re


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

LABELS_DIR = BASE_DIR / "labels"
RESULTS_DIR = BASE_DIR / "scrubadub_results"

OUTPUT_DIR = BASE_DIR / "scrubadub_evaluation"
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(text):
    """
    Basic normalization used when checking whether an original
    sensitive value remains in the scrubadub output.
    """
    if text is None:
        return ""

    text = str(text)

    text = re.sub(r"\s+", " ", text)

    return text.strip().casefold()


# ============================================================
# READ ANONYMIZED SECTION FROM RESULT FILE
# ============================================================

def read_anonymized_result(result_path):

    text = result_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    marker = "ANONYMIZED BY SCRUBADUB"

    if marker not in text:
        raise ValueError(
            f"Could not find anonymized section in {result_path.name}"
        )

    anonymized = text.split(marker, 1)[1]

    anonymized = re.sub(
        r"^\s*=+\s*",
        "",
        anonymized
    )

    return anonymized.strip()


# ============================================================
# FIND RESULT FILE FOR A LABEL
# ============================================================

def find_result_file(label_data):

    original_file = Path(label_data["file"])

    stem = original_file.stem

    expected = RESULTS_DIR / f"{stem}_scrubadub_result.txt"

    if expected.exists():
        return expected

    return None


# ============================================================
# LOAD ALL LABEL FILES
# ============================================================

label_files = sorted(LABELS_DIR.glob("*.json"))

print("=" * 70)
print("SCRUBADUB EVALUATION")
print("=" * 70)

print(f"\nFound {len(label_files)} JSON label files.")


if not label_files:
    print("\nERROR: No JSON files found in:")
    print(LABELS_DIR)
    raise SystemExit(1)


# ============================================================
# STORAGE
# ============================================================

detail_rows = []

stats = defaultdict(
    lambda: {
        "total": 0,
        "removed": 0,
        "remaining": 0
    }
)

missing_results = []
bad_labels = []


# ============================================================
# PROCESS LABELS
# ============================================================

for number, label_path in enumerate(label_files, start=1):

    print(
        f"[{number}/{len(label_files)}] "
        f"Evaluating {label_path.name}"
    )

    try:

        with open(
            label_path,
            "r",
            encoding="utf-8"
        ) as f:
            label = json.load(f)

    except Exception as error:

        bad_labels.append(
            (label_path.name, str(error))
        )

        continue

    original_file = label.get("file", "")
    language = label.get("language", "unknown").lower()
    file_format = label.get("format", "unknown").lower()

    entities = label.get("entities", [])

    # --------------------------------------------------------
    # Find corresponding scrubadub result
    # --------------------------------------------------------

    result_path = find_result_file(label)

    if result_path is None:

        missing_results.append(original_file)

        continue

    try:

        anonymized_text = read_anonymized_result(
            result_path
        )

    except Exception as error:

        missing_results.append(
            f"{original_file} ({error})"
        )

        continue

    normalized_output = normalize(anonymized_text)

    # --------------------------------------------------------
    # Evaluate every labelled entity
    # --------------------------------------------------------

    for entity in entities:

        entity_type = (
            entity.get("type", "UNKNOWN")
            .strip()
            .upper()
        )

        value = str(
            entity.get("value", "")
        ).strip()

        location = (
            entity.get("location", "unknown")
            .strip()
            .lower()
        )

        if not value:
            continue

        normalized_value = normalize(value)

        still_present = (
            normalized_value in normalized_output
        )

        if still_present:
            status = "MISSED"
        else:
            status = "REMOVED"

        # ----------------------------------------------------
        # Save detailed result
        # ----------------------------------------------------

        detail_rows.append({
            "file": original_file,
            "language": language,
            "format": file_format,
            "entity_type": entity_type,
            "location": location,
            "value": value,
            "status": status
        })

        # ----------------------------------------------------
        # Update statistics
        # ----------------------------------------------------

        key = (
            language,
            file_format,
            entity_type,
            location
        )

        stats[key]["total"] += 1

        if status == "REMOVED":
            stats[key]["removed"] += 1
        else:
            stats[key]["remaining"] += 1


# ============================================================
# WRITE DETAILED RESULTS
# ============================================================

detail_path = OUTPUT_DIR / "entity_level_results.csv"

with open(
    detail_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "file",
            "language",
            "format",
            "entity_type",
            "location",
            "value",
            "status"
        ]
    )

    writer.writeheader()
    writer.writerows(detail_rows)


# ============================================================
# CREATE FULL BREAKDOWN
# ============================================================

breakdown_path = OUTPUT_DIR / "breakdown_results.csv"

with open(
    breakdown_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "language",
        "format",
        "entity_type",
        "location",
        "total",
        "removed",
        "missed",
        "removal_rate_percent"
    ])

    for key in sorted(stats):

        language, file_format, entity_type, location = key

        total = stats[key]["total"]
        removed = stats[key]["removed"]
        missed = stats[key]["remaining"]

        rate = (
            removed / total * 100
            if total
            else 0
        )

        writer.writerow([
            language,
            file_format,
            entity_type,
            location,
            total,
            removed,
            missed,
            round(rate, 2)
        ])


# ============================================================
# AGGREGATE BY ENTITY TYPE + LANGUAGE
# ============================================================

entity_language_stats = defaultdict(
    lambda: {
        "total": 0,
        "removed": 0,
        "missed": 0
    }
)


for row in detail_rows:

    key = (
        row["language"],
        row["entity_type"]
    )

    entity_language_stats[key]["total"] += 1

    if row["status"] == "REMOVED":
        entity_language_stats[key]["removed"] += 1
    else:
        entity_language_stats[key]["missed"] += 1


entity_language_path = (
    OUTPUT_DIR /
    "entity_language_summary.csv"
)


with open(
    entity_language_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "language",
        "entity_type",
        "total",
        "removed",
        "missed",
        "removal_rate_percent"
    ])

    for key in sorted(entity_language_stats):

        language, entity_type = key

        values = entity_language_stats[key]

        total = values["total"]
        removed = values["removed"]
        missed = values["missed"]

        rate = (
            removed / total * 100
            if total
            else 0
        )

        writer.writerow([
            language,
            entity_type,
            total,
            removed,
            missed,
            round(rate, 2)
        ])


# ============================================================
# AGGREGATE BY FORMAT + LANGUAGE
# ============================================================

format_language_stats = defaultdict(
    lambda: {
        "total": 0,
        "removed": 0,
        "missed": 0
    }
)


for row in detail_rows:

    key = (
        row["language"],
        row["format"]
    )

    format_language_stats[key]["total"] += 1

    if row["status"] == "REMOVED":
        format_language_stats[key]["removed"] += 1
    else:
        format_language_stats[key]["missed"] += 1


format_language_path = (
    OUTPUT_DIR /
    "format_language_summary.csv"
)


with open(
    format_language_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "language",
        "format",
        "total_entities",
        "removed",
        "missed",
        "removal_rate_percent"
    ])

    for key in sorted(format_language_stats):

        language, file_format = key

        values = format_language_stats[key]

        total = values["total"]
        removed = values["removed"]
        missed = values["missed"]

        rate = (
            removed / total * 100
            if total
            else 0
        )

        writer.writerow([
            language,
            file_format,
            total,
            removed,
            missed,
            round(rate, 2)
        ])


# ============================================================
# BODY/NOTES/HIDDEN/METADATA SUMMARY
# ============================================================

location_stats = defaultdict(
    lambda: {
        "total": 0,
        "removed": 0,
        "missed": 0
    }
)


for row in detail_rows:

    location = row["location"]

    location_stats[location]["total"] += 1

    if row["status"] == "REMOVED":
        location_stats[location]["removed"] += 1
    else:
        location_stats[location]["missed"] += 1


location_path = (
    OUTPUT_DIR /
    "location_summary.csv"
)


with open(
    location_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "location",
        "total",
        "removed",
        "missed",
        "removal_rate_percent"
    ])

    for location in sorted(location_stats):

        values = location_stats[location]

        total = values["total"]
        removed = values["removed"]
        missed = values["missed"]

        rate = (
            removed / total * 100
            if total
            else 0
        )

        writer.writerow([
            location,
            total,
            removed,
            missed,
            round(rate, 2)
        ])


# ============================================================
# OVERALL STATISTICS
# ============================================================

total_entities = len(detail_rows)

total_removed = sum(
    1
    for row in detail_rows
    if row["status"] == "REMOVED"
)

total_missed = sum(
    1
    for row in detail_rows
    if row["status"] == "MISSED"
)

overall_rate = (
    total_removed / total_entities * 100
    if total_entities
    else 0
)


# ============================================================
# PRINT ENTITY RESULTS
# ============================================================

print("\n" + "=" * 70)
print("RESULTS BY ENTITY TYPE AND LANGUAGE")
print("=" * 70)


for key in sorted(entity_language_stats):

    language, entity_type = key

    values = entity_language_stats[key]

    total = values["total"]
    removed = values["removed"]
    missed = values["missed"]

    rate = (
        removed / total * 100
        if total
        else 0
    )

    print(
        f"{language.upper():2} "
        f"{entity_type:15} "
        f"{removed:4}/{total:<4} "
        f"removed "
        f"({rate:6.2f}%) | "
        f"missed: {missed}"
    )


# ============================================================
# PRINT FORMAT RESULTS
# ============================================================

print("\n" + "=" * 70)
print("RESULTS BY FORMAT AND LANGUAGE")
print("=" * 70)


for key in sorted(format_language_stats):

    language, file_format = key

    values = format_language_stats[key]

    total = values["total"]
    removed = values["removed"]
    missed = values["missed"]

    rate = (
        removed / total * 100
        if total
        else 0
    )

    print(
        f"{language.upper():2} "
        f"{file_format.upper():5} "
        f"{removed:5}/{total:<5} "
        f"removed "
        f"({rate:6.2f}%) | "
        f"missed: {missed}"
    )


# ============================================================
# PRINT LOCATION RESULTS
# ============================================================

print("\n" + "=" * 70)
print("RESULTS BY LOCATION")
print("=" * 70)


for location in sorted(location_stats):

    values = location_stats[location]

    total = values["total"]
    removed = values["removed"]
    missed = values["missed"]

    rate = (
        removed / total * 100
        if total
        else 0
    )

    print(
        f"{location:15} "
        f"{removed:5}/{total:<5} "
        f"removed "
        f"({rate:6.2f}%) | "
        f"missed: {missed}"
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("OVERALL")
print("=" * 70)

print(f"Label files evaluated: {len(label_files)}")
print(f"Entities evaluated:    {total_entities}")
print(f"Entities removed:      {total_removed}")
print(f"Entities missed:       {total_missed}")
print(f"Removal rate:          {overall_rate:.2f}%")

print(f"\nMissing result files:  {len(missing_results)}")
print(f"Bad label files:       {len(bad_labels)}")


if missing_results:

    print("\nWARNING — missing results:")

    for item in missing_results[:20]:
        print(" -", item)

    if len(missing_results) > 20:
        print(
            f" ... and "
            f"{len(missing_results) - 20} more"
        )


if bad_labels:

    print("\nWARNING — invalid label files:")

    for name, error in bad_labels:
        print(f" - {name}: {error}")


print("\n" + "=" * 70)
print("OUTPUT FILES")
print("=" * 70)

print(detail_path)
print(breakdown_path)
print(entity_language_path)
print(format_language_path)
print(location_path)

print("\nEvaluation complete.")
