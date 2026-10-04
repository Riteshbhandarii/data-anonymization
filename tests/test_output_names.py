"""Verify pipeline output naming without running an anonymization algorithm."""

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from pipeline import run_pipeline


def identity_anonymizer(markdown: str) -> str:
    """Keep synthetic text unchanged so tests isolate pipeline file handling."""
    return markdown


class OutputNamesTest(unittest.TestCase):
    def test_same_stem_with_different_formats_has_distinct_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = root / "outputs"
            text_source = root / "report.txt"
            markdown_source = root / "report.md"
            text_source.write_text("Text document", encoding="utf-8")
            markdown_source.write_text("# Markdown document", encoding="utf-8")

            text_result = run_pipeline(
                text_source, str(output_dir), anonymizer=identity_anonymizer
            )
            markdown_result = run_pipeline(
                markdown_source, output_dir, anonymizer=identity_anonymizer
            )

            self.assertEqual(
                text_result.output_path, output_dir / "report.txt_anonymized.md"
            )
            self.assertEqual(
                markdown_result.output_path, output_dir / "report.md_anonymized.md"
            )
            self.assertEqual(
                text_result.output_path.read_text(encoding="utf-8"), "Text document\n"
            )
            self.assertEqual(
                markdown_result.output_path.read_text(encoding="utf-8"),
                "# Markdown document\n",
            )

    def test_repeated_name_preserves_previous_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "report.txt"
            source.write_text("Synthetic input", encoding="utf-8")
            output_dir = root / "outputs"
            returned_text = [
                "First synthetic result", "Second result\n", "Third result: é\n"
            ]
            results = []
            for text in returned_text:
                result = run_pipeline(
                    source, output_dir, anonymizer=lambda markdown, text=text: text
                )
                results.append(result)

            self.assertEqual(
                [result.output_path.name for result in results],
                [
                    "report.txt_anonymized.md",
                    "report.txt_anonymized_2.md",
                    "report.txt_anonymized_3.md",
                ],
            )
            for result, expected_text in zip(results, returned_text):
                self.assertEqual(result.markdown, expected_text)
                self.assertEqual(
                    result.output_path.read_bytes(), expected_text.encode("utf-8")
                )

    def test_concurrent_runs_do_not_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "report.txt"
            source.write_text("Synthetic input", encoding="utf-8")
            output_dir = root / "outputs"
            workers = 8
            ready_to_save = Barrier(workers)

            def run_one(index: int):
                def anonymizer(markdown: str) -> str:
                    ready_to_save.wait(timeout=10)
                    return f"Synthetic result {index}\n"

                return run_pipeline(source, output_dir, anonymizer=anonymizer)

            with ThreadPoolExecutor(max_workers=workers) as executor:
                results = list(executor.map(run_one, range(workers)))

            self.assertEqual(len({result.output_path for result in results}), workers)
            self.assertEqual(len(list(output_dir.glob("*.md"))), workers)
            for index, result in enumerate(results):
                self.assertEqual(
                    result.output_path.read_text(encoding="utf-8"),
                    f"Synthetic result {index}\n",
                )


if __name__ == "__main__":
    unittest.main()
