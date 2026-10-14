"""Regression tests for detector boundaries and labelled dataset accounting."""

import json
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from detect.gliner_detector import GlinerDetector, windows
from detect.privacy_filter import PrivacyFilterDetector
from eval.run_matrix import Doc, detect_long, run_dataset


def span(start, end, kind="PERSON"):
    return SimpleNamespace(start=start, end=end, entity_type=kind, score=0.9)


class CompleteNameModel:
    config = SimpleNamespace(max_len=384)

    def predict_entities(self, text, labels, threshold):
        start = text.find("Aino Virtanen")
        return [] if start < 0 else [{"start": start, "end": start + 13,
                                     "label": "person", "score": 0.9}]


class WindowAuditTests(unittest.TestCase):
    def test_gliner_detects_a_full_name_across_the_old_cut(self):
        text = "x " * 345 + "Aino Virtanen " + "x " * 20
        detector = GlinerDetector(device="cpu")
        detector._model = CompleteNameModel()
        with patch("detect.gliner_detector.pattern_spans", return_value=[]):
            result = detector.detect(text)
        self.assertEqual([(690, 703)], [(s.start, s.end) for s in result])

    def test_gliner_overlap_does_not_duplicate_identical_detections(self):
        text = "x " * 140 + "Aino Virtanen " + "x " * 100
        detector = GlinerDetector(device="cpu")
        detector._model = CompleteNameModel()
        with patch("detect.gliner_detector.pattern_spans", return_value=[]):
            result = detector.detect(text)
        self.assertEqual([(280, 293)], [(s.start, s.end) for s in result])

    def test_dense_punctuation_cannot_silently_truncate_the_identifier_tail(self):
        import re

        class TruncatingModel(CompleteNameModel):
            def predict_entities(self, text, labels, threshold):
                # Same word-splitting rule as the installed GLiNER processor.
                tokens = list(re.finditer(r"\w+(?:[-_]\w+)*|\S", text))
                if len(tokens) > self.config.max_len:
                    text = text[:tokens[self.config.max_len - 1].end()]
                return super().predict_entities(text, labels, threshold)

        text = "!" * 680 + " Aino Virtanen"
        detector = GlinerDetector(device="cpu")
        detector._model = TruncatingModel()
        with patch("detect.gliner_detector.pattern_spans", return_value=[]):
            result = detector.detect(text)
        self.assertEqual([(681, 694)], [(s.start, s.end) for s in result])

    def test_privacy_filter_cross_window_span_and_dedup(self):
        class Encoded(dict):
            def to(self, device):
                return self

        def tokenizer(piece, **kwargs):
            start = piece.find("Aino Virtanen")
            offsets = [(0, 0)] if start < 0 else [(start, start + 13)]
            return Encoded(piece=piece, offset_mapping=[SimpleNamespace(tolist=lambda: offsets)])

        class Tensor:
            def __init__(self, rows):
                self.rows = rows

            def __getitem__(self, index):
                return self

            def float(self):
                return self

            def log_softmax(self, dim):
                return self

            def tolist(self):
                return self.rows

        class Model:
            config = SimpleNamespace(id2label={0: "O", 1: "S-private_person"})

            def __call__(self, piece):
                rows = [[-20, 0]] if "Aino Virtanen" in piece else [[0, -20]]
                return SimpleNamespace(logits=Tensor(rows))

        detector = PrivacyFilterDetector()
        detector._tokenizer, detector._model = tokenizer, Model()
        with patch.dict("sys.modules", {"torch": SimpleNamespace(no_grad=nullcontext)}), \
                patch("detect.privacy_filter.pattern_spans", return_value=[]):
            for offset in [3990, 3900]:
                text = "x " * (offset // 2) + "Aino Virtanen " + "x " * 100
                result = detector.detect(text)
                self.assertEqual([(offset, offset + 13)], [(s.start, s.end) for s in result])

    def test_outer_chunk_boundary_preserves_and_deduplicates_identifiers(self):
        class Finder:
            def detect(self, text, language="en"):
                at = text.find("NAME")
                return [] if at < 0 else [span(at, at + 4)]

        for offset in [99_998, 99_996]:
            text = "x" * offset + "NAME" + "x" * 30
            result = detect_long(Finder(), text, "en")
            self.assertEqual([(offset, offset + 4)], [(s.start, s.end) for s in result])

    def test_short_initial_lines_do_not_cause_thousands_of_overlapping_calls(self):
        from eval.run_matrix import split_text

        text = "x\n" * 1000 + "y" * 200_000
        result = list(split_text(text, 100_000, overlap=1000))
        self.assertEqual(3, len(result))
        self.assertTrue(all(text[offset:offset + len(piece)] == piece for offset, piece in result))

    def test_invalid_window_configuration_fails_instead_of_looping(self):
        for size, overlap in [(0, 0), (10, 10), (10, -1)]:
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                list(windows("text", size, overlap=overlap))


class MatrixAuditTests(unittest.TestCase):
    def test_negative_documents_count_towards_precision(self):
        docs = [Doc("positive", "fi", "word", annotated=[(0, 4)]),
                Doc("negative", "fi", "word", annotated=[])]
        detector = SimpleNamespace(detect=lambda text, language: [span(0, 4)])
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict("eval.run_matrix.LOADERS", {"turku": lambda args: docs}), \
                patch("eval.run_matrix.get_method", return_value=detector), \
                patch("redact.redact", return_value="[PERSON]"):
            precision = run_dataset("turku", ["basic"], SimpleNamespace(limit=0), Path(directory))[3]
        self.assertEqual([{"dataset": "turku", "method": "basic", "language": "fi",
                           "detections": 2, "unlabelled": 1}], precision)

    def test_negative_only_run_keeps_its_precision_in_the_summary(self):
        from eval.run_matrix import (
            PRECISION_COLUMNS,
            RESULT_COLUMNS,
            merge_rows,
            write_summary,
        )

        docs = [Doc("positive", "fi", "word", annotated=[(0, 4)]),
                Doc("negative", "fi", "word", annotated=[])]
        detector = SimpleNamespace(detect=lambda text, language: [span(0, 4)])
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict("eval.run_matrix.LOADERS", {"turku": lambda args: docs}), \
                patch("eval.run_matrix.get_method", return_value=detector), \
                patch("redact.redact", return_value="[PERSON]"):
            root = Path(directory)
            rows, _, runtimes, precision = run_dataset("turku", ["basic"], SimpleNamespace(limit=0), root)
            # No requested recall labels, but detections still have annotations.
            self.assertEqual([], rows)
            merge_rows(root / "results.csv", RESULT_COLUMNS, (), set(), rows)
            merge_rows(root / "runtime.csv", list(runtimes[0]), (), set(), runtimes)
            merge_rows(root / "precision.csv", PRECISION_COLUMNS, (), set(), precision)
            write_summary(root)
            self.assertIn("50.0% (1/2)", (root / "summary.md").read_text())

    def test_failed_declared_real_document_is_not_silently_dropped(self):
        from eval.run_matrix import load_real_uk

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.csv").write_text("filename,format\nmissing.csv,csv\n")
            with patch("eval.run_matrix.REAL_UK", root), \
                    patch("pipeline.extractors.extract_to_markdown", side_effect=OSError("missing")), \
                    self.assertRaisesRegex(RuntimeError, "declared real-uk document"):
                load_real_uk(SimpleNamespace(max_chars=0))

    def test_empty_requested_dataset_fails_before_loading_models(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict("eval.run_matrix.LOADERS", {"turku": lambda args: []}), \
                patch("eval.run_matrix.get_method") as model:
            with self.assertRaisesRegex(ValueError, "no documents"):
                run_dataset("turku", ["basic"], SimpleNamespace(limit=0), Path(directory))
            model.assert_not_called()


class DatasetConfigurationAuditTests(unittest.TestCase):
    def test_ai4privacy_requires_documents_for_each_requested_language(self):
        from eval.run_matrix import load_ai4privacy

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ai4privacy").mkdir()
            (root / "ai4privacy/validation_en.jsonl").write_text(json.dumps({
                "uid": "negative", "source_text": "ordinary text", "privacy_mask": []}))
            (root / "ai4privacy/validation_fi.jsonl").write_text("")
            with patch("eval.run_matrix.CORPUS_ROOT", root), self.assertRaisesRegex(ValueError, "fi"):
                load_ai4privacy(SimpleNamespace(ai4p_rows=10))

    def test_invalid_sample_limits_fail_before_evaluation(self):
        import io
        from contextlib import redirect_stderr

        from eval.run_matrix import main

        for option, value in [("--limit", "-1"), ("--tab-docs", "-1"),
                              ("--max-chars", "-1"), ("--ai4p-rows", "0"),
                              ("--turku-sentences", "0")]:
            with self.subTest(option=option), patch("eval.run_matrix.run_dataset") as run, \
                    redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["--out", "unused", option, value])
            run.assert_not_called()

    def test_unlabelled_real_documents_do_not_become_negative_controls(self):
        doc = Doc("unlabelled", "en", "word")
        detector = SimpleNamespace(detect=lambda text, language: [span(0, 4)])
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict("eval.run_matrix.LOADERS", {"real-uk": lambda args: [doc]}), \
                patch("eval.run_matrix.get_method", return_value=detector), \
                patch("redact.redact", return_value="[PERSON]"):
            report = run_dataset("real-uk", ["basic"], SimpleNamespace(limit=0), Path(directory))
        self.assertEqual([], report[3])
        self.assertEqual(1, report[1][0]["count"])


if __name__ == "__main__":
    unittest.main()
