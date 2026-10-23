"""Privacy gate for frozen supplied candidates, not detector-recall accuracy."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter

from eval.context_guard_validation import (
    DEFAULT_FIXTURE,
    ENTITY_TYPE_NORMALIZATION,
    EVALUATION_SCOPE,
    FROZEN_FIXTURE_SHA256,
    evaluate_cases,
    load_current_filter,
    load_fixture,
    normalized_entity_type,
)


class ContextHoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Schema checks can run independently; evaluating either policy is lazy.
        cls.fixture = load_fixture()
        cls.current_results = None

    @classmethod
    def results(cls):
        if cls.current_results is None:
            current_filter = load_current_filter()
            cls.current_results = evaluate_cases(
                cls.fixture["cases"], current_filter, current_filter
            )
        return cls.current_results

    def test_frozen_fixture_schema_hash_and_unicode_offsets(self):
        raw = DEFAULT_FIXTURE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), FROZEN_FIXTURE_SHA256)
        self.assertNotIn(b"\r", raw)
        self.assertEqual(self.fixture["schema_version"], 1)
        self.assertEqual(len(self.fixture["cases"]), 120)
        self.assertEqual(
            Counter(case["language"] for case in self.fixture["cases"]),
            {"en": 60, "fi": 60},
        )
        for case in self.fixture["cases"]:
            for span in case["spans"]:
                with self.subTest(case=case["id"]):
                    self.assertIs(type(span["start"]), int)
                    self.assertIs(type(span["end"]), int)
                    self.assertGreaterEqual(span["start"], 0)
                    self.assertGreater(span["end"], span["start"])
                    self.assertLessEqual(span["end"], len(case["text"]))
                    selected = case["text"][span["start"] : span["end"]]
                    self.assertEqual(len(selected), span["end"] - span["start"])

    def test_age_normalization_is_uniform(self):
        self.assertEqual(ENTITY_TYPE_NORMALIZATION, {"AGE": "DATE_TIME"})
        age_spans = [
            span
            for case in self.fixture["cases"]
            for span in case["spans"]
            if span["entity_type"] == "AGE"
        ]
        self.assertEqual(len(age_spans), 34)
        self.assertEqual(
            Counter(span["expect"] for span in age_spans),
            {"preserve_detection": 12, "discard_detection": 22},
        )
        for span in age_spans:
            self.assertEqual(normalized_entity_type(span["entity_type"]), "DATE_TIME")
        for entity_type in ("DATE_TIME", "PERSON", "LOCATION"):
            self.assertEqual(normalized_entity_type(entity_type), entity_type)

    def test_current_retains_every_sensitive_candidate(self):
        results = self.results()
        for language, categories in results["by_language_category"].items():
            for category, metrics in categories.items():
                with self.subTest(language=language, category=category):
                    self.assertEqual(
                        metrics["current"]["preserve_dropped"],
                        0,
                        "Current policy dropped sensitive supplied candidates; "
                        + json.dumps(metrics, sort_keys=True),
                    )
        self.assertEqual(results["overall"]["new_sensitive_losses"], 0)

    def test_utility_is_reported_without_a_perfect_score_gate(self):
        current = self.results()["overall"]["current"]
        # Utility is an observed count, not an assertion of a target success rate.
        print(
            json.dumps(
                {
                    "evaluation_scope": EVALUATION_SCOPE,
                    "utility": {
                        "discard_dropped": current["discard_dropped"],
                        "discard_total": current["discard_total"],
                        "discard_retained": current["discard_retained"],
                    },
                },
                sort_keys=True,
            )
        )
        self.assertEqual(
            current["discard_dropped"] + current["discard_retained"],
            current["discard_total"],
        )


if __name__ == "__main__":
    unittest.main()
