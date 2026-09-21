"""Extract text from supported files and represent it as Markdown."""

import csv
from io import BytesIO
from pathlib import Path
from typing import Any

from .errors import ExtractionError, UnsupportedFormatError

TEXT_EXTENSIONS = {".md", ".txt"}
IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = tuple(
    sorted(TEXT_EXTENSIONS | IMAGE_EXTENSIONS | {".csv", ".docx", ".pdf", ".pptx", ".xlsx"})
)


def detect_format(file_path: str | Path) -> str:
    """Return the normalized extension for a supported input file."""
    suffix = Path(file_path).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(SUPPORTED_EXTENSIONS)
        raise UnsupportedFormatError(
            f"Unsupported file type '{suffix or '(none)'}'. Supported types: {supported}."
        )
    return suffix


def extract_to_markdown(file_path: str | Path, ocr_language: str = "eng") -> str:
    """Extract one supported file into a Markdown string."""
    path = Path(file_path)
    if not path.is_file():
        raise ExtractionError(f"Input file does not exist: {path}")

    suffix = detect_format(path)
    try:
        if suffix in TEXT_EXTENSIONS:
            return _extract_text(path)
        if suffix == ".csv":
            return _extract_csv(path)
        if suffix == ".docx":
            return _extract_docx(path)
        if suffix == ".xlsx":
            return _extract_xlsx(path)
        if suffix == ".pptx":
            return _extract_pptx(path)
        if suffix == ".pdf":
            return _extract_pdf(path, ocr_language)
        if suffix in IMAGE_EXTENSIONS:
            return _extract_image(path, ocr_language)
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Could not extract '{path.name}': {exc}") from exc

    raise UnsupportedFormatError(f"No extractor registered for '{suffix}'.")


def _extract_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _extract_csv(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    return _rows_to_markdown(rows, empty_message="_Empty CSV file._")


def _extract_docx(path: Path) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(path)
    parts: list[str] = []

    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if not text:
                continue

            style_name = paragraph.style.name if paragraph.style else ""
            if style_name.startswith("Heading"):
                level_text = style_name.removeprefix("Heading").strip()
                level = int(level_text) if level_text.isdigit() else 2
                parts.append(f"{'#' * max(1, min(level, 6))} {text}")
            elif style_name.startswith("List"):
                parts.append(f"- {text}")
            else:
                parts.append(text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            rows = [[cell.text for cell in row.cells] for row in table.rows]
            parts.append(_rows_to_markdown(rows, empty_message="_Empty table._"))

    return "\n\n".join(parts)


def _extract_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=False)
    parts: list[str] = []
    try:
        for sheet in workbook.worksheets:
            parts.append(f"## Sheet: {sheet.title}")
            rows = [
                ["" if value is None else str(value) for value in row]
                for row in sheet.iter_rows(values_only=True)
            ]
            rows = [row for row in rows if any(cell.strip() for cell in row)]
            parts.append(_rows_to_markdown(rows, empty_message="_Empty sheet._"))
    finally:
        workbook.close()
    return "\n\n".join(parts)


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation

    presentation = Presentation(path)
    parts: list[str] = []

    for index, slide in enumerate(presentation.slides, start=1):
        title_shape = slide.shapes.title
        title = title_shape.text.strip() if title_shape and title_shape.has_text_frame else ""
        heading = f"## Slide {index}"
        if title:
            heading = f"{heading}: {title}"
        parts.append(heading)

        for shape in slide.shapes:
            if title_shape is not None and shape.shape_id == title_shape.shape_id:
                continue
            if getattr(shape, "has_table", False):
                rows = [[cell.text for cell in row.cells] for row in shape.table.rows]
                parts.append(_rows_to_markdown(rows, empty_message="_Empty table._"))
            elif getattr(shape, "has_text_frame", False):
                text = shape.text.strip()
                if text:
                    parts.append(text)

        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                parts.append(f"### Speaker notes\n\n{notes}")

    return "\n\n".join(parts)


def _extract_pdf(path: Path, ocr_language: str) -> str:
    import pymupdf

    parts: list[str] = []
    with pymupdf.open(path) as document:
        for index, page in enumerate(document, start=1):
            parts.append(f"## Page {index}")
            text = page.get_text("text").strip()
            if text:
                parts.append(text)
            else:
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                parts.append(_ocr_image_bytes(pixmap.tobytes("png"), ocr_language))
    return "\n\n".join(parts)


def _extract_image(path: Path, ocr_language: str) -> str:
    from PIL import Image

    with Image.open(path) as image:
        text = _run_tesseract(image, ocr_language)
    return f"## OCR text\n\n{text.strip()}"


def _ocr_image_bytes(image_bytes: bytes, ocr_language: str) -> str:
    from PIL import Image

    with Image.open(BytesIO(image_bytes)) as image:
        return _run_tesseract(image, ocr_language).strip()


def _run_tesseract(image: Any, ocr_language: str) -> str:
    try:
        import pytesseract
    except ImportError as exc:
        raise ExtractionError(
            "OCR requires pytesseract and Pillow. Install the project requirements."
        ) from exc

    try:
        return pytesseract.image_to_string(image, lang=ocr_language)
    except pytesseract.TesseractNotFoundError as exc:
        raise ExtractionError(
            "OCR requires the Tesseract executable. Install Tesseract and add it to PATH."
        ) from exc
    except pytesseract.TesseractError as exc:
        raise ExtractionError(
            f"Tesseract could not use OCR language '{ocr_language}': {exc}"
        ) from exc


def _rows_to_markdown(rows: list[list[Any]], empty_message: str) -> str:
    if not rows:
        return empty_message

    width = max(len(row) for row in rows)
    padded_rows = [row + [""] * (width - len(row)) for row in rows]
    escaped_rows = [[_escape_cell(value) for value in row] for row in padded_rows]
    header = escaped_rows[0]
    separator = ["---"] * width

    lines = [_markdown_row(header), _markdown_row(separator)]
    lines.extend(_markdown_row(row) for row in escaped_rows[1:])
    return "\n".join(lines)


def _escape_cell(value: Any) -> str:
    return str(value).strip().replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")


def _markdown_row(row: list[str]) -> str:
    return f"| {' | '.join(row)} |"
