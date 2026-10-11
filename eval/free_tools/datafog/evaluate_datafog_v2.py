
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
RESULTS_DIR = BASE_DIR / "datafog_results"
OUTPUT_DIR = BASE_DIR / "datafog_evaluation_v2"

OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================
# NORMALIZATION
# ============================================================

def normalize(text):
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip().casefold()


# ============================================================
# READ ORIGINAL AND ANONYMIZED TEXT
# ============================================================

def read_sections(result_path):
    text = result_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    def section(start_marker, end_marker):
        start_pattern = (
            rf"(?m)^ORIGINAL\s*$"
            if start_marker == "ORIGINAL"
            else rf"(?m)^{re.escape(start_marker)}\s*$"
        )

        match = re.search(start_pattern, text)

        if not match:
            raise ValueError(
                f"Missing section: {start_marker}"
            )

        remainder = text[match.end():]

        end_match = re.search(
            rf"(?m)^{re.escape(end_marker)}\s*$",
            remainder
        )

        if not end_match:
            raise ValueError(
                f"Missing section: {end_marker}"
            )

        content = remainder[:end_match.start()]

        # Remove separator-only lines
        content = re.sub(
            r"(?m)^\s*=+\s*$",
            "",
            content
        )

        return content.strip()

    original = section(
        "ORIGINAL",
        "ANONYMIZED BY DATAFOG"
    )

    anonymized = section(
        "ANONYMIZED BY DATAFOG",
        "DATAFOG FINDINGS"
    )

    return original, anonymized


# ============================================================
# CLASSIFY EACH LABEL
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
# MAIN EVALUATION
# ============================================================

detail_rows = []
missing_results = []
bad_labels = []

label_files = sorted(LABELS_DIR.glob("*.json"))

print("=" * 70)
print("DATAFOG EVALUATION V2")
print("=" * 70)
print(f"Found {len(label_files)} label files.")

if not label_files:
    raise SystemExit("ERROR: No JSON labels found.")

for index, label_path in enumerate(label_files, start=1):
    print(
        f"[{index}/{len(label_files)}] "
        f"Evaluating {label_path.name}"
    )

    try:
        label = json.loads(
            label_path.read_text(encoding="utf-8")
        )

        original_file = label["file"]
        language = label.get("language", "unknown").lower()
        file_format = label.get("format", "unknown").lower()

        result_path = (
            RESULTS_DIR
            / f"{Path(original_file).stem}_datafog_result.txt"
        )

        if not result_path.exists():
            missing_results.append(original_file)
            continue

        original, anonymized = read_sections(result_path)

        for entity in label.get("entities", []):
            value = str(entity.get("value", "")).strip()

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
                ).upper(),
                "location": str(
                    entity.get("location", "unknown")
                ).lower(),
                "value": value,
                "status": status
            })

    except Exception as error:
        bad_labels.append(
            (label_path.name, str(error))
        )


# ============================================================
# WRITE DETAILED RESULTS
# ============================================================

detail_path = OUTPUT_DIR / "entity_level_results_v2.csv"

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
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(detail_rows)


# ============================================================
# SUMMARIES
# ============================================================

def write_summary(filename, group_fields):
    stats = defaultdict(
        lambda: defaultdict(int)
    )

    for row in detail_rows:
        key = tuple(row[field] for field in group_fields)
        stats[key][row["status"]] += 1

    path = OUTPUT_DIR / filename

    with path.open(
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

            not_extracted = counts["NOT_EXTRACTED"]
            missed = counts["MISSED"]
            changed = counts["CHANGED_REVIEW"]

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

    return path


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
        ["language", "format", "entity_type", "location"]
    )
]


# ============================================================
# FINAL SUMMARY
# ============================================================

counts = defaultdict(int)

for row in detail_rows:
    counts[row["status"]] += 1

total = len(detail_rows)
not_extracted = counts["NOT_EXTRACTED"]
missed = counts["MISSED"]
changed = counts["CHANGED_REVIEW"]
evaluable = total - not_extracted

changed_rate = (
    changed / evaluable * 100
    if evaluable
    else 0
)

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
    print("\nMissing results:")
    for item in missing_results[:20]:
        print(" -", item)

if bad_labels:
    print("\nInvalid labels or result sections:")
    for name, error in bad_labels[:20]:
        print(f" - {name}: {error}")

print("\nOutput files:")
print(detail_path)

for path in summary_paths:
    print(path)

print("\nEvaluation V2 complete.")
