"""Keep screenshot comparisons explicit about masking and OCR settings."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from eval import screenshot_bench as bench


class ScreenshotBenchmarkTests(unittest.TestCase):
    def test_repository_redactor_receives_default_and_selected_options(self):
        image = Image.new("RGB", (40, 20), "white")
        detector = object()
        for whole_lines, scale in ((False, 1), (True, 2)):
            with self.subTest(whole_lines=whole_lines, scale=scale), \
                    patch.object(bench, "get_method", return_value=detector), \
                    patch.object(bench, "redact_image", return_value=(image, [])) as redact:
                actual, redactor = bench.make_redactor("combined", whole_lines=whole_lines, ocr_scale=scale)
                self.assertIs(detector, actual)
                self.assertIs(image, redactor(image, "fi"))
                redact.assert_called_once_with(image, detector, language="fi", ocr_language="eng+fin",
                                               whole_lines=whole_lines, ocr_scale=scale)

    def test_unsupported_options_are_rejected_before_loading_external_redactor(self):
        with patch.object(bench, "get_method") as load:
            for method in bench.IMAGE_REDACTOR:
                for options in ({"whole_lines": True}, {"ocr_scale": 2}):
                    with self.subTest(method=method, options=options), \
                            self.assertRaisesRegex(ValueError, "repository image redactor"):
                        bench.make_redactor(method, **options)
            load.assert_not_called()

    def test_scaling_does_not_change_reference_or_output_scoring_ocr(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "example.png"
            Image.new("RGB", (40, 20), "white").save(source)
            (root / "text").mkdir()
            (root / "text" / "example.txt").write_text("Public text", encoding="utf-8")
            case = {"source": source, "file": "example.png", "language": "en", "quality": "standard",
                    "entities": [{"type": "PERSON", "value": "Anna"}]}
            detector = SimpleNamespace(detect=lambda text, language: [])
            with patch.object(bench, "image_cases", return_value=[case]), \
                    patch.object(bench, "ocr_words", return_value=[]) as ocr, \
                    patch.object(bench, "make_redactor", return_value=(
                        detector, lambda image, language: image)) as make:
                documents = bench.evaluate(root, ["combined"], whole_lines=True, ocr_scale=3)
            make.assert_called_once_with("combined", whole_lines=True, ocr_scale=3)
            self.assertEqual(2, ocr.call_count)
            for call in ocr.call_args_list:
                self.assertEqual({}, call.kwargs)
                self.assertEqual("eng+fin", call.args[1])
            self.assertEqual("unread", documents[0]["entities"][0]["state"])

    def test_summary_records_the_redactor_and_fixed_scoring_settings(self):
        summary = bench.format_summary([], [], {}, whole_lines=True, ocr_scale=2)
        self.assertIn("Masking: whole OCR lines", summary)
        self.assertIn("Redactor OCR: 2x. Reference and output OCR: 1x", summary)


if __name__ == "__main__":
    unittest.main()
