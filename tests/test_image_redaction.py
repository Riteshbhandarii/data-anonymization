"""Image redaction and its scoring, tested on drawn boxes without OCR or models."""

import unittest
from types import SimpleNamespace

from PIL import Image

from eval.screenshot_bench import (
    blacked,
    find_occurrences,
    score_image,
    summarize,
    value_state,
)
from redact.image import Word, draw_boxes, layout, redact_image, words_in_spans


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
