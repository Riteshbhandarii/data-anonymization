"""Validate experiment controls and provider boundaries without external calls."""

import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from eval.create_study import create_suite
from eval.study import OpenAIProvider, prepare, run, score_answer, summarize


class FixtureDetector:
    """An oracle for plumbing tests, never a claimed detection baseline."""

    def detect(self, text, language="en"):
        return [
            {"start": match.start(), "end": match.end(), "entity_type": "PERSON", "score": 1.0}
            for match in re.finditer(r"(?:Alice|Bob|Carla|David) Example", text)
        ]


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.suite_path = create_suite(Path(self.temporary.name) / "suite")
        self.plan = prepare(self.suite_path, FixtureDetector())

    def test_controls_pairs_and_identical_utility_questions(self):
        requests = self.plan["requests"]
        self.assertEqual(84, len(requests))
        self.assertEqual({"yes", "no"}, {
            row["ground_truth"][0] for row in requests if row["prompt_type"] == "linkage"
        })
        naming = [row for row in requests if row["document_id"] == "a1" and row["prompt_type"] == "naming:company"]
        self.assertEqual({"raw", "target", "unrelated"}, {row["control"] for row in naming})
        unrelated = next(row for row in naming if row["control"] == "unrelated")
        self.assertEqual("b1", unrelated["input_id"])
        self.assertIn("Birch Example Foods", unrelated["prompt"])
        self.assertNotIn("Aster Example Analytics", unrelated["prompt"])
        self.assertEqual(["Aster Example Analytics"], unrelated["ground_truth"])
        utility = [row for row in requests if row["document_id"] == "a2" and row["prompt_type"] == "same_contact"]
        self.assertEqual(3, len(utility))
        self.assertEqual(1, len({row["prompt"].split("\n\nDocument data")[0] for row in utility}))
        pseudonym = next(row for row in utility if row["sanitization_config"]["variant"] == "pseudonymized")
        self.assertIn("[PERSON_1]", pseudonym["prompt"])
        self.assertIn("[PERSON_2]", pseudonym["prompt"])
        for document in json.loads(self.suite_path.read_text(encoding="utf-8"))["documents"]:
            content = (self.suite_path.parent / document["file"]).read_text(encoding="utf-8")
            self.assertNotIn(f"memo {document['id']}", content)
            self.assertEqual("# Project allocation memo", content.splitlines()[0])

    def test_exact_scoring_errors_and_refusals_are_distinct(self):
        self.assertEqual("correct", score_answer({"answer": "  YES. ", "refused": False}, ["yes"]))
        self.assertEqual("wrong", score_answer({"answer": "yes or no", "refused": False}, ["yes"]))
        self.assertEqual("refused", score_answer({"answer": "", "refused": True}, ["yes"]))
        self.assertEqual("invalid", score_answer({"answer": "yes", "refused": "false"}, ["yes"]))
        self.assertEqual("invalid", score_answer({"answer": "", "refused": False}, ["yes"]))

    def test_limit_checked_before_calls_and_truth_never_passed(self):
        calls = []

        def answer(prompt, *, web_search):
            calls.append((prompt, web_search))
            raise RuntimeError("provider failure")

        provider = SimpleNamespace(model="offline-test", answer=answer)
        with self.assertRaises(ValueError):
            run(self.plan, provider, max_requests=1)
        self.assertEqual([], calls)
        result_file = Path(self.temporary.name) / "answers.jsonl"
        rows = run(self.plan, provider, max_requests=100, output_path=result_file)
        self.assertEqual(84, len(calls))
        self.assertTrue(all(row["score"] == "error" for row in rows))
        self.assertEqual(84, sum(row["error"] for row in summarize(rows)))
        self.assertEqual(84, len(result_file.read_text(encoding="utf-8").splitlines()))
        self.assertTrue(all(not enabled for (prompt, enabled), row in zip(calls, rows) if row["task"] == "utility"))

    def test_subject_balance_and_paths_are_validated(self):
        suite = json.loads(self.suite_path.read_text(encoding="utf-8"))
        suite["documents"][0]["file"] = "../outside.md"
        self.suite_path.write_text(json.dumps(suite), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside"):
            prepare(self.suite_path, FixtureDetector())

    def test_provider_records_actual_search_and_does_not_receive_truth(self):
        arguments = []
        payload = {"id": "offline-response", "model": "offline-test", "status": "completed",
                   "output": [{"type": "web_search_call", "status": "completed", "action": {"type": "search"}}],
                   "usage": {"input_tokens": 10, "output_tokens": 4}}
        response = SimpleNamespace(output_text='{"answer":"yes","refused":false}',
                                   model_dump=lambda **kwargs: payload)
        client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: arguments.append(kwargs) or response))
        result = OpenAIProvider("offline-test", client=client).answer("Question only", web_search=True)
        self.assertTrue(result["web_search_used"])
        self.assertFalse(arguments[0]["store"])
        self.assertEqual([{"type": "web_search"}], arguments[0]["tools"])
        self.assertEqual("Question only", arguments[0]["input"])
        self.assertNotIn("ground_truth", arguments[0])
        payload["output"][0]["status"] = "failed"
        failed_search = OpenAIProvider("offline-test", client=client).answer("Q", web_search=True)
        self.assertTrue(failed_search["web_search_attempted"])
        self.assertFalse(failed_search["web_search_used"])
        payload["status"] = "incomplete"
        self.assertEqual("error", OpenAIProvider("offline-test", client=client).answer("Q", web_search=False)["status"])

    def test_answers_require_a_list_instead_of_a_single_string(self):
        suite = json.loads(self.suite_path.read_text(encoding="utf-8"))
        suite["documents"][0]["naming"]["company"] = "Aster Example Analytics"
        self.suite_path.write_text(json.dumps(suite), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "list of accepted answer strings"):
            prepare(self.suite_path, FixtureDetector())

    def test_required_search_failure_and_malformed_provider_results_are_counted(self):
        plan = {**self.plan, "requests": [self.plan["requests"][0]]}
        for result, expected in (
            ({"answer": {"answer": "Aster Example Analytics", "refused": False},
              "web_search_used": False}, "error"),
            ({"answer": {"answer": "", "refused": True}, "web_search_used": False}, "refused"),
            ({"status": "unexpected"}, "invalid"),
            ("not a response object", "invalid"),
        ):
            with self.subTest(response=result):
                provider = SimpleNamespace(model="offline-test", answer=lambda *args, _result=result, **kwargs: _result)
                rows = run(plan, provider)
                self.assertEqual(expected, rows[0]["score"])
                self.assertEqual(1, summarize(rows)[0][expected])
        provider = SimpleNamespace(model="offline-test", answer=lambda *args, **kwargs: {
            "answer": {"answer": "Aster Example Analytics", "refused": False},
            "web_search_used": False,
        })
        self.assertEqual("correct", run(plan, provider, web_search=False)[0]["score"])


if __name__ == "__main__":
    unittest.main()
