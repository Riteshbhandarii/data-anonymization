"""Measure extraction recall against the synthetic corpus's JSON labels."""

import argparse
import csv
import json
import re
import unicodedata
from collections.abc import Callable
from pathlib import Path

from .extractors import extract_to_markdown

LOCATIONS = (
    "body", "metadata", "notes", "hidden_sheet", "header", "footer",
    "comment", "tracked_change", "embedded_image",
)


def _normalize(text: str) -> str:
    """Ignore layout whitespace, but retain spelling, case, and punctuation."""
    text = unicodedata.normalize("NFC", text).replace("<br>", " ").replace(r"\|", "|")
    return " ".join(text.split())


def location_ranges(markdown: str, source: Path) -> list[tuple[str, int, int]]:
    """Return source-location ranges in the original Markdown character offsets.

    Only worksheet names/states are read from XLSX, to classify the existing
    section headings. Label values are matched exclusively against Markdown.
    """
    hidden_sheets: set[str] = set()
    if source.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook

        workbook = load_workbook(source, read_only=True)
        try:
            hidden_sheets = {
                sheet.title for sheet in workbook.worksheets if sheet.sheet_state != "visible"
            }
        finally:
            workbook.close()

    ranges: list[tuple[str, int, int]] = []
    location = "body"
    start = offset = 0
    for raw_line in markdown.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        previous = location
        if line == "## Document metadata":
            location = "metadata"
        elif line == "## Document content" or re.match(r"^## (Slide|Page) \d+", line):
            location = "body"
        elif line == "### Speaker notes":
            location = "notes"
        elif line == "### Embedded image text":
            location = "embedded_image"
        elif line == "## Review comments":
            location = "comment"
        elif line == "## Tracked changes":
            location = "tracked_change"
        elif re.match(r"^## (?:First page |Even page )?Header \(section \d+\)$", line, re.IGNORECASE):
            location = "header"
        elif re.match(r"^## (?:First page |Even page )?Footer \(section \d+\)$", line, re.IGNORECASE):
            location = "footer"
        elif line.startswith("## Sheet: "):
            sheet_name = line.removeprefix("## Sheet: ")
            location = "hidden_sheet" if sheet_name in hidden_sheets else "body"
        if location != previous:
            if offset > start:
                ranges.append((previous, start, offset))
            start = offset
        offset += len(raw_line)
    if offset > start:
        ranges.append((location, start, offset))
    return ranges


def _text_by_location(markdown: str, source: Path) -> dict[str, str]:
    """Normalize each actual Markdown region for labelled-value matching."""
    sections: dict[str, list[str]] = {location: [] for location in LOCATIONS}
    for location, start, end in location_ranges(markdown, source):
        sections[location].append(markdown[start:end])

    return {key: _normalize("\n".join(lines)) for key, lines in sections.items()}


def _aggregate(documents: list[dict], dimensions: tuple[str, ...] = ("format",)) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for document in documents:
        for entity in document["entities"]:
            values = {**document, "location": entity["location"]}
            key = tuple(values[dimension] for dimension in dimensions)
            if key not in groups:
                groups[key] = {
                    **dict(zip(dimensions, key)),
                    "documents": set(),
                    "planted": 0,
                    "returned": 0,
                }
            group = groups[key]
            group["documents"].add(document["file"])
            group["planted"] += 1
            group["returned"] += int(entity["returned"])

    rows = []
    for key in sorted(groups):
        row = groups[key]
        row["documents"] = len(row["documents"])
        row["missing"] = row["planted"] - row["returned"]
        row["recall"] = row["returned"] / row["planted"]
        rows.append(row)
    return rows


def _label_files(root: Path) -> list[Path]:
    """Use the generated index when present, excluding stale unindexed files."""
    index = root / "index.csv"
    if not index.is_file():
        return sorted((root / "labels").glob("*.json"))
    with index.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    files = []
    for record in records:
        relative = Path(record["file"])
        label_path = root / "labels" / f"{relative.stem}.json"
        if not label_path.is_file():
            raise ValueError(f"Manifest document has no label file: {record['file']}")
        label = json.loads(label_path.read_text(encoding="utf-8"))
        for field in ("file", "format", "language"):
            if record[field] != label[field]:
                raise ValueError(f"Manifest and label disagree on {field}: {label_path.name}")
        if record.get("quality", "standard") != label.get("quality", "standard"):
            raise ValueError(f"Manifest and label disagree on quality: {label_path.name}")
        if "entities" in record and int(record["entities"]) != len(label["entities"]):
            raise ValueError(f"Manifest and label disagree on entity count: {label_path.name}")
        files.append(label_path)
    return files


