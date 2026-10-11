
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
OUTPUT_DIR = BASE_DIR / "scrubadub_evaluation_v2"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(text):
    if text is None:
        return ""

    return re.sub(
        r"\s+", " ", str(text)
    ).strip().casefold()


# ============================================================
# READ ORIGINAL AND ANONYMIZED SECTIONS
# ============================================================

def read_sections(result_path):
    text = result_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    original_match = re.search(
        r"(?m)^ORIGINAL\s*$",
        text
    )

    anonymized_match = re.search(
        r"(?m)^ANONYMIZED BY SCRUBADUB\s*$",
        text
    )

    if not original_match or not anonymized_match:
        raise ValueError(
            "Missing ORIGINAL or ANONYMIZED section"
        )

    if original_match.end() >= anonymized_match.start():
        raise ValueError(
            "Result sections are in incorrect order"
        )

    original = text[
        original_match.end():anonymized_match.start()
    ]

    anonymized = text[
        anonymized_match.end():
    ]

    def clean_section(section):
        section = re.sub(
            r"(?m)^\s*=+\s*$",
            "",
            section
        )
        return section.strip()

    return (
        clean_section(original),
        clean_section(anonymized)
    )


# ============================================================
# FIND RESULT FILE
# ============================================================

def find_result_file(label_data):
    original_file = Path(label_data["file"])
    stem = original_file.stem

    expected = (
        RESULTS_DIR
        / f"{stem}_scrubadub_result.txt"
    )

    if expected.exists():
        return expected

    return None


# ============================================================
# CLASSIFY LABELLED ENTITIES
# ============================================================

def classify(value, original, anonymized):
    value_norm = normalize(value)
    original_norm = normalize(original)
    anonymized_norm = normalize(anonymized)

    if value_norm not in original_norm:
        return "NOT_EXTRACTED"

    if value_norm in anonymized_norm:
        return "MISSED"

    return "CHANGED_REVIEW"


# ============================================================
# LOAD LABEL FILES
# ============================================================

label_files = sorted(
    LABELS_DIR.glob("*.json")
)

print("=" * 70)
print("SCRUBADUB EVALUATION V2")
print("=" * 70)
print(f"Found {len(label_files)} JSON label files.")

if not label_files:
    raise SystemExit(
        f"ERROR: No labels found in {LABELS_DIR}"
    )


# ============================================================
# PROCESS ALL LABELS
# ============================================================

detail_rows = []
missing_results = []
bad_labels = []

for number, label_path in enumerate(
    label_files, start=1
):
    print(
        f"[{number}/{len(label_files)}] "
        f"Evaluating {label_path.name}"
    )

    try:
        label = json.loads(
            label_path.read_text(
                encoding="utf-8"
            )
        )

        original_file = label["file"]
        language = str(
            label.get("language", "unknown")
        ).lower()

        file_format = str(
            label.get("format", "unknown")
        ).lower()

        result_path = find_result_file(label)

        if result_path is None:
            missing_results.append(original_file)
            continue

        original, anonymized = read_sections(
            result_path
        )

        for entity in label.get("entities", []):
            value = str(
                entity.get("value", "")
            ).strip()

            if not value:
                continue

            status = classify(
                value,
                original,
                anonymized
            )

            detail_rows.append({
                "file": original_file,
                "language": language,
                "format": file_format,
                "entity_type": str(
                    entity.get("type", "UNKNOWN")
                ).strip().upper(),
                "location": str(
                    entity.get("location", "unknown")
                ).strip().lower(),
                "value": value,
                "status": status
            })

    except Exception as error:
        bad_labels.append(
            (label_path.name, str(error))
        )


# ============================================================
# SAVE ENTITY-LEVEL RESULTS
# ============================================================

detail_path = (
    OUTPUT_DIR / "entity_level_results_v2.csv"
)

fields = [
    "file",
    "language",
    "format",
    "entity_type",
    "location",
    "value",
    "status"
]

with detail_path.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(detail_rows)


# ============================================================
# CREATE SUMMARY FILES
# ============================================================

def write_summary(filename, group_fields):
    stats = defaultdict(
        lambda: defaultdict(int)
    )

    for row in detail_rows:
        key = tuple(
            row[field]
            for field in group_fields
        )

        stats[key][row["status"]] += 1

    output_path = OUTPUT_DIR / filename

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:
        writer = csv.writer(f)

        writer.writerow(
            list(group_fields) + [
                "total",
                "not_extracted",
                "missed",
                "changed_review",
                "changed_rate_percent"
            ]
        )

        for key in sorted(stats):
            counts = stats[key]

            total = sum(counts.values())

            not_extracted = counts[
                "NOT_EXTRACTED"
            ]

            missed = counts["MISSED"]

            changed = counts[
                "CHANGED_REVIEW"
            ]

            evaluable = total - not_extracted

            rate = (
                changed / evaluable * 100
                if evaluable
                else 0
            )

            writer.writerow(
                list(key) + [
                    total,
                    not_extracted,
                    missed,
                    changed,
                    round(rate, 2)
                ]
            )

    return output_path


summary_paths = [
    write_summary(
        "entity_language_summary_v2.csv",
        ["language", "entity_type"]
    ),
    write_summary(
        "format_language_summary_v2.csv",
        ["language", "format"]
    ),
    write_summary(
        "location_summary_v2.csv",
        ["location"]
    ),
    write_summary(
        "breakdown_results_v2.csv",
        [
            "language",
            "format",
            "entity_type",
            "location"
        ]
    )
]


# ============================================================
# OVERALL RESULTS
# ============================================================

counts = defaultdict(int)

for row in detail_rows:
    counts[row["status"]] += 1

total = len(detail_rows)

not_extracted = counts[
    "NOT_EXTRACTED"
]

missed = counts["MISSED"]

changed = counts[
    "CHANGED_REVIEW"
]

evaluable = total - not_extracted

changed_rate = (
    changed / evaluable * 100
    if evaluable
    else 0
)


# ============================================================
# PRINT SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("OVERALL V2")
print("=" * 70)

print(f"Label files found:       {len(label_files)}")
print(f"Entities evaluated:      {total}")
print(f"Present in original:     {evaluable}")
print(f"Not extracted:           {not_extracted}")
print(f"Unchanged / missed:      {missed}")
print(f"Changed - needs review:  {changed}")
print(f"Changed rate:            {changed_rate:.2f}%")
print(f"Missing result files:    {len(missing_results)}")
print(f"Bad label files:         {len(bad_labels)}")

if missing_results:
    print("\nMissing result files:")
    for item in missing_results[:20]:
        print(" -", item)

if bad_labels:
    print("\nInvalid labels or results:")
    for name, error in bad_labels[:20]:
        print(f" - {name}: {error}")

print("\nOutput files:")
print(detail_path)

for path in summary_paths:
    print(path)

print("\nScrubadub V2 evaluation complete.")

