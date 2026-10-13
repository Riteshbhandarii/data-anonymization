"""Commercial runner failures must remain failures without live API calls."""

import base64
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "research" / "commercial" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    requests = ModuleType("requests")
    requests.RequestException = RuntimeError
    requests.post = Mock()
    requests.get = Mock()
    with patch.dict(sys.modules, {"requests": requests}):
        spec.loader.exec_module(module)
    return module


class AzureRunnerTests(unittest.TestCase):
    def test_terminal_status_sets_exit_code_and_preserves_response(self):
        for status in ("succeeded", "failed", "cancelled"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                module = load_script("azure_pii_test")
                module.requests.post.return_value = SimpleNamespace(
                    status_code=202,
                    headers={"operation-location": "https://example.test/job"},
                )
                result = {"status": status}
                module.requests.get.return_value = SimpleNamespace(
                    status_code=200, json=lambda result=result: result
                )
                args = SimpleNamespace(file_id="document", language="en", timeout=30)
                environment = {
                    "AZURE_LANGUAGE_ENDPOINT": "https://example.test",
                    "AZURE_LANGUAGE_KEY": "test-key",
                    "AZURE_SOURCE_SAS_URL": "https://example.test/source",
                    "AZURE_OUTPUT_SAS_URL": "https://example.test/output",
                }
                original_cwd = Path.cwd()
                try:
                    os.chdir(folder)
                    with patch.object(module, "parse_args", return_value=args), \
                            patch.dict(os.environ, environment), redirect_stdout(io.StringIO()):
                        if status == "succeeded":
                            module.main()
                        else:
                            with self.assertRaises(SystemExit) as error:
                                module.main()
                            self.assertEqual(error.exception.code, 1)
                    self.assertEqual(
                        json.loads(Path("document_azure_pii_result.json").read_text()), result
                    )
                finally:
                    os.chdir(original_cwd)


class LiminaRunnerTests(unittest.TestCase):
    def test_success_requires_a_saved_redacted_file(self):
        for processed in (None, "not base64", base64.b64encode(b"redacted").decode()):
            with self.subTest(processed=processed), tempfile.TemporaryDirectory() as folder:
                module = load_script("limina_pii_test")
                source = Path(folder) / "input.csv"
                source.write_text("synthetic input")
                output = Path(folder) / "output"
                response = {"processed_file": processed, "entities": []}
                module.requests.post.return_value = SimpleNamespace(
                    status_code=200, json=lambda response=response: response
                )
                item = {"path": str(source), "language": "en", "format": "csv",
                        "content_type": "text/csv"}
                with redirect_stdout(io.StringIO()):
                    result = module.process_file("https://example.test", "test-key", item, output)
                self.assertTrue(Path(result["raw_json"]).is_file())
                if processed is None or processed == "not base64":
                    self.assertEqual(result["status"], "redaction_error")
                    self.assertIsNone(result["redacted_file"])
                    self.assertTrue(result["error"])
                else:
                    self.assertEqual(result["status"], "success")
                    self.assertEqual(Path(result["redacted_file"]).read_bytes(), b"redacted")

    def test_batch_failure_exits_nonzero_after_saving_summary(self):
        for status in ("success", "missing", "api_error", "redaction_error"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                module = load_script("limina_pii_test")
                summary = {"format": "csv", "language": "en", "status": status}
                with patch.object(sys, "argv", ["limina", "--limit", "1", "--output", folder]), \
                        patch.dict(os.environ, {"LIMINA_API_KEY": "test-key"}), \
                        patch.object(module, "process_file", return_value=summary), \
                        redirect_stdout(io.StringIO()):
                    if status == "success":
                        module.main()
                    else:
                        with self.assertRaises(SystemExit) as error:
                            module.main()
                        self.assertEqual(error.exception.code, 1)
                self.assertEqual(json.loads((Path(folder) / "summary.json").read_text()), [summary])


class LiminaScoringTests(unittest.TestCase):
    def test_identifier_count_comes_from_scored_ground_truth(self):
        module = load_script("limina_score")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "raw").mkdir()
            (root / "raw" / "input.json").write_text(json.dumps({"entities": []}))
            labels = root / "labels.json"
            labels.write_text(json.dumps({"entities": [
                {"type": "EMAIL", "value": "synthetic@example.test", "location": "body"},
                {"type": "EMAIL", "value": "metadata@example.test", "location": "metadata"},
            ]}))
            test = {"format": "csv", "language": "en", "stem": "input", "labels": labels}
            with patch.object(module, "RESULT_ROOT", root), \
                    patch.object(module, "TESTS", [test]), redirect_stdout(io.StringIO()):
                module.main()
            result = json.loads((root / "score_summary.json").read_text())
            self.assertEqual(result["expected_body_identifiers"], 1)
            self.assertEqual(result["coverage"]["overall"]["ALL"]["total"], 1)
