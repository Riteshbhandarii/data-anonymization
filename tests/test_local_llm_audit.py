"""Local completion errors and invalid spans must not inflate benchmark scores."""

import json
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from detect.local_llm import LocalLLMDetector


def span(start, end, kind="PERSON"):
    return SimpleNamespace(start=start, end=end, entity_type=kind, score=0.9)


class LocalResponseAuditTests(unittest.TestCase):
    def test_malformed_envelopes_raise_a_countable_error(self):
        bad = [None, [], {}, {"choices": None}, {"choices": []}, {"choices": [None]},
               {"choices": [{"finish_reason": "stop", "message": None}]},
               {"choices": [{"finish_reason": "stop", "message": {"content": None}}]}]
        for result in bad:
            with self.subTest(result=result), patch("detect.local_llm.json.load", return_value=result):
                detector = LocalLLMDetector("local")
                detector.opener = SimpleNamespace(open=lambda *a, **k: nullcontext(None))
                with self.assertRaises((ValueError, TypeError)):
                    detector.detect("Aino")

    def test_invalid_detector_spans_do_not_inflate_local_recall(self):
        import hashlib

        from eval.local_llm_bench import benchmark

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "labels").mkdir()
            (root / "text").mkdir()
            (root / "index.csv").write_text("file\na.md\n")
            label = json.dumps({"language": "fi", "entities": [
                {"type": "PERSON", "value": "Aino", "location": "body"}]})
            (root / "labels/a.json").write_text(label)
            (root / "text/a.txt").write_text("Aino")
            digest = hashlib.sha256(label.encode() + b"Aino").hexdigest()
            (root / "corpus.json").write_text(json.dumps({"corpus_sha256": digest}))
            detector = SimpleNamespace(detect=lambda text, lang: [span(-1, 50)])
            report = benchmark(root, detector)
            self.assertEqual(1, report["failed_documents"])
            self.assertEqual(0, report["recall"][0]["covered"])
            self.assertEqual(1, report["recall"][0]["planted"])
            from eval.bench import main

            (root / "text/a.txt").write_text("edited")
            with patch("eval.bench.build_analyzer") as analyzer, self.assertRaises(SystemExit):
                main(root)
            analyzer.assert_not_called()

    def test_final_pass_rejects_invalid_base_scores_before_the_model_call(self):
        from detect.local_llm import FinalPassDetector

        invalid = span(0, 4)
        invalid.score = float("nan")
        base = SimpleNamespace(detect=lambda text, language: [invalid])
        with patch.object(LocalLLMDetector("local"), "detect") as final:
            with self.assertRaises(ValueError):
                FinalPassDetector(base, SimpleNamespace(detect=final)).detect("Aino")
            final.assert_not_called()


if __name__ == "__main__":
    unittest.main()
