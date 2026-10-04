"""Compare one detector on saved body text and actual documents through the pipeline."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import unicodedata
from pathlib import Path

from detect import PresidioDetector
from eval.bench import MODEL_SETS, THRESHOLD, TYPE_MAP, fingerprint, manifest
from pipeline import run_pipeline
from pipeline.extractors import extract_to_markdown
from pipeline.normalization import normalize_markdown
from redact import PipelineAnonymizer, validate_spans


def normalized_offsets(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Normalize matching whitespace/NFC while retaining original character ranges.

    The detector sees the original Markdown. This mapping is used only to find
    labelled values; its offsets always point back into that detector input.
    """
    characters = []
    offsets = []
    index = 0
    while index < len(text):
        start = index
        if text.startswith("<br>", index):
            chunk, index = " ", index + 4
        elif text.startswith(r"\|", index):
            chunk, index = "|", index + 2
        else:
            index += 1
            while index < len(text) and unicodedata.combining(text[index]):
                index += 1
            chunk = unicodedata.normalize("NFC", text[start:index])
        for character in chunk:
            if character.isspace():
                if characters and characters[-1] == " ":
                    offsets[-1] = (offsets[-1][0], index)
                else:
                    characters.append(" ")
                    offsets.append((start, index))
            else:
                characters.append(character)
                offsets.append((start, index))
    return "".join(characters), offsets


def occurrences(text: str, value: str, ranges: list[tuple[str, int, int]], location: str) -> list[tuple[int, int]]:
    """Find every value occurrence in its labelled region, with global offsets."""
    needle = normalized_offsets(value)[0].strip()
    if not needle:
        raise ValueError("Label values must not be empty")
    matches = []
    for section, start, end in ranges:
        if section != location:
            continue
        normalized, offsets = normalized_offsets(text[start:end])
        position = normalized.find(needle)
        while position >= 0:
            matches.append((start + offsets[position][0], start + offsets[position + len(needle) - 1][1]))
            position = normalized.find(needle, position + 1)
    return matches


def score_label(text: str, entity: dict, spans: list, ranges: list[tuple[str, int, int]], *, expected: int = 1) -> dict:
    """Require a correctly typed span to cover every character of every occurrence."""
    matches = occurrences(text, entity["value"], ranges, entity["location"])
    relevant = [span for span in spans if TYPE_MAP.get(span.entity_type) == entity["type"]]
    states = []
    for start, end in matches:
        if any(span.start <= start and span.end >= end for span in relevant):
            states.append("whole")
        elif any(span.start < end and span.end > start for span in relevant):
            states.append("partial")
        else:
            states.append("missed")
    missing = max(0, expected - len(matches))
    whole = bool(states) and not missing and all(state == "whole" for state in states)
    return {
        **entity,
        "expected_occurrences_minimum": expected,
        "extracted": bool(matches),
        "extraction_incomplete": bool(missing),
        "whole": whole,
        "partial": not whole and any(state != "missed" for state in states),
        "occurrences": [{"start": start, "end": end, "detection": state}
                        for (start, end), state in zip(matches, states, strict=True)],
        "missing_occurrences_minimum": missing,
    }


def aggregate(documents: list[dict], dimensions: tuple[str, ...]) -> list[dict]:
    """Summarize label recall separately from individual occurrence coverage."""
    groups = {}
    for document in documents:
        for stage, entities in document["scores"].items():
            for entity in entities:
                attributes = {**document, **entity, "stage": stage}
                key = tuple(attributes[name] for name in dimensions)
                row = groups.setdefault(key, {
                    **{name: attributes[name] for name in dimensions},
                    "labels": 0, "extracted": 0, "extraction_incomplete": 0,
                    "whole": 0, "partial": 0, "occurrences": 0,
                    "whole_occurrences": 0, "partial_occurrences": 0,
                    "missed_occurrences": 0, "missing_occurrences_minimum": 0,
                })
                row["labels"] += 1
                for field in ("extracted", "extraction_incomplete", "whole", "partial", "missing_occurrences_minimum"):
                    row[field] += int(entity[field])
                row["occurrences"] += len(entity["occurrences"])
                for occurrence in entity["occurrences"]:
                    row[f"{occurrence['detection']}_occurrences"] += 1
    for row in groups.values():
        row["missed"] = row["labels"] - row["whole"] - row["partial"]
        row["whole_recall"] = row["whole"] / row["labels"]
    return [groups[key] for key in sorted(groups)]


