"""Tests for dependency-free extraction helpers."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import extract_to_markdown


class ExtractorTests(unittest.TestCase):
    def test_csv_is_converted_to_a_markdown_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "people.csv"
            input_path.write_text(
                "name,email\nAlice,alice@example.com\n",
                encoding="utf-8",
            )

            markdown = extract_to_markdown(input_path)

            self.assertEqual(
                "| name | email |\n"
                "| --- | --- |\n"
                "| Alice | alice@example.com |",
                markdown,
            )

    def test_markdown_input_is_read_without_reformatting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "input.md"
            input_path.write_text("# Existing Markdown\n", encoding="utf-8")

            self.assertEqual(
                "# Existing Markdown\n",
                extract_to_markdown(input_path),
            )

    def test_docx_paragraph_and_table_are_extracted(self) -> None:
        from docx import Document

        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "input.docx"
            document = Document()
            document.add_heading("Report", level=1)
            document.add_paragraph("Contact Alice")
            table = document.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "Name"
            table.cell(0, 1).text = "Email"
            table.cell(1, 0).text = "Alice"
            table.cell(1, 1).text = "alice@example.com"
            document.save(input_path)

            markdown = extract_to_markdown(input_path)

            self.assertIn("# Report", markdown)
            self.assertIn("Contact Alice", markdown)
            self.assertIn("| Name | Email |", markdown)

    def test_xlsx_sheet_is_extracted(self) -> None:
        from openpyxl import Workbook

        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "input.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "People"
            sheet.append(["Name", "Email"])
            sheet.append(["Alice", "alice@example.com"])
            workbook.save(input_path)
            workbook.close()

            markdown = extract_to_markdown(input_path)

            self.assertIn("## Sheet: People", markdown)
            self.assertIn("| Alice | alice@example.com |", markdown)

    def test_pptx_slide_is_extracted_without_duplicate_title(self) -> None:
        from pptx import Presentation

        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "input.pptx"
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            slide.shapes.title.text = "Overview"
            slide.placeholders[1].text = "Contact Alice"
            presentation.save(input_path)

            markdown = extract_to_markdown(input_path)

            self.assertEqual(1, markdown.count("Overview"))
            self.assertIn("## Slide 1: Overview", markdown)
            self.assertIn("Contact Alice", markdown)

    def test_pdf_text_layer_is_extracted(self) -> None:
        import pymupdf

        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "input.pdf"
            document = pymupdf.open()
            page = document.new_page()
            page.insert_text((72, 72), "Contact Alice")
            document.save(input_path)
            document.close()

            markdown = extract_to_markdown(input_path)

            self.assertIn("## Page 1", markdown)
            self.assertIn("Contact Alice", markdown)

    def test_pdf_page_without_text_uses_ocr(self) -> None:
        import pymupdf

        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "scan.pdf"
            document = pymupdf.open()
            document.new_page()
            document.save(input_path)
            document.close()

            with patch(
                "pipeline.extractors._ocr_image_bytes",
                return_value="Scanned text",
            ) as ocr:
                markdown = extract_to_markdown(input_path, ocr_language="eng")

            ocr.assert_called_once()
            self.assertIn("Scanned text", markdown)


if __name__ == "__main__":
    unittest.main()
