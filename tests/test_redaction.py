"""Verify span replacement independently of the detector's recognition quality."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from detect import PresidioDetector
from pipeline import run_pipeline
from redact import AliasMap, PipelineAnonymizer, Span, redact, resolve_spans


class RedactionTests(unittest.TestCase):
    def test_replacement_preserves_markdown_and_unicode_offsets(self):
        text = "# People\n\nÅsa emailed Eva.  \nNext line.\n"
        spans = [Span(text.index("Åsa"), text.index("Åsa") + 3, "PERSON", 0.8),
                 Span(text.index("Eva"), text.index("Eva") + 3, "PERSON", 0.8)]
        self.assertEqual(redact(text, spans), "# People\n\n[PERSON] emailed [PERSON].  \nNext line.\n")

    def test_pseudonyms_share_within_document_and_explicit_corpus_scope(self):
        text = "Alice Bob Alice"
        spans = [Span(0, 5, "PERSON", 1), Span(6, 9, "PERSON", 1), Span(10, 15, "PERSON", 1)]
        aliases = AliasMap()
        self.assertEqual(redact(text, spans, mode="pseudonymize", aliases=aliases),
                         "[PERSON_1] [PERSON_2] [PERSON_1]")
        self.assertEqual(redact("Bob", [Span(0, 3, "PERSON", 1)], mode="pseudonymize", aliases=aliases), "[PERSON_2]")
        self.assertEqual(redact("Bob", [Span(0, 3, "PERSON", 1)], mode="pseudonymize"), "[PERSON_1]")
        self.assertNotIn("Alice", repr(aliases))
        aliases.clear()
        self.assertEqual(aliases.token("PERSON", "Bob"), "[PERSON_1]")

    def test_overlapping_spans_cover_union_deterministically(self):
        text = "George Washington Square"
        spans = [Span(0, 17, "PERSON", 0.8), Span(7, 24, "LOCATION", 0.8), Span(7, 17, "PERSON", 0.9)]
        self.assertEqual(resolve_spans(text, spans), [Span(0, 24, "PERSON", 0.9)])
        self.assertEqual(redact(text, spans), "[PERSON]")
        self.assertEqual(redact(text, reversed(spans)), "[PERSON]")

    def test_adjacent_entities_remain_distinct(self):
        self.assertEqual(redact("AliceBob", [Span(0, 5, "PERSON", 1), Span(5, 8, "PERSON", 1)],
                                mode="pseudonymize"), "[PERSON_1][PERSON_2]")

    def test_invalid_spans_are_rejected_before_editing(self):
        cases = [
            {"start": -1, "end": 3, "entity_type": "PERSON", "score": 1},
            {"start": 2, "end": 2, "entity_type": "PERSON", "score": 1},
            {"start": 0, "end": 99, "entity_type": "PERSON", "score": 1},
            {"start": True, "end": 3, "entity_type": "PERSON", "score": 1},
            {"start": 0, "end": 3, "entity_type": "PERSON", "score": float("nan")},
            {"start": 0, "end": 3, "entity_type": "BAD]", "score": 1},
            {"start": 0, "end": 3, "entity_type": "PERSON"},
        ]
        for span in cases:
            with self.subTest(span=span), self.assertRaises(ValueError):
                redact("Alice", [span])
        with self.assertRaises(ValueError):
            redact("Alice", [], mode="unknown")
        self.assertEqual(redact("No detections.  \n", []), "No detections.  \n")

    def test_adapter_reuses_analyzer_configuration(self):
        calls = []
        analyzer = SimpleNamespace(analyze=lambda **kwargs: calls.append(kwargs) or [])
        detector = PresidioDetector(analyzer, score_threshold=0.25)
        self.assertEqual(detector.detect("Same text.  \n", language="fi"), [])
        self.assertEqual(calls, [{"text": "Same text.  \n", "language": "fi", "score_threshold": 0.25}])

    def test_pipeline_saves_redaction_and_uses_normalized_offsets(self):
        seen = []

        def detect(text, language):
            seen.append((text, language))
            offset = text.index("Alice")
            return [Span(offset, offset + 5, "PERSON", 1)]

        anonymizer = PipelineAnonymizer(SimpleNamespace(detect=detect), language="en")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            source.write_bytes(b"\r\nAlice speaks.  \r\nNext line.\r\n")
            result = run_pipeline(source, Path(directory) / "out", anonymizer=anonymizer)
            self.assertEqual(seen, [("Alice speaks.  \nNext line.\n", "en")])
            self.assertEqual(result.output_path.read_text(encoding="utf-8"), "[PERSON] speaks.  \nNext line.\n")
            self.assertEqual(anonymizer.last_spans, (Span(0, 5, "PERSON", 1),))


if __name__ == "__main__":
    unittest.main()
