"""Regression coverage for metadata, document stories, image OCR, and formulas."""

import shutil
import unittest
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

from pipeline import ExtractionError, extract_to_markdown


class ExtractionGapTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_docx_metadata_and_all_header_footer_variants(self):
        from docx import Document
        from docx.enum.section import WD_SECTION_START
        from docx.shared import Inches

        document = Document()
        document.add_paragraph("Body Contact")
        document.core_properties.author = "Metadata Author"
        document.core_properties.last_modified_by = "Metadata Editor"
        document.core_properties.keywords = "metadata-only@example.test"
        document.core_properties.comments = "Metadata Comment"
        first = document.sections[0]
        for name in (
            "header", "first_page_header", "even_page_header",
            "footer", "first_page_footer", "even_page_footer",
        ):
            story = getattr(first, name)
            story.paragraphs[0].text = f"Contact in {name}"
            story.add_table(rows=1, cols=1, width=Inches(4)).cell(0, 0).text = (
                f"Table contact in {name}"
            )
        # The second section inherits the same stories and must not repeat them.
        document.add_section(WD_SECTION_START.NEW_PAGE)
        path = self.root / "stories.docx"
        document.save(path)

        markdown = extract_to_markdown(path)
        self.assertIn("## Document metadata", markdown)
        self.assertIn("## Document content", markdown)
        for value in (
            "Body Contact", "Metadata Author", "Metadata Editor",
            "metadata-only@example.test", "Metadata Comment",
        ):
            self.assertIn(value, markdown)
        for name in (
            "header", "first_page_header", "even_page_header",
            "footer", "first_page_footer", "even_page_footer",
        ):
            self.assertEqual(markdown.count(f"Contact in {name}"), 1)
            self.assertEqual(markdown.count(f"Table contact in {name}"), 1)

    def test_pptx_metadata_and_speaker_notes(self):
        from pptx import Presentation

        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = "Body slide"
        slide.notes_slide.notes_text_frame.text = "Notes Contact"
        presentation.core_properties.author = "Slides Author"
        presentation.core_properties.last_modified_by = "Slides Editor"
        presentation.core_properties.keywords = "slides-only@example.test"
        path = self.root / "metadata.pptx"
        presentation.save(path)

        markdown = extract_to_markdown(path)
        for value in (
            "Slides Author", "Slides Editor", "slides-only@example.test",
            "### Speaker notes", "Notes Contact",
        ):
            self.assertIn(value, markdown)

    def test_xlsx_metadata_and_hidden_worksheet(self):
        from openpyxl import Workbook

        workbook = Workbook()
        workbook.active.append(["Visible Contact"])
        hidden = workbook.create_sheet("Private")
        hidden.sheet_state = "hidden"
        hidden.append(["Hidden Contact"])
        workbook.properties.creator = "Workbook Author"
        workbook.properties.lastModifiedBy = "Workbook Editor"
        workbook.properties.keywords = "workbook-only@example.test"
        path = self.root / "metadata.xlsx"
        workbook.save(path)
        workbook.close()

        markdown = extract_to_markdown(path)
        for value in (
            "Workbook Author", "Workbook Editor", "workbook-only@example.test",
            "## Sheet: Private", "Hidden Contact", "Visible Contact",
        ):
            self.assertIn(value, markdown)

    def test_pdf_metadata_and_text_without_unnecessary_ocr(self):
        import pymupdf

        path = self.root / "text.pdf"
        with pymupdf.open() as document:
            document.new_page().insert_text((40, 40), "Visible Contact")
            document.set_metadata({
                "author": "PDF Author",
                "subject": "pdf-only@example.test",
                "keywords": "PDF Keywords",
            })
            document.save(path)

        with patch("pipeline.extractors._ocr_image_bytes") as ocr:
            markdown = extract_to_markdown(path)
        ocr.assert_not_called()
        for value in ("PDF Author", "pdf-only@example.test", "PDF Keywords", "Visible Contact"):
            self.assertIn(value, markdown)

    def _mixed_pdf(self, rotation: int = 0) -> Path:
        import pymupdf

        # Rasterize known text before embedding it; the final PDF has no text
        # objects for this identifier, so it can only be returned through OCR.
        with pymupdf.open() as image_document:
            image_page = image_document.new_page(width=480, height=100)
            image_page.insert_text((20, 60), "image-only@example.test", fontsize=24)
            image_bytes = image_page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")
        path = self.root / "mixed.pdf"
        with pymupdf.open() as document:
            page = document.new_page(width=600, height=400)
            page.insert_text((40, 40), "Visible Contact")
            page.insert_image(pymupdf.Rect(40, 100, 520, 200), stream=image_bytes)
            page.set_rotation(rotation)
            document.save(path)
        return path

    def test_mixed_pdf_ocr_adds_image_text_and_deduplicates_text_layer(self):
        from PIL import Image

        for rotation, size in ((0, (960, 200)), (90, (200, 960))):
            with self.subTest(rotation=rotation):
                path = self._mixed_pdf(rotation)
                with patch(
                    "pipeline.extractors._ocr_image_bytes",
                    return_value="Visible Contact\nimage-only@example.test\nimage-only@example.test",
                ) as ocr:
                    markdown = extract_to_markdown(path, ocr_language="eng")
                ocr.assert_called_once()
                self.assertEqual(ocr.call_args.args[1], "eng")
                with Image.open(BytesIO(ocr.call_args.args[0])) as region:
                    # Only the image region is passed to OCR, not the entire page.
                    self.assertEqual(region.size, size)
                self.assertEqual(markdown.count("Visible Contact"), 1)
                self.assertEqual(markdown.count("image-only@example.test"), 1)

    def test_scanned_pdf_still_uses_full_page_ocr(self):
        import pymupdf

        path = self.root / "scanned.pdf"
        with pymupdf.open() as document:
            document.new_page()
            document.save(path)
        with patch(
            "pipeline.extractors._ocr_image_bytes", return_value="Scanned Contact"
        ) as ocr:
            markdown = extract_to_markdown(path)
        ocr.assert_called_once()
        self.assertIn("Scanned Contact", markdown)

    @unittest.skipUnless(shutil.which("tesseract"), "Tesseract is not installed")
    def test_mixed_pdf_real_ocr_reads_identifier_inside_image(self):
        markdown = extract_to_markdown(self._mixed_pdf())
        self.assertIn("Visible Contact", markdown)
        self.assertIn("image-only@example.test", markdown)

    def _formula_workbook(self) -> Path:
        from openpyxl import Workbook

        workbook = Workbook()
        workbook.active.title = "Contacts"
        workbook.active.append(["Computed name"])
        workbook.active["A2"] = '=CONCAT("Formula", " Contact")'
        path = self.root / "formulas.xlsx"
        workbook.save(path)
        workbook.close()
        return path

    def _set_formula_cache(self, path: Path, value: str, result_type: str = "str"):
        # openpyxl writes formulas but does not calculate their cached values.
        # Patch the OOXML cache to model a workbook saved by Excel/LibreOffice.
        with ZipFile(path) as archive:
            entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
        namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with ZipFile(path, "w") as archive:
            for item, data in entries:
                if item.filename == "xl/worksheets/sheet1.xml":
                    root = ET.fromstring(data)
                    cell = root.find(".//s:c[@r='A2']", namespace)
                    cell.set("t", result_type)
                    cached = cell.find("s:v", namespace)
                    cached.text = value
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                archive.writestr(item, data)

    def test_xlsx_formula_uses_cached_result_instead_of_expression(self):
        path = self._formula_workbook()
        self._set_formula_cache(path, "Formula Contact")
        markdown = extract_to_markdown(path)
        self.assertIn("Formula Contact", markdown)
        self.assertNotIn("CONCAT", markdown)

    def test_xlsx_formula_without_cache_fails_with_cell_context(self):
        path = self._formula_workbook()
        with self.assertRaisesRegex(ExtractionError, "Contacts.*A2.*cached result"):
            extract_to_markdown(path)

    def test_xlsx_formula_with_cached_empty_string_is_valid(self):
        path = self._formula_workbook()
        self._set_formula_cache(path, "")
        markdown = extract_to_markdown(path)
        self.assertIn("Computed name", markdown)
        self.assertNotIn("CONCAT", markdown)

    def test_xlsx_formula_error_cache_is_not_treated_as_content(self):
        path = self._formula_workbook()
        self._set_formula_cache(path, "#REF!", "e")
        with self.assertRaisesRegex(ExtractionError, "Recalculate and save"):
            extract_to_markdown(path)


if __name__ == "__main__":
    unittest.main()
