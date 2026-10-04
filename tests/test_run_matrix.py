"""Pure helpers of the dataset runs and the manual pack; no models are loaded."""

import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from detect.gliner_detector import select_device, windows
from eval.make_pack import answer_rows, best_method, pair_prompt, truncate_at_line
from eval.run_matrix import detect_long, mention_state, merge_rows, split_text, tally


def span(start, end, kind):
    return SimpleNamespace(start=start, end=end, entity_type=kind, score=0.9)


class MentionStateTests(unittest.TestCase):
    def test_whole_partial_and_missed(self):
        spans = [span(0, 10, "PERSON")]
        self.assertEqual("covered", mention_state(2, 8, "PERSON", spans))
        self.assertEqual("partial", mention_state(5, 15, "PERSON", spans))
        self.assertEqual("", mention_state(20, 30, "PERSON", spans))

    def test_wrong_type_does_not_count(self):
        self.assertEqual("", mention_state(0, 5, "PERSON", [span(0, 5, "LOCATION")]))

    def test_unmapped_type_accepts_any_detection(self):
        self.assertEqual("covered", mention_state(0, 5, "CODE", [span(0, 9, "PLATE")]))

    def test_covered_wins_over_earlier_partial(self):
        spans = [span(0, 3, "PERSON"), span(0, 9, "PERSON")]
        self.assertEqual("covered", mention_state(0, 9, "PERSON", spans))


class ChunkingTests(unittest.TestCase):
    def test_pieces_rebuild_the_text_and_stay_small(self):
        text = "".join(f"line {i}\n" for i in range(50))
        pieces = list(split_text(text, 40))
        self.assertEqual(text, "".join(p for _, p in pieces))
        self.assertTrue(all(len(p) <= 40 for _, p in pieces))
        self.assertTrue(all(text[o:o + len(p)] == p for o, p in pieces))

    def test_detect_long_shifts_offsets_back(self):
        class Finder:
            def detect(self, text, language="en"):
                at = text.find("NAME")
                return [span(at, at + 4, "PERSON")] if at >= 0 else []

        text = "x\n" * 30 + "NAME\n" + "y\n" * 30
        found = detect_long(Finder(), text, "en") if len(text) > 100_000 else None
        self.assertIsNone(found)  # short text takes the direct path
        import eval.run_matrix as rm
        old, rm.MAX_CHUNK = rm.MAX_CHUNK, 20
        try:
            (result,) = [s for s in rm.detect_long(Finder(), text, "en")]
        finally:
            rm.MAX_CHUNK = old
        self.assertEqual("NAME", text[result.start:result.end])

    def test_gliner_windows_cover_everything(self):
        text = "word " * 400
        self.assertEqual(text, "".join(p for _, p in windows(text, 100)))


class DeviceTests(unittest.TestCase):
    def test_environment_override_wins(self):
        self.assertEqual("cpu", select_device({"GLINER_DEVICE": "cpu"}))


class TallyTests(unittest.TestCase):
    def test_counts_by_group(self):
        records = [
            {"entity_type": "PERSON", "language": "en", "state": "covered"},
            {"entity_type": "PERSON", "language": "en", "state": "partial"},
            {"entity_type": "PERSON", "language": "en", "state": ""},
        ]
        (row,) = tally(records, "tab", "basic")
        self.assertEqual((3, 1, 1), (row["planted"], row["covered"], row["partial"]))

    def test_merge_keeps_other_datasets(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.csv"
            merge_rows(path, ["dataset", "n"], ("dataset",), {("a",)}, [{"dataset": "a", "n": 1}])
            merge_rows(path, ["dataset", "n"], ("dataset",), {("b",)}, [{"dataset": "b", "n": 2}])
            merge_rows(path, ["dataset", "n"], ("dataset",), {("a",)}, [{"dataset": "a", "n": 3}])
            with path.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        self.assertEqual({("b", "2"), ("a", "3")}, {(r["dataset"], r["n"]) for r in rows})


class PackTests(unittest.TestCase):
    def test_best_method_uses_mean_over_datasets(self):
        rows = [
            {"dataset": "fake", "method": "a", "planted": "10", "covered": "10", "partial": "0"},
            {"dataset": "tab", "method": "a", "planted": "10", "covered": "0", "partial": "0"},
            {"dataset": "fake", "method": "b", "planted": "10", "covered": "6", "partial": "0"},
            {"dataset": "tab", "method": "b", "planted": "10", "covered": "6", "partial": "0"},
        ]
        self.assertEqual("b", best_method(rows))

    def test_truncation_stops_at_a_line_break(self):
        text = "aaaa\nbbbb\ncccc\n"
        out = truncate_at_line(text, 8)
        self.assertTrue(out.startswith("aaaa"))
        self.assertNotIn("bbbb", out)
        self.assertEqual(text, truncate_at_line(text, 100))

    def test_each_prompt_gets_a_row_with_and_without_search(self):
        rows = answer_rows([("F01", "fake", "naming", "F01-naming-company")])
        self.assertEqual(["no", "yes"], [r["web_search"] for r in rows])
        self.assertEqual("", rows[0]["answer"])

    def test_pair_prompt_labels_both_documents(self):
        text = pair_prompt("one", "two")
        self.assertIn("Document A:\none", text)
        self.assertIn("Document B:\ntwo", text)


if __name__ == "__main__":
    unittest.main()
