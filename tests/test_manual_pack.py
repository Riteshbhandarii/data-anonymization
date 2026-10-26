"""Validate manual controls and preserve recorded experiment answers."""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval.make_pack import FAKE_PICKS, REAL_PICKS, best_method, build_pack


class ManualPackTests(unittest.TestCase):
    def test_incomplete_method_cannot_win_the_comparison(self):
        rows = [{"dataset": "fake", "method": "partial", "planted": "10", "covered": "10"},
                {"dataset": "fake", "method": "complete", "planted": "10", "covered": "8"},
                {"dataset": "tab", "method": "complete", "planted": "10", "covered": "8"}]
        self.assertEqual("complete", best_method(rows))
        with self.assertRaisesRegex(ValueError, "every labelled dataset"):
            best_method([])

    def test_existing_pack_answers_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary) / "pack"
            pack.mkdir()
            answers = pack / "answers.csv"
            answers.write_text("already recorded responses")
            with self.assertRaises(FileExistsError):
                build_pack(Path(temporary) / "nonexistent-runs", pack)
            self.assertEqual("already recorded responses", answers.read_text())

    def test_unrelated_control_truth_is_the_original_target_and_prompt_has_no_truth(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs, corpus, real = root / "runs", root / "fake-corpus", root / "real"
            runs.mkdir()
            (corpus / "labels").mkdir(parents=True)
            (corpus / "docx").mkdir()
            (real / "pptx").mkdir(parents=True)
            (runs / "results.csv").write_text("dataset,method,planted,covered\nfake,test,10,8\n")
            index = []
            for language, fmt in FAKE_PICKS:
                for number in range(6 if (language, fmt) == ("en", "docx") else 1):
                    stem = f"{language}_{fmt}_{number:02d}"
                    index.append({"file": f"{fmt}/{stem}.{fmt}", "language": language, "format": fmt})
                    labels = {"entities": [
                        {"type": "COMPANY", "value": f"Company {stem}", "location": "body"},
                        {"type": "PERSON", "value": f"Person {stem}", "location": "body"}]}
                    (corpus / "labels" / f"{stem}.json").write_text(json.dumps(labels))
                    folder = runs / "fake" / "test"
                    folder.mkdir(parents=True, exist_ok=True)
                    (folder / f"{stem}_anonymized.md").write_text(f"Sanitized input {stem}")
            with (corpus / "index.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["file", "language", "format"])
                writer.writeheader()
                writer.writerows(index)
            with (real / "manifest.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["filename", "publisher", "dataset_title"])
                writer.writeheader()
                for doc_id, stem in REAL_PICKS.items():
                    writer.writerow({"filename": f"{stem}.csv", "publisher": "Public publisher", "dataset_title": doc_id})
                    folder = runs / "real-uk" / "test"
                    folder.mkdir(parents=True, exist_ok=True)
                    (folder / f"{stem}_anonymized.md").write_text(
                        "## Document metadata\n- Keywords: shared-template-code\n"
                        "## Document content\nPublic sanitized input")
            pack = root / "pack"
            with patch("eval.make_pack.REAL_UK", real), \
                    patch("pipeline.extractors.extract_to_markdown", return_value="Fictional raw control"):
                build_pack(runs, pack)
            with (pack / "ground_truth.csv").open(newline="") as stream:
                truth = {row["doc_id"]: row for row in csv.DictReader(stream)}
            control_id = "control-F01-C01-naming-company"
            self.assertEqual(truth["F01"]["organisation"], truth[control_id]["organisation"])
            self.assertNotEqual(truth["C01"]["organisation"], truth[control_id]["organisation"])
            prompt = (pack / "paste" / f"{control_id}.txt").read_text()
            self.assertIn("en_docx_05", prompt)
            self.assertNotIn(truth["F01"]["organisation"], prompt)
            self.assertIn(control_id, (pack / "prompts.md").read_text())
            self.assertIn("not-run", (pack / "README.md").read_text())
            linkage = (pack / "paste/link-R01-R02.txt").read_text()
            self.assertNotIn("shared-template-code", linkage)
            self.assertIn("Public sanitized input", linkage)
            self.assertIn("Paste the cleaned text, never upload the original file.",
                          (pack / "prompts.md").read_text())
            with patch("eval.make_pack.REAL_UK", real), \
                    patch("pipeline.extractors.extract_to_markdown", return_value="Fictional raw control"):
                build_pack(runs, root / "pack-with-metadata", include_metadata=True)
            self.assertIn("shared-template-code",
                          (root / "pack-with-metadata/paste/link-R01-R02.txt").read_text())


if __name__ == "__main__":
    unittest.main()
