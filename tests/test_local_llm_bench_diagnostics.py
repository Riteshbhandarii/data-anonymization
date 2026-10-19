"""Any-type recall and over-masking arithmetic; no LLM, no network."""

import unittest
from pathlib import Path
from types import SimpleNamespace

from eval.local_llm_bench import over_masking, spans_out_path, union_state


def span(start, end, kind="LOCATION"):
    return SimpleNamespace(start=start, end=end, entity_type=kind)


TEXT = "Mail Aino at 12 Oak Road now"
ENTITIES = [{"value": "Aino", "type": "PERSON", "location": "body"},
            {"value": "12 Oak Road", "type": "ADDRESS", "location": "body"},
            {"value": "now", "type": "DATE", "location": "metadata"}]


class DiagnosticsTests(unittest.TestCase):
    def test_union_of_pieces_covers_whole(self):
        value = "12 Oak Road"
        start = TEXT.find(value)
        pieces = [span(start, start + 2, "A"), span(start + 2, start + len(value), "B")]
        self.assertEqual(union_state(TEXT, value, pieces), "covered")

    def test_partial_and_none(self):
        start = TEXT.find("12 Oak Road")
        self.assertEqual(union_state(TEXT, "12 Oak Road", [span(start, start + 5)]), "partial")
        self.assertEqual(union_state(TEXT, "12 Oak Road", [span(0, 4)]), "")

    def test_every_occurrence_must_be_covered(self):
        text = "Aino and Aino"
        self.assertEqual(union_state(text, "Aino", [span(0, 4)]), "partial")

    def test_over_masking_counts_outside_body_labels(self):
        a = TEXT.find("Aino")
        o = TEXT.find("12 Oak Road")
        # span 1 masks "Mail Aino" (5 chars outside); span 2 sits on a metadata label only
        spans = [span(0, a + 4), span(o, o + 11), span(TEXT.find("now"), len(TEXT))]
        outside, orphans = over_masking(TEXT, ENTITIES, spans)
        self.assertEqual(outside, 5 + 3)
        self.assertEqual(orphans, 0)

    def test_overlapping_spans_not_double_counted_and_orphans(self):
        spans = [span(0, 4), span(2, 6), span(len(TEXT) - 1, len(TEXT))]
        outside, orphans = over_masking(TEXT, ENTITIES, spans)
        self.assertEqual(outside, 5 + 1)
        self.assertEqual(orphans, 1)

    def test_spans_out_only_under_outputs(self):
        root = Path(__file__).resolve().parent.parent
        self.assertEqual(spans_out_path(root / "outputs" / "x" / "s.json"), root / "outputs" / "x" / "s.json")
        for bad in (root / "s.json", "/tmp/s.json", root / "outputs" / ".." / "s.json"):
            with self.assertRaises(ValueError):
                spans_out_path(bad)


if __name__ == "__main__":
    unittest.main()
