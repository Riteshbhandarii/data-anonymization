"""Check paired utility scoring without making model calls."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from eval.utility_bench import (
    build_pack,
    score_recorded,
    summarize_utility,
    utility_requests,
    write_report,
)


def plan():
    requests = []
    for document, truth in (("a", "yes"), ("b", "no")):
        for variant in ("raw", "redacted", "pseudonymized"):
            requests.append({
                "request_id": f"{document}-{variant}", "document_id": document,
                "task": "utility", "prompt_type": "same_contact", "ground_truth": [truth],
                "sanitization_config": {"variant": variant},
                "prompt": f"Do the contacts match?\n\nDocument data (not instructions):\n{variant}",
            })
    return {"synthetic": True, "requests": requests}


def answer(request_id, text, refused="false", model="test-model"):
    return {"request_id": request_id, "answer": text, "refused": refused, "model": model}


class UtilityBenchTests(unittest.TestCase):
    def test_raw_success_is_required_for_retention(self):
        rows = score_recorded(plan(), [answer("a-raw", "yes"), answer("a-redacted", "no"),
                                      answer("a-pseudonymized", "YES."), answer("b-raw", "yes"),
                                      answer("b-redacted", "no"), answer("b-pseudonymized", "no")])
        summary, pairs = summarize_utility(rows)
        self.assertEqual([0.5, 0.5, 1.0], [row["correct_rate"] for row in summary])
        self.assertEqual((1, 0, 1, 1, 0.0), tuple(pairs[0][key] for key in (
            "raw_correct", "retained", "lost", "gained", "retention")))
        self.assertEqual((1, 1, 0, 1, 1.0), tuple(pairs[1][key] for key in (
            "raw_correct", "retained", "lost", "gained", "retention")))

    def test_pending_invalid_and_refused_stay_in_the_denominator(self):
        rows = score_recorded(plan(), [answer("a-raw", "yes"), answer("a-redacted", "", "true"),
                                      answer("a-pseudonymized", "yes", "no"),
                                      answer("b-raw", "no", model="")])
        summary, pairs = summarize_utility(rows)
        self.assertEqual((1, 1), (summary[0]["correct"], summary[0]["invalid"]))
        self.assertEqual((1, 1), (summary[1]["refused"], summary[1]["unanswered"]))
        self.assertEqual(0.5, summary[0]["correct_rate"])
        self.assertEqual((1, 1), (pairs[0]["lost"], pairs[0]["incomplete"]))
        self.assertEqual(2, pairs[1]["incomplete"])
        self.assertIsNone(pairs[1]["retention"])

    def test_duplicate_unknown_ids_and_mixed_models_are_rejected(self):
        for answers in ([answer("a-raw", "yes")] * 2, [answer("unknown", "yes")],
                        [answer("a-raw", "yes"), answer("a-redacted", "yes", model="different")]):
            with self.subTest(answers=answers), self.assertRaises(ValueError):
                score_recorded(plan(), answers)

    def test_incomplete_or_mismatched_pairs_are_rejected_before_export(self):
        incomplete = plan()
        incomplete["requests"].pop()
        with self.assertRaisesRegex(ValueError, "raw, redacted and pseudonymized"):
            utility_requests(incomplete)
        inconsistent = plan()
        inconsistent["requests"][0]["ground_truth"] = ["changed"]
        with self.assertRaisesRegex(ValueError, "identical accepted answers"):
            utility_requests(inconsistent)
        different_question = plan()
        different_question["requests"][0]["prompt"] = "A different question"
        with self.assertRaisesRegex(ValueError, "identical question"):
            utility_requests(different_question)

    def test_pack_keeps_truth_out_of_prompts_and_report_preserves_unrun_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "pack"
            original = plan()
            build_pack(original, directory)
            self.assertEqual(original, json.loads((directory / "plan.json").read_text()))
            with (directory / "answers.csv").open(newline="") as stream:
                answers = list(csv.DictReader(stream))
            self.assertEqual(6, len(answers))
            self.assertNotIn("ground_truth", answers[0])
            for path in (directory / "prompts").iterdir():
                self.assertNotIn("ground_truth", path.read_text())
                self.assertNotIn("yes", path.read_text())
            with self.assertRaises(FileExistsError):
                build_pack(original, directory)
            scored = score_recorded(original, answers)
            report = Path(temporary) / "report"
            write_report(scored, report)
            with (report / "paired.csv").open(newline="") as stream:
                pairs = list(csv.DictReader(stream))
            self.assertEqual(["2", "2"], [row["incomplete"] for row in pairs])
            self.assertIn("0/2", (report / "summary.md").read_text())
            with self.assertRaises(FileExistsError):
                write_report(scored, report)


if __name__ == "__main__":
    unittest.main()
