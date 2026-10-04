"""Check the testbench helpers without loading any spaCy model."""

import unittest
from types import SimpleNamespace

from app.logic import (
    highlight_html,
    label_intervals,
    recall_table,
    score_labels,
    split_sections,
    summarize,
)


def span(start, end, entity_type):
    return SimpleNamespace(start=start, end=end, entity_type=entity_type, score=0.8)


class AppLogicTests(unittest.TestCase):
    text = "Mail Anna <a@b.fi> or call +358 40 1234567 about Ox."

    def entities(self):
        return [{"type": "PERSON", "value": "Anna", "location": "body"},
                {"type": "EMAIL", "value": "a@b.fi", "location": "body"},
                {"type": "PHONE", "value": "+358 40 1234567", "location": "body"},
                {"type": "COMPANY", "value": "Secret Oy", "location": "metadata"}]

    def test_found_partial_missed_absent(self):
        t = self.text
        results = [span(5, 9, "PERSON"),
                   span(t.index("a@b"), t.index("a@b") + 3, "EMAIL_ADDRESS"),
                   span(0, 4, "PHONE_NUMBER")]  # wrong place
        status = {s["type"]: s["status"] for s in score_labels(t, self.entities(), results)}
        self.assertEqual(status, {"PERSON": "covered", "EMAIL": "partial",
                                  "PHONE": "missed", "COMPANY": "absent"})

    def test_wrong_type_does_not_count(self):
        scored = score_labels(self.text, self.entities()[:1], [span(5, 9, "LOCATION")])
        self.assertEqual(scored[0]["status"], "missed")

    def test_summary_counts_and_misses(self):
        scored = score_labels(self.text, self.entities(), [span(5, 9, "PERSON")])
        got, total, misses = summarize(scored)
        self.assertEqual((got, total), (1, 3))
        self.assertEqual(sorted(misses), ["EMAIL", "PHONE"])

    def test_highlight_escapes_and_marks(self):
        out = highlight_html("<b>Anna</b> & co", [(3, 7, "PERSON", 0.9)], {"PERSON": "#fff"})
        self.assertIn("&lt;b&gt;", out)
        self.assertIn(">Anna</mark>", out)
        self.assertNotIn("<b>", out)

    def test_overlaps_are_merged(self):
        out = highlight_html("abcdef", [(0, 3, "A", 0.5), (2, 5, "B", 0.9)], {})
        self.assertEqual(out.count("<mark"), 1)
        self.assertIn(">abcde</mark>", out)

    def test_label_intervals_cover_every_occurrence(self):
        scored = [{"type": "PERSON", "value": "Eva", "location": "body", "status": "partial"}]
        self.assertEqual(len(label_intervals("Eva met Eva", scored)), 2)

    def test_hidden_sections(self):
        md = ("## Document metadata\nAuthor: X\n\n## Document content\nbody\n\n"
              "## Footer (section 1)\nfoot\n\n## Slide 1\ns\n\n### Speaker notes\nn")
        hidden = {t: h for t, _, h in split_sections(md)}
        self.assertEqual(hidden, {"Document metadata": True, "Document content": False,
                                  "Footer (section 1)": True, "Slide 1": False,
                                  "Speaker notes": True})

    def test_recall_table(self):
        rows = [{"dataset": "d", "method": "m", "covered": "3", "planted": "4"},
                {"dataset": "d", "method": "m", "covered": "1", "planted": "4"}]
        self.assertEqual(recall_table(rows), {("d", "m"): 0.5})


if __name__ == "__main__":
    unittest.main()
