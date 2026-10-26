"""Evaluation integrity checks use tiny local caches without NLP dependencies."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval import context_model_validation as model_validation
from eval.context_guard_validation import FIXTURE_SCOPE, ValidationError, load_fixture


def fixture():
    return {"schema_version": 1, "scope": FIXTURE_SCOPE, "cases": [{
        "id": "local-check", "language": "en", "category": "person_name",
        "text": "Example", "spans": [{"start": 0, "end": 7, "entity_type": "PERSON",
                                       "expect": "preserve_detection"}],
    }]}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExplicitFixtureTests(unittest.TestCase):
    def test_new_fixture_requires_its_explicit_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixture.json"
            digest = write_json(source, fixture())
            with self.assertRaisesRegex(ValidationError, "SHA256 mismatch"):
                load_fixture(source)
            self.assertEqual(load_fixture(source, expected_sha256=digest), fixture())

    def test_explicit_hash_does_not_bypass_language_or_offset_validation(self):
        for field, replacement in (("language", "xx"), ("spans", [{
            "start": 0, "end": 8, "entity_type": "PERSON", "expect": "preserve_detection",
        }])):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                value = fixture()
                value["cases"][0][field] = replacement
                source = Path(directory) / "fixture.json"
                digest = write_json(source, value)
                with self.assertRaises(ValidationError):
                    load_fixture(source, expected_sha256=digest)


class ModelReplayIntegrityTests(unittest.TestCase):
    policy = b"def filter_context_spans(text, spans):\n    return list(spans)\n"

    def prepare(self, root):
        example = fixture()
        case = example["cases"][0]
        digest = hashlib.sha256(json.dumps(example).encode()).hexdigest()
        document = {**case, "text_sha256": hashlib.sha256(case["text"].encode()).hexdigest(),
                    "presidio": [], "model": [], "routed": [{
                        "start": 0, "end": 7, "entity_type": "PERSON", "score": 0.9,
                    }]}
        raw_hash = write_json(root / "raw_components.json", {
            "created_utc": "capture-time", "fixture_sha256": digest, "documents": [document],
        })
        provenance = {
            "raw_sha256": raw_hash, "fixture_sha256": digest, "device": "cpu", "offline": True,
            "torch_threads": 4, "gliner_model": "cached-model", "gliner_threshold": 0.4,
            "presidio_threshold": 0.0, "versions": {"torch": "captured-version"},
            "component_source_hashes": {"detect/combined.py": "captured-source-hash"},
        }
        write_json(root / "provenance.json", provenance)
        return example, digest, provenance

    def git_result(self, arguments, **kwargs):
        return self.policy if arguments[1] == "show" else b"baseline-commit\n"

    def test_replay_preserves_capture_versions_and_historical_unknown_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            example, digest, provenance = self.prepare(root)
            with patch.object(model_validation, "OUT", root), patch.object(
                    model_validation.subprocess, "check_output", side_effect=self.git_result):
                report = model_validation.score(example, digest, self.policy, baseline_ref="8051239")
            self.assertEqual(report["baseline_ref"], "8051239")
            self.assertEqual(report["baseline_commit"], "baseline-commit")
            self.assertEqual(report["versions"], provenance["versions"])
            self.assertIsNone(report["runtime"]["python"])
            self.assertEqual(report["capture_created_utc"], "capture-time")
            self.assertEqual(report["evaluation_stage"], "development-replay")
            self.assertFalse(model_validation.has_privacy_regression(report))

    def test_replay_rejects_changed_cache_and_mismatched_provenance_fixture(self):
        for mismatch in ("cache", "provenance"):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                example, digest, provenance = self.prepare(root)
                if mismatch == "cache":
                    with (root / "raw_components.json").open("a", encoding="utf-8") as output:
                        output.write("\n")
                else:
                    provenance["fixture_sha256"] = "0" * 64
                    write_json(root / "provenance.json", provenance)
                with (patch.object(model_validation, "OUT", root), patch.object(
                        model_validation.subprocess, "check_output", side_effect=self.git_result),
                        self.assertRaisesRegex(ValidationError, "SHA256 mismatch")):
                    model_validation.score(example, digest, self.policy)

    def test_gate_rejects_partial_or_typed_losses_from_raw_or_baseline(self):
        report = {"groups": {"overall": {}}}
        self.assertFalse(model_validation.has_privacy_regression(report))
        for reference in ("routed", "baseline"):
            for metric in ("any_overlap", "typed_overlap", "any_full_coverage", "typed_full_coverage"):
                with self.subTest(reference=reference, metric=metric):
                    changed = copy.deepcopy(report)
                    changed["groups"]["overall"][
                        f"current_sensitive_losses_vs_{reference}_{metric}"] = 1
                    self.assertTrue(model_validation.has_privacy_regression(changed))


class IndependentPrivacyTargetsTests(unittest.TestCase):
    def annotation(self):
        return {"schema_version": 1, "fixture_sha256": "f" * 64,
                "scope": "independent sensitive-range annotation", "cases": [{
                    "id": "local-check", "text_sha256": hashlib.sha256(b"Example").hexdigest(),
                    "targets": [{"start": 0, "end": 7, "entity_type": "PERSON"}],
                }]}

    def test_annotation_hash_fixture_text_ids_and_offsets_are_validated(self):
        for mismatch in (None, "hash", "fixture", "text", "id", "offset"):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory() as directory:
                value = self.annotation()
                if mismatch == "fixture":
                    value["fixture_sha256"] = "0" * 64
                if mismatch == "text":
                    value["cases"][0]["text_sha256"] = "0" * 64
                if mismatch == "id":
                    value["cases"][0]["id"] = "unknown"
                if mismatch == "offset":
                    value["cases"][0]["targets"][0]["end"] = 8
                path = Path(directory) / "privacy.json"
                digest = write_json(path, value)
                if mismatch == "hash":
                    digest = "0" * 64
                if mismatch is None:
                    _, by_id = model_validation.load_privacy_targets(path, digest, fixture(), "f" * 64)
                    self.assertEqual(by_id["local-check"], value["cases"][0]["targets"])
                else:
                    with self.assertRaises(ValidationError):
                        model_validation.load_privacy_targets(path, digest, fixture(), "f" * 64)

    def test_exact_character_gate_catches_loss_hidden_by_equal_coarse_metrics(self):
        from types import SimpleNamespace

        left = SimpleNamespace(start=0, end=2, entity_type="PERSON")
        right = SimpleNamespace(start=5, end=7, entity_type="PERSON")
        target = {"start": 0, "end": 7, "entity_type": "PERSON"}
        self.assertEqual(model_validation.metrics([left, right], target, "PERSON")["any_full_coverage"],
                         model_validation.metrics([left], target, "PERSON")["any_full_coverage"])
        counts = model_validation.privacy_character_metrics(
            {"routed": [left, right], "old": [left, right], "current": [left]}, [target])
        self.assertEqual(counts["current_lost_any_characters_vs_baseline"], 2)
        self.assertEqual(counts["current_lost_typed_characters_vs_routed"], 2)
        report = {"groups": {"overall": {}}, "independent_privacy_targets": {
            "groups": {"overall": counts}}}
        self.assertTrue(model_validation.has_privacy_regression(report))
        report = {"groups": {"overall": {}}, "candidate_range_character_retention": {
            "groups": {"overall": counts}}}
        self.assertTrue(model_validation.has_privacy_regression(report))


if __name__ == "__main__":
    unittest.main()
