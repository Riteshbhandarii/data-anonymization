"""Validate reproducible smoke fixtures and honest results without OCR or models."""

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pymupdf
import reportlab
from PIL import Image

from eval import screenshot_smoke as smoke
from redact.image import Word


class ScreenshotSmokeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.font = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        self.text = "## Page 1\nscan-one@example.test\n## Page 3\nscan-three@example.test\n"
        self.version = self.enterContext(patch.object(
            smoke.pytesseract, "get_tesseract_version", return_value="test-tesseract",
        ))
        self.ocr = self.enterContext(patch.object(smoke, "ocr_words", return_value=[
            Word(text, index * 50, 10, 45, 14, (1, 1, 1))
            for index, text in enumerate(("Alice", "Example", "Väinö", "Mäkinen"))
        ]))
        self.extract = self.enterContext(patch.object(smoke, "extract_to_markdown", return_value=self.text))

    def test_fixture_pixels_and_font_provenance_are_reproducible(self):
        first, second = self.root / "first", self.root / "second"
        rows, scanned = smoke.run_smoke(first, self.font)
        smoke.run_smoke(second, self.font)
        expected = {f"small-{language}-{size}px.png" for language in ("en", "fi") for size in (12, 14)}
        self.assertEqual(expected, {path.name for path in first.glob("*.png")})
        pixels = set()
        for name in sorted(expected):
            with self.subTest(name=name), Image.open(first / name) as left, Image.open(second / name) as right:
                self.assertEqual((640, 140), left.size)
                self.assertEqual(left.size, right.size)
                self.assertEqual(left.tobytes(), right.tobytes())
                self.assertEqual((0, 255), left.convert("L").getextrema())
                pixels.add(hashlib.sha256(left.tobytes()).hexdigest())
        self.assertEqual(4, len(pixels))

        with pymupdf.open(first / "scanned-smoke.pdf") as left, \
                pymupdf.open(second / "scanned-smoke.pdf") as right:
            self.assertEqual(3, len(left))
            self.assertEqual(len(left), len(right))
            for index, page in enumerate(left):
                with self.subTest(page=index):
                    self.assertEqual((500, 150), (page.rect.width, page.rect.height))
                    self.assertEqual("", page.get_text())
                    images = page.get_images()
                    self.assertEqual(1, len(images))
                    embedded = left.extract_image(images[0][0])
                    self.assertEqual((1000, 300), (embedded["width"], embedded["height"]))
                    self.assertEqual(page.get_pixmap().samples, right[index].get_pixmap().samples)
        self.assertEqual([True, True, True], scanned["native_text_empty"])
        expected_hash = hashlib.sha256(self.font.read_bytes()).hexdigest()
        for report in [*rows, scanned]:
            self.assertEqual(str(self.font.resolve()), report["provenance"]["font_file"])
            self.assertEqual(expected_hash, report["provenance"]["font_sha256"])
            self.assertEqual("test-tesseract", report["provenance"]["tesseract"])

    def test_ocr_misses_are_reported_and_detection_is_explicitly_not_run(self):
        output = self.root / "ocr-only"
        rows, scanned = smoke.run_smoke(output, self.font)
        self.assertEqual(8, len(rows))
        self.assertEqual([1, 2] * 4, [call.kwargs["scale"] for call in self.ocr.call_args_list])
        self.assertEqual({("en", 12, 1), ("en", 12, 2), ("fi", 12, 1), ("fi", 12, 2),
                          ("en", 14, 1), ("en", 14, 2), ("fi", 14, 1), ("fi", 14, 2)},
                         {(row["language"], row["font_px"], row["scale"]) for row in rows})
        for row in rows:
            self.assertEqual((1, 2), (row["found"], row["total"]))
            self.assertEqual([True, False], [value["extracted"] for value in row["values"]])
        self.assertEqual([True, False, True], [value["extracted"] for value in scanned["values"]])
        self.assertEqual([None, None, None], [value["detected"] for value in scanned["values"]])
        self.assertIsNone(scanned["method"])
        self.assertEqual("not_run", scanned["detection_status"])
        saved = json.loads((output / "scanned-smoke.json").read_text(encoding="utf-8"))
        self.assertEqual("not_run", saved["detection_status"])
        self.assertTrue(all(value["detected"] is None for value in saved["values"]))
        self.assertEqual(self.text, (output / "scanned-smoke.md").read_text(encoding="utf-8"))

    def test_requested_detector_records_actual_coverage_instead_of_extraction_success(self):
        value = "scan-one@example.test"
        start = self.text.index(value)
        detector = SimpleNamespace(detect=Mock(return_value=[
            SimpleNamespace(start=start, end=start + len(value), entity_type="EMAIL_ADDRESS", score=1.0),
        ]))
        methods = ModuleType("detect.methods")
        methods.get_detector = Mock(return_value=detector)
        with patch.dict(sys.modules, {"detect.methods": methods}):
            _, scanned = smoke.run_smoke(self.root / "detected", self.font, method="combined")
        methods.get_detector.assert_called_once_with("combined")
        detector.detect.assert_called_once_with(self.text, language="en")
        self.assertEqual("combined", scanned["method"])
        self.assertEqual("completed", scanned["detection_status"])
        self.assertEqual([True, False, True], [value["extracted"] for value in scanned["values"]])
        self.assertEqual([True, False, False], [value["detected"] for value in scanned["values"]])

    def test_missing_ocr_runtime_fails_cli_without_publishing_success_reports(self):
        output = self.root / "missing-ocr"
        self.version.side_effect = smoke.pytesseract.TesseractNotFoundError()
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as failure:
            smoke.main(["--out", str(output), "--font", str(self.font)])
        self.assertEqual(2, failure.exception.code)
        self.assertIn("Screenshot smoke could not run", stderr.getvalue())
        self.assertIn("tesseract", stderr.getvalue().lower())
        self.assertFalse((output / "small-text-smoke.json").exists())
        self.assertFalse((output / "scanned-smoke.json").exists())
        self.ocr.assert_not_called()
        self.extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
