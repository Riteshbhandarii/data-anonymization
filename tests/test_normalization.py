"""Preserve Markdown hard breaks when preparing text for anonymization."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from pipeline import normalize_markdown, run_pipeline


class MarkdownNormalizationTests(unittest.TestCase):
    def test_space_hard_breaks_survive_line_ending_normalization(self):
        for line_ending in ("\n", "\r\n", "\r"):
            for spaces in ("  ", "    "):
                with self.subTest(line_ending=line_ending, spaces=len(spaces)):
                    markdown = f"First line{spaces}{line_ending}Second line"
                    self.assertEqual(
                        normalize_markdown(markdown), f"First line{spaces}\nSecond line\n"
                    )

    def test_backslash_hard_break_is_preserved(self):
        self.assertEqual(
            normalize_markdown("First line\\\r\nSecond line"),
            "First line\\\nSecond line\n",
        )

    def test_content_spacing_survives_at_document_boundaries(self):
        self.assertEqual(
            normalize_markdown("\n\n    Indented code  \n\n"), "    Indented code  \n"
        )

    def test_fenced_code_content_retains_trailing_spaces(self):
        markdown = "```text\n  Indented text  \n```\n"
        self.assertEqual(normalize_markdown(markdown), markdown)

    def test_blank_line_cleanup_does_not_remove_adjacent_hard_breaks(self):
        self.assertEqual(
            normalize_markdown("\n \t\nFirst line  \nSecond line\n\n \n\nParagraph\n\t\n"),
            "First line  \nSecond line\n\nParagraph\n",
        )
        self.assertEqual(normalize_markdown("\r\n \t\r\n"), "")

    def test_pipeline_preserves_hard_breaks_in_module_input_and_saved_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "report.md"
            source.write_bytes(b"First line  \r\nSecond line\r\n")
            processed = "Processed first line  \nProcessed second line\n"
            anonymizer = Mock(return_value=processed)

            result = run_pipeline(source, root / "outputs", anonymizer=anonymizer)

            anonymizer.assert_called_once_with("First line  \nSecond line\n")
            self.assertEqual(result.markdown, processed)
            self.assertEqual(result.output_path.read_bytes(), processed.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
