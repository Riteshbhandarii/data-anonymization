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


def ocr_words(image: Image.Image, language: str = "eng+fin") -> list[Word]:
    """Read the words of an image with their boxes, in reading order."""
    import pytesseract

    data = pytesseract.image_to_data(_visible_rgb(image), lang=language,
                                   output_type=pytesseract.Output.DICT)
    return [
        Word(text.strip(), data["left"][i], data["top"][i], data["width"][i], data["height"][i],
             (data["block_num"][i], data["par_num"][i], data["line_num"][i]))
        for i, text in enumerate(data["text"]) if text.strip()
    ]


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
                 words: Sequence[Word] | None = None) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    """Detect identifiers in the image text and black them out.

    ``detector`` is any object with ``detect(text, language=...)`` returning
    spans, as in ``detect.methods``. Pass ``words`` to reuse an earlier OCR
    result. Returns the redacted copy and the word boxes that were filled.
    """
    words = ocr_words(image, ocr_language) if words is None else words
    text, ranges = layout(words)
    spans = validate_spans(text, detector.detect(text, language=language))
    boxes = [words[index].box for index in words_in_spans(ranges, spans)]
    return draw_boxes(image, boxes), boxes
