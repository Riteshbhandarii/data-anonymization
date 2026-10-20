"""Keep published independent cases as model-free privacy regressions."""

import unittest
from pathlib import Path

from eval.context_guard_validation import (
    evaluate_cases,
    load_current_filter,
    load_fixture,
)
from eval.context_model_validation import load_privacy_targets


class ContextHoldoutV2Tests(unittest.TestCase):
    def test_sensitive_candidates_stay_masked_and_prior_utility_is_preserved(self):
        source = Path(__file__).parent / "fixtures/context_holdout_v2.json"
        fixture = load_fixture(source, expected_sha256=(
            "c14a231b9d9b25ae7a6a8702f3d617c0f56043507c1d7c2e54122cf9695d031b"))
        policy = load_current_filter()
        metrics = evaluate_cases(fixture["cases"], policy, policy)["overall"]["current"]
        self.assertEqual(metrics["preserve_total"], 90)
        self.assertEqual(metrics["preserve_dropped"], 0)
        # The frozen pre-refinement policy discarded eight supplied decoys.
        # This is a regression floor, not a target used to tune the policy.
        self.assertGreaterEqual(metrics["discard_dropped"], 8)

    def test_independent_technical_conformance_preserves_identity_candidates(self):
        source = Path(__file__).parent / "fixtures/technical_citation_holdout.json"
        fixture = load_fixture(source, expected_sha256=(
            "c5371a6758ada6d23e3155daa8224b27c183f25cd291a24adbfa5e78efde1a31"))
        policy = load_current_filter()
        metrics = evaluate_cases(fixture["cases"], policy, policy)["overall"]["current"]
        self.assertEqual(metrics["preserve_total"], 20)
        self.assertEqual(metrics["preserve_dropped"], 0)
        self.assertEqual(metrics["discard_total"], 20)
        self.assertEqual(metrics["discard_dropped"], 20)
        _, targets = load_privacy_targets(
            source.with_name("technical_citation_privacy_targets.json"),
            "0b13e70c8a46ca62f4e11807e545900df054a64f979b4b5bb6e59d224e482384",
            fixture, "c5371a6758ada6d23e3155daa8224b27c183f25cd291a24adbfa5e78efde1a31")
        self.assertEqual(sum(len(values) for values in targets.values()), 20)


if __name__ == "__main__":
    unittest.main()
