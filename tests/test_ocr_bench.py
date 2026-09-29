"""Test OCR metrics and failure accounting without downloading OCR models."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from eval.ocr_bench import edit_distance, evaluate, image_cases


class OCRBenchmarkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ("png", "labels", "evidence"):
            (self.root / name).mkdir()
        image = self.root / "png" / "example.png"
        image.write_bytes(b"Synthetic fixture pixels consumed only by a test reader")
        (self.root / "index.csv").write_text(
            "file,format,language,quality\npng/example.png,png,en,clean\n", encoding="utf-8"
        )
        (self.root / "labels" / "example.json").write_text(json.dumps({
            "file": "png/example.png", "format": "png", "language": "en", "quality": "clean",
            "entities": [{"type": "PERSON", "value": "Alex", "location": "body"}],
        }), encoding="utf-8")
        (self.root / "evidence" / "example.json").write_text(json.dumps({
            "document_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
            "images": [{"title": "Contact", "body": ["Alex"]}],
        }), encoding="utf-8")

    def test_character_distance_counts_substitutions_insertions_and_deletions(self):
        self.assertEqual(3, edit_distance("kitten", "sitting"))
        self.assertEqual(3, edit_distance("abc", ""))
        self.assertEqual(0, edit_distance("ä", "ä"))

    def test_reader_receives_only_image_path_and_metrics_use_its_output(self):
        received = []

        def reader(path):
            received.append(path)
            return "Contact\nA1ex"

        report = evaluate(self.root, reader, engine="test")
        self.assertEqual([self.root / "png" / "example.png"], received)
        row = report["summary"][0]
        self.assertEqual(0, row["recall"])
        self.assertEqual(1, row["character_edits"])
        self.assertAlmostEqual(1 / len("Contact Alex"), row["cer"])

    def test_failed_reader_remains_in_denominator(self):
        def reader(path):
            raise RuntimeError("Engine unavailable")

        report = evaluate(self.root, reader, engine="test")
        row = report["summary"][0]
        self.assertEqual(1, row["errors"])
        self.assertEqual(1, row["planted"])
        self.assertEqual(0, row["returned"])
        self.assertEqual(1, row["cer"])

    def test_changed_image_cannot_use_stale_reference(self):
        (self.root / "png" / "example.png").write_bytes(b"Different image")
        with self.assertRaisesRegex(ValueError, "differs from its generated reference"):
            image_cases(self.root)

    def test_empty_identifier_cannot_count_as_a_returned_value(self):
        path = self.root / "labels" / "example.json"
        labels = json.loads(path.read_text(encoding="utf-8"))
        labels["entities"][0]["value"] = " "
        path.write_text(json.dumps(labels), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid standalone-image entity"):
            evaluate(self.root, lambda path: "Contact Alex", engine="test")


if __name__ == "__main__":
    unittest.main()
