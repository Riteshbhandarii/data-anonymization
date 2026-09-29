"""Check corpus recall, source-location accounting, and CI failure behavior."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline import extract_to_markdown
from pipeline.validation import (
    evaluate_corpus,
    format_summary,
    location_ranges,
    write_reports,
)

REPOSITORY = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "labels").mkdir()

    def add_document(self, text: str, entities: list[dict]) -> None:
        (self.root / "example.txt").write_text(text, encoding="utf-8")
        (self.root / "labels" / "example.json").write_text(
            json.dumps({
                "file": "example.txt", "format": "txt", "language": "en",
                "entities": entities,
            }),
            encoding="utf-8",
        )

    def test_body_occurrence_does_not_satisfy_metadata_label(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
            {"type": "PERSON", "value": "Alex Example", "location": "metadata"},
        ])
        report = evaluate_corpus(self.root)
        self.assertEqual((2, 1), (
            report["by_format"][0]["planted"], report["by_format"][0]["returned"]
        ))
        self.assertEqual(0, next(
            row["returned"] for row in report["by_location"] if row["location"] == "metadata"
        ))

    def test_metadata_occurrence_does_not_satisfy_body_label(self) -> None:
        self.add_document("## Document metadata\n\nAuthor: Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
            {"type": "PERSON", "value": "Alex Example", "location": "metadata"},
        ])
        report = evaluate_corpus(self.root)
        self.assertEqual(0, next(
            row["returned"] for row in report["by_location"] if row["location"] == "body"
        ))

    def test_failed_document_stays_in_denominator(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])

        def broken_reader(path: Path) -> str:
            raise RuntimeError("Reader failed")

        report = evaluate_corpus(self.root, extractor=broken_reader)
        self.assertEqual(1, report["by_format"][0]["planted"])
        self.assertEqual(0, report["by_format"][0]["returned"])
        self.assertIn("Reader failed", report["documents"][0]["error"])

    def test_empty_corpus_cannot_pass(self) -> None:
        with self.assertRaisesRegex(ValueError, "No JSON label files"):
            evaluate_corpus(self.root)

    def test_missing_required_location_is_explicitly_not_tested(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])
        report = evaluate_corpus(self.root, require_locations=("body", "comment"))
        self.assertEqual(["comment"], report["missing_required_locations"])
        self.assertIn("N/A", format_summary(report))
        completed = self.run_cli("--require-locations", "body,comment", "--min-recall", "0")
        self.assertEqual(1, completed.returncode, completed.stderr)

    def test_location_ranges_preserve_original_character_offsets(self) -> None:
        markdown = ("## Document content\r\nBody\r\n## Header (section 1)\r\n# A heading\r\n"
                    "Header Person\r\n## Review comments\r\nComment Person\r\n"
                    "## Tracked changes\r\nRevision Person\r\n")
        ranges = location_ranges(markdown, self.root / "document.docx")
        self.assertEqual(markdown, "".join(markdown[start:end] for _, start, end in ranges))
        self.assertEqual(["body", "header", "comment", "tracked_change"],
                         [location for location, _, _ in ranges])
        for location, start, end in ranges:
            if location == "header":
                self.assertIn("# A heading", markdown[start:end])
                self.assertIn("Header Person", markdown[start:end])

    def test_index_excludes_stale_unindexed_labels(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])
        (self.root / "labels" / "stale.json").write_text("invalid JSON", encoding="utf-8")
        (self.root / "index.csv").write_text(
            "file,format,language,entities\nexample.txt,txt,en,1\n", encoding="utf-8"
        )
        report = evaluate_corpus(self.root)
        self.assertEqual(1, len(report["documents"]))

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "pipeline.validation", str(self.root),
             "--report-dir", str(self.root / "report"), *arguments],
            cwd=REPOSITORY, capture_output=True, text=True, check=False,
        )

    def add_noisy_document(self, *, missing_file: bool = False) -> None:
        if not missing_file:
            (self.root / "noisy.txt").write_text("Garbled text", encoding="utf-8")
        (self.root / "labels" / "noisy.json").write_text(json.dumps({
            "file": "noisy.txt", "format": "txt", "language": "en",
            "quality": "low_resolution", "entities": [
                {"type": "PERSON", "value": "Noisy Person", "location": "body"},
            ],
        }), encoding="utf-8")

    def test_quality_threshold_excludes_noisy_recall_but_reports_it(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])
        self.add_noisy_document()
        self.assertEqual(1, self.run_cli().returncode)
        completed = self.run_cli("--threshold-qualities", "standard")
        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads((self.root / "report" / "details.json").read_text(encoding="utf-8"))
        noisy = next(row for row in report["by_quality"] if row["quality"] == "low_resolution")
        self.assertEqual(0, noisy["recall"])
        self.assertEqual(1, noisy["missing"])

    def test_excluded_quality_extraction_error_still_fails(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])
        self.add_noisy_document(missing_file=True)
        self.assertEqual(1, self.run_cli("--threshold-qualities", "standard").returncode)

    def test_unknown_threshold_quality_cannot_silently_pass(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])
        self.assertEqual(2, self.run_cli("--threshold-qualities", "typo").returncode)

    def test_location_threshold_reports_ocr_miss_without_hiding_it(self) -> None:
        self.add_document("Alex Example\n### Embedded image text\nOCR character error", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
            {"type": "EMAIL", "value": "picture@example.test", "location": "embedded_image"},
        ])
        self.assertEqual(1, self.run_cli().returncode)
        completed = self.run_cli("--threshold-locations", "body", "--require-locations", "embedded_image")
        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads((self.root / "report" / "details.json").read_text(encoding="utf-8"))
        image = next(row for row in report["by_location"] if row["location"] == "embedded_image")
        self.assertEqual((1, 0, 0), (image["planted"], image["returned"], image["recall"]))
        self.assertEqual(["body"], report["thresholds"]["locations"])
        self.assertIn("Gated locations: body", format_summary(report))

    def test_threshold_locations_cannot_hide_errors_or_missing_required_coverage(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])
        missing = self.run_cli("--threshold-locations", "body", "--require-locations", "embedded_image")
        self.assertEqual(1, missing.returncode, missing.stderr)
        self.add_noisy_document(missing_file=True)
        failed = self.run_cli("--threshold-locations", "body", "--threshold-qualities", "standard")
        self.assertEqual(1, failed.returncode, failed.stderr)

    def test_unknown_or_empty_threshold_location_selection_fails(self) -> None:
        self.add_document("Alex Example", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])
        for selection in ("typo", "metadata", "", "all,body"):
            with self.subTest(selection=selection):
                self.assertEqual(2, self.run_cli("--threshold-locations", selection).returncode)

    def test_cli_fails_on_missing_labels_and_still_writes_reports(self) -> None:
        self.add_document("Unrelated content", [
            {"type": "PERSON", "value": "Alex Example", "location": "body"},
        ])
        destination = self.root / "report"
        completed = subprocess.run(
            [sys.executable, "-m", "pipeline.validation", str(self.root),
             "--report-dir", str(destination), "--min-recall", "1.0"],
            cwd=REPOSITORY, capture_output=True, text=True, check=False,
        )
        self.assertEqual(1, completed.returncode, completed.stderr)
        self.assertEqual(
            {"summary.md", "by_format.csv", "by_location.csv", "by_quality.csv", "details.json"},
            {path.name for path in destination.iterdir()},
        )
        details = json.loads((destination / "details.json").read_text(encoding="utf-8"))
        self.assertFalse(details["documents"][0]["entities"][0]["returned"])


class GeneratedCorpusTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("tesseract"), "Generated embedded images require Tesseract")
    def test_generated_non_ocr_labels_reach_locations_and_ocr_is_reported(self) -> None:
        """Gate text extraction; OCR quality is measured separately on all pixels."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = subprocess.run(
                [sys.executable, str(REPOSITORY / "corpus" / "generate.py"),
                 "--out", str(root), "--n", "1", "--seed", "42"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            report = evaluate_corpus(
                root, extractor=lambda path: extract_to_markdown(path, "eng+fin"),
                require_locations=("header", "footer", "comment", "tracked_change", "embedded_image"),
            )
            self.assertEqual(14, len(report["documents"]))
            self.assertEqual(
                {"docx", "pptx", "xlsx", "pdf", "csv", "png"},
                {row["format"] for row in report["by_format"]},
            )
            for document in report["documents"]:
                with self.subTest(file=document["file"]):
                    self.assertIsNone(document["error"])
                    if document["quality"] == "standard":
                        self.assertEqual([], [
                            entity for entity in document["entities"]
                            if entity["location"] != "embedded_image" and not entity["returned"]
                        ])
            self.assertEqual([], report["missing_required_locations"])
            write_reports(report, root / "report")
            self.assertIn("100.00%", (root / "report" / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
