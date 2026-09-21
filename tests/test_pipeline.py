"""Tests for the end-to-end Markdown pipeline."""

import tempfile
import unittest
from pathlib import Path

from pipeline import UnsupportedFormatError, baseline_anonymize, run_pipeline
from pipeline.normalization import normalize_markdown


class PipelineTests(unittest.TestCase):
    def test_text_file_is_anonymized_twice_and_saved(self) -> None:
        calls: list[str] = []

        def test_anonymizer(markdown: str) -> str:
            calls.append(markdown)
            return markdown.replace("Alice", "[PERSON_REDACTED]")

        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            input_path = root / "example.txt"
            output_dir = root / "outputs"
            input_path.write_text("Contact Alice.\n", encoding="utf-8")

            result = run_pipeline(
                input_path,
                output_dir=output_dir,
                anonymizer=test_anonymizer,
            )

            self.assertEqual(2, len(calls))
            self.assertEqual("Contact [PERSON_REDACTED].\n", result.markdown)
            self.assertEqual(result.markdown, result.output_path.read_text(encoding="utf-8"))
            self.assertEqual("example_anonymized.md", result.output_path.name)

    def test_baseline_anonymizer_redacts_structured_identifiers(self) -> None:
        source = "Email alice@example.com from 192.168.1.20."
        result = baseline_anonymize(source)

        self.assertEqual(
            "Email [EMAIL_REDACTED] from [IP_ADDRESS_REDACTED].",
            result,
        )

    def test_unsupported_extension_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "example.bin"
            input_path.write_bytes(b"data")

            with self.assertRaises(UnsupportedFormatError):
                run_pipeline(input_path)

    def test_pipeline_requires_at_least_one_anonymization_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "example.txt"
            input_path.write_text("Text", encoding="utf-8")

            with self.assertRaises(ValueError):
                run_pipeline(input_path, anonymization_passes=0)

    def test_markdown_normalization_is_minimal(self) -> None:
        source = "# Title\r\n\r\n\r\nText with spaces   \r\n"
        self.assertEqual("# Title\n\nText with spaces\n", normalize_markdown(source))


if __name__ == "__main__":
    unittest.main()
