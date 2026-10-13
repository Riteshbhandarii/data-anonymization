import json
from pathlib import Path
from collections import defaultdict

TEST_FILES = [
    ("bench_final", "docx", "en_docx_00"),
    ("bench_final", "docx", "fi_docx_00"),
    ("bench_final_detection", "pdf", "en_pdf_00"),
    ("bench_final_detection", "pdf", "fi_pdf_00"),
    ("bench_final_detection", "xlsx", "en_xlsx_00"),
    ("bench_final_detection", "xlsx", "fi_xlsx_00"),
    ("bench_final_detection", "pptx", "en_pptx_00"),
    ("bench_final_detection", "pptx", "fi_pptx_00"),
    ("bench_final", "csv", "en_csv_00"),
    ("bench_final", "csv", "fi_csv_00"),
]

TYPE_MAP = {
    "PERSON": {"PERSON_NAME"},
    "EMAIL": {"EMAIL_ADDRESS"},
    "PHONE": {"PHONE_NUMBER"},
    "ADDRESS": {"STREET_ADDRESS", "LOCATION"},
    "COMPANY": {"ORGANIZATION_NAME"},
    "IBAN": {"IBAN_CODE"},
    "PERSONAL_ID": {"FINNISH_NATIONAL_ID"},
    "PLATE": {"VEHICLE_IDENTIFICATION_NUMBER", "LICENSE_PLATE"},
    "DATE": {"DATE", "DATE_OF_BIRTH"},
    "INVOICE": {"INVOICE_NUMBER"},
}


def normalize(text):
    return "".join(str(text).casefold().split())


def evaluate_entity(entity, findings):
    expected = normalize(entity["value"])
    expected_types = TYPE_MAP.get(entity["type"], set())

    full_matches = []
    partial_matches = []

    for finding in findings:
        detected = normalize(finding.get("quote", ""))
        detected_type = finding.get("info_type", {}).get("name", "")

        if not detected:
            continue

        if expected in detected or detected == expected:
            full_matches.append(detected_type)

        elif detected in expected and len(detected) >= 3:
            partial_matches.append(detected_type)

    if full_matches:
        type_correct = any(
            detected_type in expected_types
            for detected_type in full_matches
        )

        return "full", type_correct

    if partial_matches:
        return "partial", False

    return "missed", False


def main():
    totals = defaultdict(lambda: {
        "full": 0,
        "partial": 0,
        "missed": 0,
        "type_correct": 0,
        "total": 0,
    })

    details = []

    for root, fmt, stem in TEST_FILES:
        label_path = Path(root) / "labels" / f"{stem}.json"
        result_path = Path("commercial_google_results/raw") / f"{stem}.json"

        with label_path.open(encoding="utf-8") as f:
            labels = json.load(f)

        with result_path.open(encoding="utf-8") as f:
            data = json.load(f)

        findings = data.get("result", {}).get("findings", [])

        language = stem[:2]

        for entity in labels["entities"]:
            if entity.get("location") != "body":
                continue

            coverage, type_correct = evaluate_entity(entity, findings)

            detail = {
                "file": stem,
                "format": fmt,
                "language": language,
                "entity_type": entity["type"],
                "value": entity["value"],
                "coverage": coverage,
                "type_correct": type_correct,
            }

            details.append(detail)

            for key in ["overall", f"format:{fmt}", f"language:{language}"]:
                totals[key]["total"] += 1
                totals[key][coverage] += 1

                if type_correct:
                    totals[key]["type_correct"] += 1

    print("\nGOOGLE DLP DETECTION SCORES")
    print("=" * 75)

    for key, result in totals.items():
        total = result["total"]
        full = result["full"]
        partial = result["partial"]
        missed = result["missed"]
        correct = result["type_correct"]

        print(
            f"{key:<18} "
            f"Total={total:<3} "
            f"Full={full:<3} "
            f"Partial={partial:<3} "
            f"Missed={missed:<3} "
            f"Coverage={full / total * 100:.2f}% "
            f"TypeAware={correct / total * 100:.2f}%"
        )

    output_path = Path("commercial_google_results/scores.json")

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": dict(totals),
                "details": details,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()