def _validate_label(label: dict, source: Path) -> None:
    if not label.get("entities"):
        raise ValueError(f"No entities in labels for {source.name}")
    from pipeline.validation import LOCATIONS

    for entity in label["entities"]:
        if entity.get("location") not in LOCATIONS:
            raise ValueError(f"Unknown entity location: {entity.get('location')}")
        if not isinstance(entity.get("value"), str) or not entity["value"].strip():
            raise ValueError("Entity labels need a nonempty value")
        if not isinstance(entity.get("type"), str) or not entity["type"]:
            raise ValueError("Entity labels need a type")


def evaluate_pipeline(
    corpus_root: str | Path,
    detector,
    *,
    extractor=None,
    ocr_language: str = "eng",
    output_dir: str | Path = "outputs/evaluation/anonymized",
) -> dict:
    """Run extraction, normalization, detection, replacement and output on each file.

    The same detector instance is used on saved body text and normalized
    document extraction. All source labels remain in the full-path denominator,
    including extraction failures. Body comparison uses identical labels.
    """
    from pipeline.validation import location_ranges

    root = Path(corpus_root).resolve()
    stems = manifest(root)
    if not stems or len(stems) != len(set(stems)):
        raise ValueError("Corpus manifest must contain distinct documents")
    provenance = json.loads((root / "corpus.json").read_text(encoding="utf-8"))
    digest = fingerprint(root, stems)
    if digest != provenance.get("corpus_sha256"):
        raise ValueError("Corpus labels/text do not match their recorded fingerprint")
    documents = []
    source_digest = hashlib.sha256()
    for stem in stems:
        # A manifest entry is a basename; reject traversal before reading files.
        if stem != Path(stem).name or not re.fullmatch(r"[\w.-]+", stem):
            raise ValueError(f"Invalid corpus document stem: {stem}")
        label = json.loads((root / "labels" / f"{stem}.json").read_text(encoding="utf-8"))
        source = (root / label["file"]).resolve()
        if not source.is_relative_to(root):
            raise ValueError("Document path leaves the corpus")
        _validate_label(label, source)
        errors = []
        source_sha256 = None
        source_status = "readable"
        try:
            source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        except OSError as exc:
            # Missing or unreadable physical files are pipeline failures, not
            # permission to remove their labels from the report denominator.
            source_status = "missing" if isinstance(exc, FileNotFoundError) else "unreadable"
            errors.append(f"source_file: {type(exc).__name__}: {exc}")
        source_digest.update(f"{label['file']}\0{source_sha256 or source_status}\n".encode())
        body_text = (root / "text" / f"{stem}.txt").read_text(encoding="utf-8")
        body_labels = [entity for entity in label["entities"] if entity["location"] == "body"]
        body_ranges = [("body", 0, len(body_text))]
        expected = {id(entity): max(1, len(occurrences(body_text, entity["value"], body_ranges, "body")))
                    for entity in body_labels}
        try:
            body_spans = validate_spans(body_text, detector.detect(body_text, language=label["language"]))
        except Exception as exc:  # noqa: BLE001 - Keep detector failures in the denominator.
            body_spans = []
            errors.append(f"detector_only: {type(exc).__name__}: {exc}")
        captured = {"text": ""}

        def tracked_extractor(path, captured=captured):
            raw = extract_to_markdown(path, ocr_language=ocr_language) if extractor is None else extractor(path)
            captured["text"] = normalize_markdown(raw)
            return raw

        anonymizer = PipelineAnonymizer(detector, language=label["language"])
        output_path = None
        try:
            result = run_pipeline(source, output_dir, extractor=tracked_extractor, anonymizer=anonymizer)
            output_path = str(result.output_path)
        except Exception as exc:  # noqa: BLE001 - Keep failed files in full-path results.
            errors.append(f"full_pipeline: {type(exc).__name__}: {exc}")
        markdown = captured["text"]
        regions = location_ranges(markdown, source) if markdown else []
        scores = {
            "detector_only": [score_label(body_text, entity, body_spans, body_ranges, expected=expected[id(entity)])
                              for entity in body_labels],
            "full_pipeline": [score_label(markdown, entity, anonymizer.last_spans, regions,
                                          expected=expected.get(id(entity), 1)) for entity in label["entities"]],
        }
        documents.append({"file": label["file"], "format": label["format"], "language": label["language"],
                          "quality": label.get("quality", "standard"),
                          "source_sha256": source_sha256, "source_status": source_status,
                          "output_path": output_path,
                          "errors": errors, "scores": scores})
    versions = {}
    for package in ("presidio-analyzer", "presidio-anonymizer", "spacy", *MODEL_SETS["sm"].values(),
                    "python-docx", "openpyxl", "python-pptx", "pymupdf", "pytesseract"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {
        "metric": "location-aware, type-aware whole-value coverage of every observed occurrence",
        "scope": "Detector-only uses body labels; full pipeline uses all locations. Missing extraction is never a detection success.",
        "occurrence_scope": "Body source occurrence counts come from saved generator text. Other locations have a minimum of one per label; every extracted occurrence is scored.",
        "corpus": provenance, "corpus_root": str(root), "source_artifacts_sha256": source_digest.hexdigest(),
        "detector": type(detector).__name__, "score_threshold": getattr(detector, "score_threshold", None),
        "models": MODEL_SETS["sm"] if isinstance(detector, PresidioDetector) else {}, "versions": versions,
        "python_version": platform.python_version(),
        "extractor": "pipeline.extractors.extract_to_markdown" if extractor is None else getattr(extractor, "__name__", type(extractor).__name__),
        "ocr_language": ocr_language if extractor is None else None,
        "documents": documents,
        "by_format": aggregate(documents, ("stage", "format")),
        "by_location": aggregate(documents, ("stage", "format", "location")),
        "by_type": aggregate(documents, ("stage", "language", "type")),
        "by_quality": aggregate(documents, ("stage", "format", "quality")),
        "body_comparison": [row for row in aggregate(documents, ("stage", "location")) if row["location"] == "body"],
    }


def format_report(report: dict) -> str:
    lines = ["# Full pipeline benchmark", "", report["scope"], "", report["occurrence_scope"], "",
             "## Same body-label denominator", "",
             "| Stage | Labels | Whole | Partial | Missed | Whole recall |",
             "|---|---:|---:|---:|---:|---:|"]
    for row in report["body_comparison"]:
        lines.append(f"| {row['stage']} | {row['labels']} | {row['whole']} | {row['partial']} | {row['missed']} | {row['whole_recall']:.2%} |")
    lines.extend(["", "## By format and location", "",
                  "| Stage | Format | Location | Labels | Extracted | Whole | Partial | Whole recall |",
                  "|---|---|---|---:|---:|---:|---:|---:|"])
    for row in report["by_location"]:
        lines.append(f"| {row['stage']} | {row['format']} | {row['location']} | {row['labels']} | {row['extracted']} | {row['whole']} | {row['partial']} | {row['whole_recall']:.2%} |")
    errors = [(document["file"], error) for document in report["documents"] for error in document["errors"]]
    lines.extend(["", f"Document/stage errors: {len(errors)}.", "",
                  "CSV and JSON also separate whole, partial, missed and missing occurrences.",
                  "A successful command means evaluation completed, not that all PII was detected."])
    lines.extend(f"- `{name}`: {error}" for name, error in errors)
    return "\n".join(lines) + "\n"


def write_reports(report: dict, destination: str | Path) -> None:
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    for name in ("by_format", "by_location", "by_type", "by_quality", "body_comparison"):
        rows = report[name]
        with (output / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
            if rows:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    (output / "details.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "summary.md").write_text(format_report(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_root", type=Path)
    parser.add_argument("--report-dir", type=Path, default=Path("outputs/evaluation/pipeline"))
    parser.add_argument("--score-threshold", type=float, default=THRESHOLD)
    parser.add_argument("--ocr-language", default="eng", help="Installed Tesseract language(s), for example eng+fin")
    args = parser.parse_args()
    try:
        report = evaluate_pipeline(args.corpus_root, PresidioDetector(score_threshold=args.score_threshold),
                                   ocr_language=args.ocr_language, output_dir=args.report_dir / "anonymized")
        write_reports(report, args.report_dir)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Cannot evaluate corpus: {exc}\n")
    print(format_report(report))
    return 1 if any(document["errors"] for document in report["documents"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