def evaluate_corpus(
    corpus_root: str | Path,
    *,
    extractor: Callable[[Path], str] = extract_to_markdown,
    require_locations: tuple[str, ...] = (),
) -> dict:
    """Compare extracted Markdown with each (document, type, value, location) label.

    This evaluates extraction before anonymization. A failed document remains
    in the denominator with all its labels missing, and its error is recorded.
    """
    root = Path(corpus_root).resolve()
    unknown = set(require_locations) - set(LOCATIONS)
    if unknown:
        raise ValueError(f"Unknown required locations: {', '.join(sorted(unknown))}")
    label_files = _label_files(root)
    if not label_files:
        raise ValueError(f"No JSON label files found in {root / 'labels'}")

    documents = []
    seen_files: set[str] = set()
    for label_file in label_files:
        label = json.loads(label_file.read_text(encoding="utf-8"))
        source = (root / label["file"]).resolve()
        if not source.is_relative_to(root):
            raise ValueError(f"Label source path leaves the corpus directory: {label_file.name}")
        if label["file"] in seen_files:
            raise ValueError(f"Duplicate labels for document: {label['file']}")
        seen_files.add(label["file"])
        if not label["entities"]:
            raise ValueError(f"No entity labels in {label_file.name}")

        entities = []
        for entity in label["entities"]:
            if entity["location"] not in LOCATIONS:
                raise ValueError(f"Unknown label location: {entity['location']}")
            if not isinstance(entity["value"], str) or not _normalize(entity["value"]):
                raise ValueError(f"Empty or invalid label value in {label_file.name}")
            entities.append({**entity, "returned": False})

        document = {
            "file": label["file"],
            "format": label["format"],
            "language": label["language"],
            "quality": label.get("quality", "standard"),
            "entities": entities,
            "error": None,
        }
        try:
            markdown = extractor(source)
            if not isinstance(markdown, str):
                raise TypeError("The extractor must return a Markdown string")
            location_text = _text_by_location(markdown, source)
            for entity in entities:
                entity["returned"] = _normalize(entity["value"]) in location_text[entity["location"]]
        except Exception as exc:  # noqa: BLE001 - Keep failed documents in the recall denominator.
            document["error"] = f"{type(exc).__name__}: {exc}"
        documents.append(document)

    observed = {entity["location"] for doc in documents for entity in doc["entities"]}
    coverage = [
        {"location": location, "required": location in require_locations,
         "status": "covered" if location in observed else "not tested"}
        for location in LOCATIONS
    ]

    return {
        "metric": "location-aware labelled-value recall before anonymization",
        "corpus_root": str(root),
        "documents": documents,
        "by_format": _aggregate(documents),
        "by_location": _aggregate(documents, ("format", "location")),
        "by_quality": _aggregate(documents, ("format", "quality", "location")),
        "coverage": coverage,
        "missing_required_locations": sorted(set(require_locations) - observed),
    }


