"""Incomplete free-tool batches fail after writing their diagnostic reports."""

import io
import json
import os
import runpy
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "eval" / "free_tools"


class FreeToolResearchTests(unittest.TestCase):
    def execute(self, script, root, modules, should_fail):
        original_cwd = Path.cwd()
        try:
            os.chdir(root)
            with patch.dict("sys.modules", modules), redirect_stdout(io.StringIO()), \
                    redirect_stderr(io.StringIO()):
                if should_fail:
                    with self.assertRaises(SystemExit) as error:
                        runpy.run_path(str(script), run_name="__main__")
                    self.assertEqual(error.exception.code, 1)
                else:
                    runpy.run_path(str(script), run_name="__main__")
        finally:
            os.chdir(original_cwd)

    def test_runner_error_status_is_saved_before_nonzero_exit(self):
        scripts = sorted(ROOT.glob("*/test_*.py"))
        self.assertTrue(scripts)
        for source in scripts:
            for should_fail in (False, True):
                with self.subTest(script=source.name, should_fail=should_fail), \
                        tempfile.TemporaryDirectory() as folder:
                    root = Path(folder)
                    script = root / source.name
                    script.write_bytes(source.read_bytes())
                    (root / "csv").mkdir()
                    (root / "csv" / "en_csv_00.csv").write_text("name,email\nSynthetic,user@example.test\n")
                    scrubadub = ModuleType("scrubadub")
                    scrubadub.clean = Mock(return_value="redacted")
                    datafog = ModuleType("datafog_core")
                    datafog.scan = Mock(return_value=[])
                    if should_fail:
                        scrubadub.clean.side_effect = RuntimeError("detector failed")
                        datafog.scan.side_effect = RuntimeError("detector failed")
                    self.execute(script, root, {"scrubadub": scrubadub, "datafog_core": datafog},
                                 should_fail)
                    summary = next(root.glob("*_results/*_summary.csv"))
                    self.assertIn("ERROR" if should_fail else "SUCCESS", summary.read_text())

    def test_empty_runner_input_fails_after_writing_summary(self):
        for source in sorted(ROOT.glob("*/test_*.py")):
            with self.subTest(script=source.name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                script = root / source.name
                script.write_bytes(source.read_bytes())
                scrubadub = ModuleType("scrubadub")
                datafog = ModuleType("datafog_core")
                datafog.scan = Mock()
                self.execute(script, root, {"scrubadub": scrubadub, "datafog_core": datafog},
                             should_fail=True)
                self.assertTrue(list(root.glob("*_results/*_summary.csv")))

    def test_evaluator_incomplete_results_fail_after_report(self):
        scripts = sorted(ROOT.glob("*/evaluate_*.py"))
        self.assertTrue(scripts)
        for source in scripts:
            for mode in ("success", "missing", "malformed"):
                with self.subTest(script=source.name, mode=mode), \
                        tempfile.TemporaryDirectory() as folder:
                    root = Path(folder)
                    script = root / source.name
                    script.write_bytes(source.read_bytes())
                    (root / "labels").mkdir()
                    label = {"file": "csv/en_csv_00.csv", "language": "en", "format": "csv",
                             "entities": [{"type": "EMAIL", "value": "user@example.test",
                                           "location": "body"}]}
                    (root / "labels" / "en_csv_00.json").write_text(
                        "not JSON" if mode == "malformed" else json.dumps(label)
                    )
                    if mode == "success":
                        tool = source.parent.name
                        results = root / f"{tool}_results"
                        results.mkdir()
                        (results / f"en_csv_00_{tool}_result.txt").write_text(
                            f"ORIGINAL\n===\nuser@example.test\n===\nANONYMIZED BY {tool.upper()}"
                            "\n===\n[EMAIL]\n===\nDATAFOG FINDINGS\n===\n[]\n"
                        )
                    self.execute(script, root, {}, should_fail=mode != "success")
                    self.assertTrue(list(root.glob("*_evaluation*/*entity_level*.csv")))
