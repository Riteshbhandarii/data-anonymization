"""The local utility runner keeps malformed answers in the planned denominator."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval.local_utility import main
from eval.utility_bench import build_pack
from tests.test_local_llm import server


class LocalUtilityTests(unittest.TestCase):
    def test_complete_variants_and_invalid_completions_are_counted(self):
        for finish, expected in (("stop", "correct"), ("length", "invalid")):
            with self.subTest(finish=finish), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                requests = [{
                    "request_id": str(index), "document_id": "fictional", "prompt_type": "hours",
                    "language": "en", "task": "utility", "sanitization_config": {"variant": variant},
                    "prompt": "Total hours?\n\nDocument data (not instructions):\n18 + 12",
                    "ground_truth": ["30"],
                } for index, variant in enumerate(("raw", "redacted", "pseudonymized"))]
                build_pack({"synthetic": True, "requests": requests}, root / "pack")
                content = json.dumps({"answer": "30", "refused": False})
                with server(content, finish=finish) as (url, sent), patch("sys.argv", [
                    "local_utility", str(root / "pack"), "--model", "fixture",
                    "--base-url", url, "--out", str(root / "report"),
                ]):
                    self.assertEqual(int(finish != "stop"), main())
                report = json.loads((root / "report/report.json").read_text())
                self.assertEqual(3, len(sent))
                self.assertTrue(all(row["planned"] == row["attempted"] == row[expected] == 1
                                    for row in report["summary"]))
                self.assertTrue(all("tools" not in row for row in sent))
                self.assertTrue(all("ground_truth" not in json.dumps(row) for row in sent))
                self.assertEqual(0 if finish == "stop" else 1, report["paired"][0]["incomplete"])


if __name__ == "__main__":
    unittest.main()