def format_summary(report: dict) -> str:
    """Render the result table for the PR and the GitHub Actions job summary."""
    lines = [
        "# Extraction recall", "",
        f"Documents: {len(report['documents'])}. Metric: {report['metric']}.", "",
        "A returned label must occur in the Markdown section for its recorded location.",
        "Matching normalizes whitespace and Unicode NFC; it keeps spelling and case.", "",
        "| Format | Documents | Planted | Returned | Missing | Recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["by_format"]:
        lines.append(
            f"| {row['format']} | {row['documents']} | {row['planted']} | "
            f"{row['returned']} | {row['missing']} | {row['recall']:.2%} |"
        )
    planted = sum(row["planted"] for row in report["by_format"])
    returned = sum(row["returned"] for row in report["by_format"])
    lines.append(
        f"| **Total** | **{len(report['documents'])}** | **{planted}** | "
        f"**{returned}** | **{planted - returned}** | **{returned / planted:.2%}** |"
    )
    lines.extend([
        "", "## By location", "",
        "| Format | Location | Planted | Returned | Missing | Recall |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for row in report["by_location"]:
        lines.append(
            f"| {row['format']} | {row['location']} | {row['planted']} | "
            f"{row['returned']} | {row['missing']} | {row['recall']:.2%} |"
        )
    lines.extend([
        "", "## By quality and location", "",
        "| Format | Quality | Location | Planted | Returned | Missing | Recall |",
        "|---|---|---|---:|---:|---:|---:|",
    ])
    for row in report["by_quality"]:
        lines.append(
            f"| {row['format']} | {row['quality']} | {row['location']} | {row['planted']} | "
            f"{row['returned']} | {row['missing']} | {row['recall']:.2%} |"
        )
    lines.extend(["", "## Location coverage", "",
                  "| Location | Required | Coverage |", "|---|---|---|"])
    for row in report["coverage"]:
        status = "Covered" if row["status"] == "covered" else "N/A — no labels; not tested"
        lines.append(f"| {row['location']} | {'Yes' if row['required'] else 'No'} | {status} |")
    if report["missing_required_locations"]:
        lines.extend(["", "Missing required coverage: " + ", ".join(report["missing_required_locations"]) + "."])
    if "thresholds" in report:
        thresholds = report["thresholds"]
        qualities = ", ".join(thresholds["qualities"]) or "all observed qualities"
        locations = ", ".join(thresholds.get("locations", [])) or "all observed locations"
        lines.extend([
            "", "## Acceptance criteria", "",
            f"Minimum recall: {thresholds['min_recall']:.2%}; gated qualities: {qualities}.",
            f"Gated locations: {locations}.",
            ("Other quality/location groups remain in every report but do not gate recall. Extraction errors and "
             "missing required locations always fail."),
        ])
    errors = [document for document in report["documents"] if document["error"]]
    if errors:
        lines.extend(["", "## Extraction errors", ""])
        lines.extend(f"- `{doc['file']}`: {doc['error']}" for doc in errors)
    return "\n".join(lines) + "\n"


def write_reports(report: dict, report_dir: str | Path) -> None:
    """Write aggregate tables and per-label evidence to the requested directory."""
    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("by_format", "by_location", "by_quality"):
        rows = report[name]
        with (destination / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (destination / "details.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "summary.md").write_text(format_summary(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_root", type=Path, help="Generated corpus containing labels/*.json")
    parser.add_argument("--report-dir", type=Path, default=Path("outputs/validation/report"))
    parser.add_argument("--min-recall", type=float, default=1.0, help="Minimum recall for every format/location group")
    parser.add_argument("--ocr-language", default="eng", help="Installed Tesseract languages, e.g. eng+fin")
    parser.add_argument("--require-locations", action="append", default=[],
                        help="Required label locations, comma-separated; can be repeated")
    parser.add_argument("--threshold-qualities", default="all",
                        help="Comma-separated qualities gated by --min-recall; default: all")
    parser.add_argument("--threshold-locations", default="all",
                        help="Comma-separated locations gated by --min-recall; default: all")
    args = parser.parse_args()
    if not 0 <= args.min_recall <= 1:
        parser.error("--min-recall must be between 0 and 1")
    try:
        required = tuple(value.strip() for group in args.require_locations
                         for value in group.split(",") if value.strip())
        report = evaluate_corpus(
            args.corpus_root,
            extractor=lambda source: extract_to_markdown(source, ocr_language=args.ocr_language),
            require_locations=required,
        )
        qualities = tuple(value.strip() for value in args.threshold_qualities.split(",")
                          if value.strip())
        if not qualities:
            raise ValueError("--threshold-qualities must name at least one quality or all")
        if "all" in qualities:
            if len(qualities) != 1:
                raise ValueError("Use all alone in --threshold-qualities")
            qualities = ()
        observed = {document["quality"] for document in report["documents"]}
        if set(qualities) - observed:
            raise ValueError("Unknown or untested threshold qualities: " +
                             ", ".join(sorted(set(qualities) - observed)))
        locations = tuple(value.strip() for value in args.threshold_locations.split(",")
                          if value.strip())
        if not locations:
            raise ValueError("--threshold-locations must name at least one location or all")
        if "all" in locations:
            if len(locations) != 1:
                raise ValueError("Use all alone in --threshold-locations")
            locations = ()
        observed_locations = {row["location"] for row in report["by_location"]}
        if set(locations) - observed_locations:
            raise ValueError("Unknown or untested threshold locations: " +
                             ", ".join(sorted(set(locations) - observed_locations)))
        gated = [row for row in report["by_quality"]
                 if (not qualities or row["quality"] in qualities)
                 and (not locations or row["location"] in locations)]
        if not gated:
            raise ValueError("Threshold quality/location selection covers no labelled groups")
        report["thresholds"] = {"min_recall": args.min_recall, "qualities": list(qualities),
                                "locations": list(locations)}
        write_reports(report, args.report_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Invalid corpus or report destination: {exc}\n")
    print(format_summary(report))
    failed = any(document["error"] for document in report["documents"])
    failed |= any(row["recall"] < args.min_recall for row in gated)
    failed |= bool(report["missing_required_locations"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
