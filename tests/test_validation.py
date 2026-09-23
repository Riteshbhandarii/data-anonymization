"""Check corpus recall, source-location accounting, and CI failure behavior."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline.validation import evaluate_corpus, write_reports

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
            {"summary.md", "by_format.csv", "by_location.csv", "details.json"},
            {path.name for path in destination.iterdir()},
        )
        details = json.loads((destination / "details.json").read_text(encoding="utf-8"))
        self.assertFalse(details["documents"][0]["entities"][0]["returned"])


class GeneratedCorpusTests(unittest.TestCase):
    def test_every_generated_label_reaches_its_markdown_location(self) -> None:
        """Exercise actual generator documents, not stand-ins for the readers."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = subprocess.run(
                [sys.executable, str(REPOSITORY / "corpus" / "generate.py"),
                 "--out", str(root), "--n", "1", "--seed", "42"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            report = evaluate_corpus(root)
            self.assertEqual(10, len(report["documents"]))
            self.assertEqual(
                {"docx", "pptx", "xlsx", "pdf", "csv"},
                {row["format"] for row in report["by_format"]},
            )
            for document in report["documents"]:
                with self.subTest(file=document["file"]):
                    self.assertIsNone(document["error"])
                    self.assertEqual([], [
                        entity for entity in document["entities"] if not entity["returned"]
                    ])
            write_reports(report, root / "report")
            self.assertIn("100.00%", (root / "report" / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
