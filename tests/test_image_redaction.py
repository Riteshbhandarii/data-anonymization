"""Image redaction and its scoring, tested on drawn boxes without OCR or models."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from eval.screenshot_bench import (
    blacked,
    find_occurrences,
    score_image,
    summarize,
    value_state,
)
from redact.image import (
    Word,
    draw_boxes,
    expand_to_lines,
    layout,
    ocr_words,
    redact_image,
    words_in_spans,
)


def word(text, left, line=1):
    return Word(text, left, 10 * line, 8 * len(text), 8, (1, 1, line))


WORDS = [word("Call", 0), word("Anna", 40), word("Virtanen,", 80),
         word("Espoo", 0, line=2), word("today.", 50, line=2)]


class StubDetector:
    def __init__(self, value, entity_type="PERSON"):
        self.value, self.entity_type, self.seen = value, entity_type, None

    def detect(self, text, language="en"):
        self.seen = text
        start = text.find(self.value)
        return [SimpleNamespace(start=start, end=start + len(self.value),
                                entity_type=self.entity_type, score=0.9)]


class LayoutTests(unittest.TestCase):
    def test_lines_are_kept_and_word_ranges_point_into_the_text(self):
        text, ranges = layout(WORDS)
        self.assertEqual("Call Anna Virtanen,\nEspoo today.", text)
        self.assertEqual([word.text for word in WORDS], [text[start:end] for start, end in ranges])

    def test_a_span_touching_part_of_a_word_boxes_the_whole_word(self):
        _, ranges = layout(WORDS)
        spans = [SimpleNamespace(start=5, end=18)]  # "Anna Virtanen" without the comma
        self.assertEqual([1, 2], words_in_spans(ranges, spans))
        self.assertEqual([2], words_in_spans(ranges, [SimpleNamespace(start=17, end=18)]))

    def test_a_span_ending_where_a_word_starts_does_not_box_it(self):
        _, ranges = layout(WORDS)
        self.assertEqual([0], words_in_spans(ranges, [SimpleNamespace(start=0, end=5)]))

    def test_line_expansion_is_unique_and_preserves_reading_order(self):
        self.assertEqual([0, 1, 2], expand_to_lines(WORDS, iter([2, 1, 2])))
        self.assertEqual(list(range(len(WORDS))), expand_to_lines(WORDS, [4, 1]))
        self.assertEqual([], expand_to_lines(WORDS, []))

    def test_line_numbers_are_scoped_to_their_block_and_paragraph(self):
        words = [Word("Anna", 0, 0, 40, 8, (1, 1, 1)),
                 Word("Virtanen", 50, 0, 60, 8, (1, 1, 1)),
                 Word("Other paragraph", 0, 30, 100, 8, (1, 2, 1)),
                 Word("Other block", 0, 60, 100, 8, (2, 1, 1))]
        self.assertEqual([0, 1], expand_to_lines(words, [0]))
        self.assertEqual([2], expand_to_lines(words, [2]))
        self.assertEqual([3], expand_to_lines(words, [3]))

    def test_invalid_line_selection_cannot_select_a_different_word(self):
        for index in (-1, len(WORDS), 1.5, True):
            with self.subTest(index=index), self.assertRaises(ValueError):
                expand_to_lines(WORDS, [index])


class OcrScaleTests(unittest.TestCase):
    def setUp(self):
        self.data = {"text": [" ", " Anna "], "left": [0, 5], "top": [0, 7],
                     "width": [0, 8], "height": [0, 4], "block_num": [0, 2],
                     "par_num": [0, 3], "line_num": [0, 4]}

    def test_supported_scales_map_every_edge_outwards_to_the_original(self):
        image = Image.new("RGBA", (20, 15), (0, 0, 0, 0))
        original = image.tobytes()
        for scale, expected_box in ((1, (5, 7, 13, 11)), (2, (2, 3, 7, 6)), (3, (1, 2, 5, 4))):
            with self.subTest(scale=scale), patch("pytesseract.image_to_data", return_value=self.data) as read:
                words = ocr_words(image, "fin", scale=scale)
                self.assertEqual(1, len(words))
                self.assertEqual("Anna", words[0].text)
                self.assertEqual((2, 3, 4), words[0].line)
                self.assertEqual(expected_box, words[0].box)
                ocr_input = read.call_args.args[0]
                self.assertEqual((20 * scale, 15 * scale), ocr_input.size)
                self.assertEqual("RGB", ocr_input.mode)
                self.assertEqual((255, 255), ocr_input.convert("L").getextrema())
                self.assertEqual("fin", read.call_args.kwargs["lang"])
        self.assertEqual(original, image.tobytes())
        self.assertEqual((20, 15), image.size)

    def test_invalid_scales_fail_before_ocr(self):
        image = Image.new("RGB", (20, 15), "white")
        with patch("pytesseract.image_to_data") as read:
            for scale in (0, -1, 4, 1.5, True, "2", None):
                with self.subTest(scale=scale), self.assertRaisesRegex(ValueError, "OCR scale"):
                    ocr_words(image, scale=scale)
            read.assert_not_called()

    def test_scaled_ocr_boxes_cover_original_pixels_and_keep_output_dimensions(self):
        image = Image.new("RGB", (20, 15), "white")
        detector = StubDetector("Anna")
        with patch("pytesseract.image_to_data", return_value=self.data) as read:
            redacted, boxes = redact_image(image, detector, ocr_scale=3)
        self.assertEqual((60, 45), read.call_args.args[0].size)
        self.assertEqual([(1, 2, 5, 4)], boxes)
        self.assertEqual(image.size, redacted.size)
        self.assertEqual((0, 0), redacted.convert("L").crop(boxes[0]).getextrema())
        self.assertEqual((255, 255, 255), redacted.getpixel((19, 14)))
        self.assertEqual((255, 255), image.convert("L").getextrema())


class DrawingTests(unittest.TestCase):
    def test_boxes_are_filled_with_padding_and_the_input_is_unchanged(self):
        image = Image.new("RGB", (60, 30), "white")
        redacted = draw_boxes(image, [(20, 10, 30, 20)], padding=2)
        self.assertEqual((255, 255, 255), image.getpixel((25, 15)))
        self.assertEqual((0, 0, 0), redacted.getpixel((18, 8)))
        self.assertEqual((0, 0, 0), redacted.getpixel((32, 22)))
        self.assertEqual((255, 255, 255), redacted.getpixel((34, 15)))

    def test_detected_words_are_blacked_out_and_others_are_not(self):
        image = Image.new("RGB", (200, 40), "white")
        detector = StubDetector("Anna Virtanen")
        redacted, boxes = redact_image(image, detector, words=WORDS)
        self.assertEqual("Call Anna Virtanen,\nEspoo today.", detector.seen)
        self.assertEqual([WORDS[1].box, WORDS[2].box], boxes)
        gray = redacted.convert("L")
        self.assertEqual([False, True, True, False, False], [blacked(gray, word.box) for word in WORDS])

    def test_whole_lines_covers_other_words_only_on_the_selected_line(self):
        image = Image.new("RGB", (200, 40), "white")
        redacted, boxes = redact_image(image, StubDetector("Anna"), words=WORDS, whole_lines=True)
        self.assertEqual([entry.box for entry in WORDS[:3]], boxes)
        gray = redacted.convert("L")
        self.assertEqual([True, True, True, False, False], [blacked(gray, entry.box) for entry in WORDS])
        self.assertEqual((255, 255), image.convert("L").getextrema())

    def test_whole_lines_without_detections_preserves_visible_pixels(self):
        image = Image.new("RGB", (200, 40), "blue")
        detector = SimpleNamespace(detect=lambda text, language: [])
        redacted, boxes = redact_image(image, detector, words=WORDS, whole_lines=True)
        self.assertEqual([], boxes)
        self.assertEqual(image.tobytes(), redacted.tobytes())

    def test_precomputed_words_are_reused_without_scaling_their_coordinates(self):
        image = Image.new("RGB", (200, 40), "white")
        with patch("redact.image.ocr_words") as read:
            redacted, boxes = redact_image(image, StubDetector("Anna"), words=WORDS, ocr_scale=3)
        read.assert_not_called()
        self.assertEqual([WORDS[1].box], boxes)
        self.assertEqual(image.size, redacted.size)

    def test_transparent_hidden_text_is_discarded_instead_of_exposed(self):
        image = Image.new("RGB", (500, 60), "white")
        ImageDraw.Draw(image).text((5, 5), "hidden-email@example.test",
                                  font=ImageFont.load_default(size=24), fill="black")
        image.putalpha(0)
        # OCR sees the white composite, so it returns no words or detections.
        detector = SimpleNamespace(detect=lambda text, language: [])
        redacted, boxes = redact_image(image, detector, words=[])
        self.assertEqual([], boxes)
        self.assertEqual((255, 255), redacted.convert("L").getextrema())
        self.assertEqual((0, 255), image.convert("RGB").convert("L").getextrema())

    def test_palette_transparency_is_removed_and_visible_pixels_are_preserved(self):
        image = Image.new("P", (3, 1))
        image.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
        image.info["transparency"] = 0
        image.putpixel((1, 0), 1)
        redacted = draw_boxes(image, [])
        self.assertEqual([(255, 255, 255), (255, 0, 0), (255, 255, 255)],
                         [redacted.getpixel((index, 0)) for index in range(3)])
        self.assertEqual({}, redacted.info)


class ScoringTests(unittest.TestCase):
    def test_values_are_found_across_line_breaks_and_repeated(self):
        self.assertEqual([[1, 2, 3]], find_occurrences(WORDS, "Anna Virtanen, Espoo"))
        repeated = [word("Anna", 0), word("and", 40), word("Anna", 80)]
        self.assertEqual([[0], [2]], find_occurrences(repeated, "Anna"))
        self.assertEqual([], find_occurrences(WORDS, "Turku"))

    def test_unicode_normalization_preserves_matching_word_indices(self):
        words = [word("Ma\u0308kela\u0308", 0), word("and", 80), word("Mäkelä", 120)]
        self.assertEqual([[0], [2]], find_occurrences(words, "Mäkelä"))
        self.assertEqual([[0, 1, 2]], find_occurrences(words, "Mäkelä and Mäkelä"))

    def test_decomposed_unicode_remains_a_leak_after_redaction(self):
        words = [word("Mäkelä", 0)]
        after_words = [word("Ma\u0308kela\u0308", 0)]
        image = draw_boxes(Image.new("RGB", (100, 40), "white"), [words[0].box])
        result = score_image(words, image, after_words, [{"type": "PERSON", "value": "Mäkelä"}])
        self.assertEqual("leaked", result["entities"][0]["state"])

    def test_value_states(self):
        self.assertEqual("unread", value_state([], [], False))
        self.assertEqual("leaked", value_state([[0]], [True], True))
        self.assertEqual("hidden", value_state([[0, 1]], [True, True], False))
        self.assertEqual("partial", value_state([[0, 1]], [True, False], False))
        self.assertEqual("partial", value_state([[0], [1]], [True, False], False))

    def test_a_value_with_one_word_left_visible_is_partial_not_hidden(self):
        image = Image.new("RGB", (200, 40), "white")
        after = draw_boxes(image, [WORDS[1].box, WORDS[2].box])
        entities = [{"type": "PERSON", "value": "Anna Virtanen"},
                    {"type": "ADDRESS", "value": "Virtanen, Espoo"},
                    {"type": "COMPANY", "value": "Nokia"}]
        result = score_image(WORDS, after, [word("Call", 0)], entities)
        self.assertEqual(["hidden", "partial", "unread"], [entity["state"] for entity in result["entities"]])
        self.assertEqual((5, 2, 2, 0), (result["words"], result["words_blacked"],
                                        result["other_words"], result["other_words_blacked"]))

    def test_value_still_read_after_redaction_is_leaked(self):
        image = Image.new("RGB", (200, 40), "white")
        result = score_image(WORDS, image, WORDS, [{"type": "PERSON", "value": "Anna Virtanen"}])
        self.assertEqual("leaked", result["entities"][0]["state"])

    def test_recall_counts_only_values_readable_before(self):
        documents = [{"method": "m", "seconds": 1.0, "words": 10, "words_blacked": 4,
                      "other_words": 6, "other_words_blacked": 1,
                      "entities": [{"state": state, "text_hidden": state != "partial"}
                                   for state in ("hidden", "hidden", "partial", "unread")]}]
        row = summarize(documents, ("method",))[0]
        self.assertEqual(3, row["readable_before"])
        self.assertAlmostEqual(2 / 3, row["image_recall"])
        self.assertAlmostEqual(2 / 4, row["hidden_of_planted"])
        self.assertAlmostEqual(3 / 4, row["text_recall"])
        self.assertAlmostEqual(0.4, row["over_redaction"])
        self.assertAlmostEqual(1 / 6, row["other_words_redacted"])


if __name__ == "__main__":
    unittest.main()
