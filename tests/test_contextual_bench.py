"""Scoring for the contextual-identifier benchmark, on tiny in-memory documents."""

import unittest

from eval.contextual_bench import score, write_spans


def doc(split="test"):
    text = "Permit LU-1 for Kestrel. ISO 9001 applies."
    return {"id": "d1", "language": "en", "split": split, "text": text,
            "labels": [{"value": "LU-1", "category": "LICENCE", "start": 7, "end": 11},
                       {"value": "Kestrel", "category": "PROJECT", "start": 16, "end": 23}],
            "decoys": [{"value": "ISO 9001", "kind": "standard", "start": 25, "end": 33}]}


class ContextualScoreTests(unittest.TestCase):
    def test_any_type_cover_partial_and_decoys(self):
        result = score([doc()], {"d1": [(7, 11), (16, 19), (25, 28)]})["test"]
        self.assertEqual({"planted": 1, "covered": 1, "partial": 0}, result["categories"]["LICENCE"])
        self.assertEqual({"planted": 1, "covered": 0, "partial": 1}, result["categories"]["PROJECT"])
        self.assertEqual({"total": 1, "masked": 1}, result["decoys"])
        self.assertEqual(3, result["masked_outside_labels"]["characters"])

    def test_union_of_adjacent_spans_covers_a_value(self):
        result = score([doc()], {"d1": [(16, 19), (19, 23)]})["test"]
        self.assertEqual(1, result["categories"]["PROJECT"]["covered"])

    def test_splits_are_separate(self):
        result = score([doc("dev")], {"d1": [(7, 11)]})
        self.assertEqual(0, result["test"]["contextual"]["planted"])
        self.assertEqual(1, result["dev"]["contextual"]["covered"])
        self.assertEqual(2, result["all"]["contextual"]["planted"])

    def test_span_text_only_under_outputs(self):
        with self.assertRaises(ValueError):
            write_spans("/tmp/spans.json", [doc()], {"d1": []})


if __name__ == "__main__":
    unittest.main()
