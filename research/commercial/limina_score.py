import collections
import json
import unicodedata
from pathlib import Path


RESULT_ROOT = Path("commercial_limina_results")

TESTS = [
    {
        "format": "pdf",
        "language": "en",
        "stem": "en_pdf_00",
        "labels": Path("bench_final_detection/labels/en_pdf_00.json"),
    },
    {
        "format": "pdf",
        "language": "fi",
        "stem": "fi_pdf_00",
        "labels": Path("bench_final_detection/labels/fi_pdf_00.json"),
    },
    {
        "format": "xlsx",
        "language": "en",
        "stem": "en_xlsx_00",
        "labels": Path("bench_final_detection/labels/en_xlsx_00.json"),
    },
    {
        "format": "xlsx",
        "language": "fi",
        "stem": "fi_xlsx_00",
        "labels": Path("bench_final_detection/labels/fi_xlsx_00.json"),
    },
    {
        "format": "pptx",
        "language": "en",
        "stem": "en_pptx_00",
        "labels": Path("bench_final_detection/labels/en_pptx_00.json"),
    },
    {
        "format": "pptx",
        "language": "fi",
        "stem": "fi_pptx_00",
        "labels": Path("bench_final_detection/labels/fi_pptx_00.json"),
    },
    {
        "format": "csv",
        "language": "en",
        "stem": "en_csv_00",
        "labels": Path("bench_final/labels/en_csv_00.json"),
    },
    {
        "format": "csv",
        "language": "fi",
        "stem": "fi_csv_00",
        "labels": Path("bench_final/labels/fi_csv_00.json"),
    },
]


TYPE_MAP = {
    "PERSON": {"NAME"},
    "EMAIL": {"EMAIL_ADDRESS"},
    "PHONE": {"PHONE_NUMBER"},
    "COMPANY": {"ORGANIZATION"},
    "ADDRESS": {
        "LOCATION_ADDRESS",
        "LOCATION_ADDRESS_STREET",
    },
    "IBAN": {"BANK_ACCOUNT"},
    "DATE": {"DATE", "DOB"},
    "PERSONAL_ID": {"SSN"},
    "PLATE": {"VEHICLE_ID"},
    "INVOICE": set(),
}


def normalize(text):
    """
    Normalise text for comparison while preserving punctuation.

    Limina sometimes introduces whitespace inside extracted strings,
    e.g. 'J uha' or 'name@ example.org'. Removing whitespace allows
    those cases to be compared with the corpus ground truth without
    making the comparison overly permissive.
    """
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    return "".join(ch for ch in text if not ch.isspace())


def find_all(haystack, needle):
    start = 0

    while True:
        pos = haystack.find(needle, start)

        if pos == -1:
            break

        yield pos, pos + len(needle)
        start = pos + 1


def score_value(value, entities, accepted_labels=None):
    target = normalize(value)

    if not target:
        return "missed", []

    covered = [False] * len(target)
    matched = []

    for entity in entities:
        label = entity.get("best_label", "")

        if (
            accepted_labels is not None
            and label not in accepted_labels
        ):
            continue

        detected_original = entity.get("text", "")
        detected = normalize(detected_original)

        if not detected:
            continue

        # Detection contains the entire expected value.
        if target in detected:
            matched.append(
                {
                    "label": label,
                    "text": detected_original,
                }
            )

            return "full", matched

        # Detection is a complete substring of the expected value.
        occurrences = list(find_all(target, detected))

        if not occurrences:
            continue

        matched.append(
            {
                "label": label,
                "text": detected_original,
            }
        )

        for start, end in occurrences:
            for i in range(start, end):
                covered[i] = True

    covered_count = sum(covered)

    if covered_count == len(target):
        return "full", matched

    if covered_count > 0:
        return "partial", matched

    return "missed", matched


def make_counter():
    return collections.defaultdict(
        lambda: collections.Counter(
            {
                "total": 0,
                "full": 0,
                "partial": 0,
                "missed": 0,
            }
        )
    )


def add_count(counter, key, result):
    counter[key]["total"] += 1
    counter[key][result] += 1


