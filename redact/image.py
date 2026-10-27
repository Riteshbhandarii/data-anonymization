"""Black out detected identifiers in an image, such as a screenshot or snip.

Tesseract reads the words and their boxes, the words are joined back into
text for the same detectors the text pipeline uses, and every word a detected
span touches is covered with a filled rectangle. Only solid fill is used:
blurred or pixelated text can often be recovered.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from PIL import Image, ImageDraw

from redact.core import validate_spans

# Tesseract boxes are tight and sometimes cut the first or last glyph, by up
# to about a third of the text height on the synthetic corpus. Each box grows
# by that much, and by at least PADDING pixels.
PADDING = 3


@dataclass(frozen=True)
class Word:
    """One OCR word, its pixel box and the Tesseract (block, paragraph, line) it is on."""

    text: str
    left: int
    top: int
    width: int
    height: int
    line: tuple[int, int, int]

    @property
    def box(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.left + self.width, self.top + self.height


def ocr_words(image: Image.Image, language: str = "eng+fin", *, scale: int = 1) -> list[Word]:
    """Read words in reading order, with boxes in the original image coordinates.

    ``scale`` can enlarge small text by 2 or 3 for OCR. Box edges are rounded
    outwards when mapped back, so a fractional edge does not leave a pixel
    uncovered. The source image and the dimensions used for redaction stay
    unchanged.
    """
    if type(scale) is not int or scale not in (1, 2, 3):
        raise ValueError("OCR scale must be 1, 2, or 3")
    import pytesseract

    visible = _visible_rgb(image)
    if scale != 1:
        visible = visible.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
    data = pytesseract.image_to_data(visible, lang=language,
                                   output_type=pytesseract.Output.DICT)
    words = []
    for index, text in enumerate(data["text"]):
        if not text.strip():
            continue
        left, top = data["left"][index] // scale, data["top"][index] // scale
        right = (data["left"][index] + data["width"][index] + scale - 1) // scale
        bottom = (data["top"][index] + data["height"][index] + scale - 1) // scale
        words.append(Word(text.strip(), left, top, right - left, bottom - top,
                          (data["block_num"][index], data["par_num"][index], data["line_num"][index])))
    return words


def layout(words: Sequence[Word]) -> tuple[str, list[tuple[int, int]]]:
    """Join words with spaces inside a line and newlines between lines.

    Returns the text and each word's (start, end) in it. Keeping line breaks
    stops a detector from reading the end of one line into the next.
    """
    parts, ranges, position = [], [], 0
    for index, word in enumerate(words):
        if index:
            parts.append(" " if word.line == words[index - 1].line else "\n")
            position += 1
        parts.append(word.text)
        ranges.append((position, position + len(word.text)))
        position += len(word.text)
    return "".join(parts), ranges


def words_in_spans(ranges: Sequence[tuple[int, int]], spans: Iterable) -> list[int]:
    """Indices of the words that any span overlaps, even by one character."""
    spans = list(spans)
    return [index for index, (start, end) in enumerate(ranges)
            if any(span.start < end and span.end > start for span in spans)]


def expand_to_lines(words: Sequence[Word], indices: Iterable[int]) -> list[int]:
    """Select every OCR word sharing a selected word's block, paragraph and line.

    Results are unique and in reading order. Line numbers alone are not unique
    across Tesseract paragraphs or blocks.
    """
    lines = set()
    for index in indices:
        if type(index) is not int or not 0 <= index < len(words):
            raise ValueError("Word index is outside the OCR word list")
        lines.add(words[index].line)
    return [index for index, word in enumerate(words) if word.line in lines]


def draw_boxes(image: Image.Image, boxes: Iterable[tuple[int, int, int, int]],
               padding: int = PADDING) -> Image.Image:
    """Return an RGB copy with every box filled black; the input is not changed."""
    redacted = _visible_rgb(image)
    draw = ImageDraw.Draw(redacted)
    for left, top, right, bottom in boxes:
        grow = max(padding, (bottom - top) // 3)
        draw.rectangle((left - grow, top - grow, right + grow, bottom + grow), fill="black")
    return redacted


def _visible_rgb(image: Image.Image) -> Image.Image:
    """Composite transparency onto the same white background used for OCR.

    Dropping alpha alone exposes hidden RGB values that OCR never inspected.
    Starting from fresh pixels also leaves source metadata out of the result.
    """
    rgba = image.convert("RGBA")
    visible = Image.new("RGB", image.size, "white")
    visible.paste(rgba, (0, 0), rgba.getchannel("A"))
    return visible


def redact_image(image: Image.Image, detector, *, language: str = "en", ocr_language: str = "eng+fin",
                 words: Sequence[Word] | None = None, whole_lines: bool = False,
                 ocr_scale: int = 1) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    """Detect identifiers in the image text and black them out.

    ``detector`` is any object with ``detect(text, language=...)`` returning
    spans, as in ``detect.methods``. Pass ``words`` to reuse an earlier OCR
    result in original image coordinates. ``whole_lines`` additionally covers
    all OCR words on any detected word's line. ``ocr_scale`` optionally enlarges
    the image for OCR when ``words`` are not supplied. Returns the redacted copy
    at its original size and the word boxes that were filled.
    """
    words = ocr_words(image, ocr_language, scale=ocr_scale) if words is None else words
    text, ranges = layout(words)
    spans = validate_spans(text, detector.detect(text, language=language))
    indices = words_in_spans(ranges, spans)
    if whole_lines:
        indices = expand_to_lines(words, indices)
    boxes = [words[index].box for index in indices]
    return draw_boxes(image, boxes), boxes
