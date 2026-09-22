"""Measure extraction recall against the synthetic corpus's JSON labels."""

import argparse
import csv
import json
import re
import unicodedata
from collections.abc import Callable
from pathlib import Path

from .extractors import extract_to_markdown

LOCATIONS = ("body", "metadata", "notes", "hidden_sheet")


def _normalize(text: str) -> str:
    """Ignore layout whitespace, but retain spelling, case, and punctuation."""
    text = unicodedata.normalize("NFC", text).replace("<br>", " ").replace(r"\|", "|")
    return " ".join(text.split())


def _text_by_location(markdown: str, source: Path) -> dict[str, str]:
    """Separate reader output so a body match cannot satisfy a metadata label.

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

    sections: dict[str, list[str]] = {location: [] for location in LOCATIONS}
    location = "body"
    for line in markdown.splitlines():
        if line == "## Document metadata":
            location = "metadata"
        elif line == "### Speaker notes":
            location = "notes"
        elif line.startswith("## Sheet: "):
            sheet_name = line.removeprefix("## Sheet: ")
            location = "hidden_sheet" if sheet_name in hidden_sheets else "body"
        elif re.match(r"^#{1,2} ", line):
            location = "body"
        sections[location].append(line)

    return {key: _normalize("\n".join(lines)) for key, lines in sections.items()}


def _aggregate(documents: list[dict], by_location: bool = False) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for document in documents:
        for entity in document["entities"]:
            key = (document["format"], entity["location"]) if by_location else (document["format"],)
            if key not in groups:
                groups[key] = {
                    "format": document["format"],
                    **({"location": entity["location"]} if by_location else {}),
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


def evaluate_corpus(
    corpus_root: str | Path,
    *,
    extractor: Callable[[Path], str] = extract_to_markdown,
) -> dict:
    """Compare extracted Markdown with each (document, type, value, location) label.

    This evaluates extraction before anonymization. A failed document remains
    in the denominator with all its labels missing, and its error is recorded.
    """
    root = Path(corpus_root).resolve()
    label_files = sorted((root / "labels").glob("*.json"))
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

    return {
        "metric": "location-aware labelled-value recall before anonymization",
        "corpus_root": str(root),
        "documents": documents,
        "by_format": _aggregate(documents),
        "by_location": _aggregate(documents, by_location=True),
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
    errors = [document for document in report["documents"] if document["error"]]
    if errors:
        lines.extend(["", "## Extraction errors", ""])
        lines.extend(f"- `{doc['file']}`: {doc['error']}" for doc in errors)
    return "\n".join(lines) + "\n"


def write_reports(report: dict, report_dir: str | Path) -> None:
    """Write aggregate tables and per-label evidence to the requested directory."""
    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("by_format", "by_location"):
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
    args = parser.parse_args()
    if not 0 <= args.min_recall <= 1:
        parser.error("--min-recall must be between 0 and 1")
    try:
        report = evaluate_corpus(args.corpus_root)
        write_reports(report, args.report_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Invalid corpus or report destination: {exc}\n")
    print(format_summary(report))
    failed = any(document["error"] for document in report["documents"])
    failed |= any(row["recall"] < args.min_recall for row in report["by_location"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