def run_metric(type_aware):
    overall = make_counter()
    by_format = make_counter()
    by_language = make_counter()
    by_type = make_counter()

    details = []

    for test in TESTS:
        raw_path = (
            RESULT_ROOT
            / "raw"
            / f"{test['stem']}.json"
        )

        with raw_path.open(encoding="utf-8") as f:
            data = json.load(f)

        with test["labels"].open(encoding="utf-8") as f:
            labels = json.load(f)

        entities = data.get("entities", [])

        for expected in labels["entities"]:
            if expected["location"] != "body":
                continue

            expected_type = expected["type"]

            accepted = (
                TYPE_MAP.get(expected_type, set())
                if type_aware
                else None
            )

            result, matched = score_value(
                expected["value"],
                entities,
                accepted_labels=accepted,
            )

            add_count(overall, "ALL", result)
            add_count(
                by_format,
                test["format"].upper(),
                result,
            )
            add_count(
                by_language,
                test["language"].upper(),
                result,
            )
            add_count(
                by_type,
                expected_type,
                result,
            )

            details.append(
                {
                    "file": test["stem"],
                    "format": test["format"],
                    "language": test["language"],
                    "type": expected_type,
                    "value": expected["value"],
                    "result": result,
                    "matched_detections": matched,
                }
            )

    return {
        "overall": overall,
        "by_format": by_format,
        "by_language": by_language,
        "by_type": by_type,
        "details": details,
    }


def print_table(title, counts):
    print(f"\n{title}")

    print(
        f"{'category':<18}"
        f"{'full':>8}"
        f"{'partial':>10}"
        f"{'missed':>9}"
        f"{'total':>8}"
        f"{'rate':>10}"
    )

    for key in sorted(counts):
        row = counts[key]

        total = row["total"]
        full = row["full"]

        rate = 100 * full / total if total else 0

        print(
            f"{str(key):<18}"
            f"{full:>8}"
            f"{row['partial']:>10}"
            f"{row['missed']:>9}"
            f"{total:>8}"
            f"{rate:>9.2f}%"
        )


def serialise_counts(counts):
    return {
        str(key): dict(value)
        for key, value in counts.items()
    }


def main():
    coverage = run_metric(type_aware=False)
    strict = run_metric(type_aware=True)

    print("\n====================================")
    print("LIMINA REDACTION COVERAGE")
    print("Any Limina entity type may cover PII")
    print("====================================")

    print_table(
        "Overall",
        coverage["overall"],
    )

    print_table(
        "By format",
        coverage["by_format"],
    )

    print_table(
        "By language",
        coverage["by_language"],
    )

    print_table(
        "By ground-truth type",
        coverage["by_type"],
    )

    print("\n====================================")
    print("LIMINA TYPE-AWARE DETECTION")
    print("Entity category must also match")
    print("====================================")

    print_table(
        "Overall",
        strict["overall"],
    )

    print_table(
        "By format",
        strict["by_format"],
    )

    print_table(
        "By language",
        strict["by_language"],
    )

    print_table(
        "By ground-truth type",
        strict["by_type"],
    )

    output = {
        "documents_scored": len(TESTS),
        "expected_body_identifiers": 74,
        "scoring_note": (
            "Entity text is compared directly with ground truth after "
            "Unicode normalization and whitespace removal. Punctuation "
            "is preserved. Full coverage may be formed by multiple "
            "Limina detections."
        ),
        "type_mapping": {
            key: sorted(value)
            for key, value in TYPE_MAP.items()
        },
        "coverage": {
            "overall": serialise_counts(
                coverage["overall"]
            ),
            "by_format": serialise_counts(
                coverage["by_format"]
            ),
            "by_language": serialise_counts(
                coverage["by_language"]
            ),
            "by_type": serialise_counts(
                coverage["by_type"]
            ),
            "details": coverage["details"],
        },
        "type_aware": {
            "overall": serialise_counts(
                strict["overall"]
            ),
            "by_format": serialise_counts(
                strict["by_format"]
            ),
            "by_language": serialise_counts(
                strict["by_language"]
            ),
            "by_type": serialise_counts(
                strict["by_type"]
            ),
            "details": strict["details"],
        },
    }

    output_path = RESULT_ROOT / "score_summary.json"

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()