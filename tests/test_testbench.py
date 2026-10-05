"""Check the testbench's summaries and data views without model downloads."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app import testbench


class TestbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(testbench, "OUT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def app(self, res=None):
        app = AppTest.from_string("from app.testbench import main\nmain()", default_timeout=10)
        if res is not None:
            app.session_state["res"] = res
        return app.run()

    def result(self, labelled=True, real=False):
        text = "## Document content\nAnna met Eva.\n\n| Name |\n| --- |\n| Anna |"
        return {
            "cfg": {"path": self.root / "source.md", "method": "basic", "lang": "en",
                    "is_real": real, "mode": "replace"},
            "text": text, "clean": text.replace("Anna", "[PERSON]"),
            "results": [SimpleNamespace(start=text.index("Anna"), end=text.index("Anna") + 4,
                                        entity_type="PERSON", score=0.9)],
            "scored": [
                {"type": "PERSON", "value": "Anna", "location": "body", "status": "covered"},
                {"type": "PERSON", "value": "Eva", "location": "body", "status": "missed"},
                {"type": "EMAIL", "value": "missing@example.org", "location": "metadata", "status": "absent"},
            ] if labelled else None,
            "times": {"extract": 0.1, "detect": 0.2, "clean": 0.1}, "errors": {},
            "saved": self.root / "source_anonymized.md",
        }

    def test_upload_without_file_explains_disabled_run_and_offers_gliner(self):
        app = self.app()
        self.assertFalse(app.exception)
        button = next(button for button in app.button if button.label == "Run document")
        self.assertTrue(button.disabled)
        self.assertIn("Choose a document to enable Run.", [caption.value for caption in app.caption])
        detector = next(radio for radio in app.radio if radio.label == "Detector")
        self.assertIn("GLiNER + patterns", detector.options)
        self.assertEqual(["Extract", "Detect", "Clean", "Results", "Pack"], [tab.label for tab in app.tabs])

    def test_label_summary_keeps_extraction_misses_in_denominator(self):
        app = self.app(self.result())
        self.assertFalse(app.exception)
        detected = app.tabs[1]
        metrics = {metric.label: metric.value for metric in detected.metric}
        self.assertEqual(metrics, {"Detections": "1", "Found labels": "1 / 3",
                                   "Missed labels": "2", "Partial labels": "0"})
        self.assertEqual(1, len(detected.get("html")))
        self.assertEqual(4, len(app.tabs[2].metric))

    def test_real_document_has_one_warning_and_type_counts(self):
        app = self.app(self.result(labelled=False, real=True))
        self.assertFalse(app.exception)
        self.assertEqual(1, len(app.warning))
        self.assertEqual("Unlabelled", app.tabs[1].metric[-1].value)
        self.assertEqual(["Person (1)"], app.tabs[1].get("button_group")[-1].options)

    def test_chart_scale_is_percentage_and_entity_rows_start_with_largest_gap(self):
        folder = self.root / "runs"
        folder.mkdir()
        (folder / "results.csv").write_text(
            "dataset,method,entity_type,planted,covered,partial\n"
            "fake,basic,PERSON,10,9,0\n"
            "fake,rules,PERSON,10,10,0\n"
            "fake,basic,EMAIL,10,2,1\n", encoding="utf-8",
        )
        app = self.app()
        self.assertFalse(app.exception)
        table = app.tabs[3].dataframe[0].value
        self.assertEqual("EMAIL", table.iloc[0]["entity_type"])
        spec = testbench.recall_chart({("fake", "basic"): 0.5, ("fake", "rules"): 0.9}).to_dict()
        self.assertEqual([0, 1], spec["layer"][0]["encoding"]["color"]["scale"]["domain"])

    def test_pack_groups_files_and_renders_only_one_selected_view(self):
        pack = self.root / "pack"
        (pack / "docs").mkdir(parents=True)
        (pack / "paste").mkdir()
        (pack / "docs" / "F01.md").write_text("## Document\nSynthetic content", encoding="utf-8")
        (pack / "docs" / "F02.md").write_text("## Second document\nOther content", encoding="utf-8")
        (pack / "paste" / "F01.txt").write_text("What is the amount?", encoding="utf-8")
        app = self.app()
        self.assertFalse(app.exception)
        tab = app.tabs[4]
        self.assertEqual(1, len(tab.selectbox))
        self.assertEqual(1, len(tab.get("html")))
        self.assertEqual(0, len(tab.expander))


if __name__ == "__main__":
    unittest.main()
