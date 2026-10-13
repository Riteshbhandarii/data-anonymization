"""Exercise the real Streamlit workflow with fictional text and a stub detector."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class FixtureDetector:
    def detect(self, text, language="en"):
        values = (("Alice Example", "PERSON"), ("alice@example.test", "EMAIL_ADDRESS"))
        return [SimpleNamespace(start=text.index(value), end=text.index(value) + len(value),
                                entity_type=kind, score=1.0)
                for value, kind in values if value in text]


class AppWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        script = root / "app" / "testbench.py"
        script.parent.mkdir()
        script.write_text((Path(__file__).resolve().parents[1] / "app" / "testbench.py").read_text())
        corpus = root / "outputs" / "app-corpus"
        (corpus / "labels").mkdir(parents=True)
        (corpus / "txt").mkdir()
        self.source = corpus / "txt" / "Alice_Example.txt"
        self.source.write_text("Contact Alice Example at alice@example.test.")
        (corpus / "corpus.json").write_text("{}")
        (corpus / "labels" / "example.json").write_text(json.dumps({
            "file": "txt/Alice_Example.txt", "language": "en", "entities": [
                {"type": "PERSON", "value": "Alice Example", "location": "body"},
                {"type": "EMAIL", "value": "alice@example.test", "location": "body"}]}))
        self.app = AppTest.from_file(str(script), default_timeout=20)

    def run_document(self):
        with patch("detect.methods.get_detector", return_value=FixtureDetector()):
            self.app.run()
            self.app.sidebar.radio[0].set_value("Synthetic corpus").run()
            self.app.sidebar.button[0].click().run()
        self.assertEqual([], list(self.app.exception))

    def test_settings_change_hides_previous_output_and_rerun_preserves_it(self):
        with patch("streamlit.download_button", return_value=False) as download:
            self.run_document()
        self.assertEqual("anonymized.md", download.call_args.kwargs["file_name"])
        original = self.app.session_state["res"]
        saved = original["saved"]
        content = saved.read_text()
        self.assertNotIn("Alice Example", content)
        self.app.sidebar.radio[2].set_value("Use consistent pseudonyms").run()
        self.assertTrue(any("settings changed" in item.value for item in self.app.info))
        self.assertEqual([], list(self.app.metric))
        with patch("detect.methods.get_detector", return_value=FixtureDetector()):
            self.app.sidebar.button[0].click().run()
        self.assertEqual([], list(self.app.exception))
        self.assertNotEqual(saved, self.app.session_state["res"]["saved"])
        self.assertEqual(content, saved.read_text())

    def test_replaced_input_hides_previous_output(self):
        self.run_document()
        self.source.write_text("A different input document.")
        self.app.run()
        self.assertEqual([], list(self.app.exception))
        self.assertTrue(any("document or settings changed" in item.value for item in self.app.info))
        self.assertEqual([], list(self.app.metric))

    def test_save_failure_is_visible_without_crashing_the_clean_preview(self):
        with patch("pipeline.core._save_markdown", side_effect=OSError("disk full")):
            self.run_document()
        self.assertTrue(any("Saving failed: disk full" in item.value for item in self.app.error))
        self.assertIn("clean", self.app.session_state["res"])


if __name__ == "__main__":
    unittest.main()
