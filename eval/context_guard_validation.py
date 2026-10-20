"""Frozen supplied-candidate checks: candidate-policy validation, not detector recall.

Both policies receive the same independently authored spans.  The fixture uses
AGE as a semantic label; the production candidate contract uses DATE_TIME.
The uniform AGE -> DATE_TIME adapter below is applied before either policy.
No detector, NLP pipeline, or model is run by this evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "context_holdout.json"
FROZEN_FIXTURE_SHA256 = (
    "96964af553983fdb00cd3f1c78ca140ded9f9cfd99e5faae70257770fe14801c"
)
BASELINE_REVISION = "c07a2e8"
POLICY_SOURCE_PATH = Path("detect/context_rules.py")
ENTITY_TYPE_NORMALIZATION = {"AGE": "DATE_TIME"}
EVALUATION_SCOPE = "candidate-policy validation, not detector recall"
FIXTURE_SCOPE = (
    "independently authored synthetic contract checks, not real-world accuracy"
)

PolicyFilter = Callable[[str, Iterable[SimpleNamespace]], list[SimpleNamespace]]
CandidateKey = tuple[int, int, str]


class ValidationError(ValueError):
    """A contract or evaluation failure with no fixture sentences in its message."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def normalized_entity_type(entity_type: str) -> str:
    """Normalize every AGE candidate, regardless of its expected outcome."""
    return ENTITY_TYPE_NORMALIZATION.get(entity_type, entity_type)


def load_fixture(path: Path | str = DEFAULT_FIXTURE) -> dict[str, Any]:
    """Validate the original frozen bytes, schema, and Python Unicode offsets."""
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    _require(digest == FROZEN_FIXTURE_SHA256, "Frozen fixture SHA256 mismatch")
    _require(b"\r" not in raw, "Fixture must use LF line endings")
    try:
        fixture = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValidationError("Fixture must be valid UTF-8 JSON") from None

    _require(isinstance(fixture, dict), "Fixture root must be an object")
    _require(
        set(fixture) == {"schema_version", "scope", "cases"},
        "Unexpected fixture root fields",
    )
    _require(type(fixture["schema_version"]) is int, "Invalid schema version type")
    _require(fixture["schema_version"] == 1, "Unsupported schema version")
    _require(fixture["scope"] == FIXTURE_SCOPE, "Unexpected fixture scope")
    _require(isinstance(fixture["cases"], list), "Fixture cases must be a list")
    _require(bool(fixture["cases"]), "Fixture must contain cases")

    seen_ids: set[str] = set()
    for index, case in enumerate(fixture["cases"]):
        location = f"cases[{index}]"
        _require(isinstance(case, dict), f"{location} must be an object")
        _require(
            set(case) == {"id", "language", "text", "category", "spans"},
            f"{location} has unexpected fields",
        )
        _require(isinstance(case["id"], str) and bool(case["id"]), f"{location}: invalid id")
        _require(case["id"] not in seen_ids, f"{location}: duplicate id")
        seen_ids.add(case["id"])
        _require(case["language"] in {"en", "fi"}, f"{location}: invalid language")
        _require(isinstance(case["text"], str) and bool(case["text"]), f"{location}: invalid text")
        _require(
            isinstance(case["category"], str) and bool(case["category"]),
            f"{location}: invalid category",
        )
        _require(
            isinstance(case["spans"], list) and bool(case["spans"]),
            f"{location}: spans must be a nonempty list",
        )
        seen_keys: set[CandidateKey] = set()
        for span_index, span in enumerate(case["spans"]):
            span_location = f"{location}.spans[{span_index}]"
            _require(isinstance(span, dict), f"{span_location} must be an object")
            _require(
                set(span) == {"start", "end", "entity_type", "expect"},
                f"{span_location}: unexpected fields",
            )
            _require(
                type(span["start"]) is int and type(span["end"]) is int,
                f"{span_location}: offsets must be integers",
            )
            _require(
                0 <= span["start"] < span["end"] <= len(case["text"]),
                f"{span_location}: invalid Python Unicode offsets",
            )
            _require(
                bool(case["text"][span["start"] : span["end"]]),
                f"{span_location}: empty selected span",
            )
            _require(
                isinstance(span["entity_type"], str) and bool(span["entity_type"]),
                f"{span_location}: invalid entity type",
            )
            _require(
                span["expect"] in {"preserve_detection", "discard_detection"},
                f"{span_location}: invalid expectation",
            )
            key = (
                span["start"],
                span["end"],
                normalized_entity_type(span["entity_type"]),
            )
            _require(key not in seen_keys, f"{span_location}: duplicate normalized candidate")
            seen_keys.add(key)
    return fixture


def _candidate_key(candidate: SimpleNamespace) -> CandidateKey:
    return (candidate.start, candidate.end, candidate.entity_type)


def _retained_keys(
    policy: PolicyFilter, case: dict[str, Any], label: str
) -> set[CandidateKey]:
    # Fresh objects for each policy prevent one policy from altering the other input.
    candidates = [
        SimpleNamespace(
            start=span["start"],
            end=span["end"],
            entity_type=normalized_entity_type(span["entity_type"]),
            score=0.9,
        )
        for span in case["spans"]
    ]
    supplied_keys = {_candidate_key(candidate) for candidate in candidates}
    try:
        retained = policy(case["text"], candidates)
        retained_keys = {_candidate_key(candidate) for candidate in retained}
    except Exception as error:  # noqa: BLE001 - suppress sentence-bearing exception details
        # Report only the case id and exception class, never sentence-bearing details.
        raise ValidationError(
            f"{label} filter raised {type(error).__name__} in case {case['id']}"
        ) from None
    _require(
        retained_keys <= supplied_keys,
        f"{label} filter returned an unsupplied candidate in case {case['id']}",
    )
    return retained_keys


def _policy_metrics() -> dict[str, int]:
    return {
        "preserve_total": 0,
        "preserve_retained": 0,
        "preserve_dropped": 0,
        "discard_total": 0,
        "discard_dropped": 0,
        "discard_retained": 0,
    }


def _comparison_metrics() -> dict[str, Any]:
    return {
        "baseline": _policy_metrics(),
        "current": _policy_metrics(),
        "new_sensitive_losses": 0,
        "recovered_sensitive_candidates": 0,
    }


def _record(metrics: dict[str, int], preserve: bool, retained: bool) -> None:
    if preserve:
        metrics["preserve_total"] += 1
        metrics["preserve_retained" if retained else "preserve_dropped"] += 1
    else:
        metrics["discard_total"] += 1
        metrics["discard_retained" if retained else "discard_dropped"] += 1


def evaluate_cases(
    cases: list[dict[str, Any]],
    baseline_filter: PolicyFilter,
    current_filter: PolicyFilter,
) -> dict[str, Any]:
    """Return aggregate retention/removal counts without sentences or case ids."""
    overall = _comparison_metrics()
    by_language: dict[str, Any] = {}
    by_category: dict[str, Any] = {}
    by_language_category: dict[str, Any] = {}

    for case in cases:
        baseline_keys = _retained_keys(baseline_filter, case, "baseline")
        current_keys = _retained_keys(current_filter, case, "current")
        language = case["language"]
        category = case["category"]
        language_metrics = by_language.setdefault(language, _comparison_metrics())
        category_metrics = by_category.setdefault(category, _comparison_metrics())
        language_categories = by_language_category.setdefault(language, {})
        combined_metrics = language_categories.setdefault(category, _comparison_metrics())
        groups = (overall, language_metrics, category_metrics, combined_metrics)

        for span in case["spans"]:
            key = (
                span["start"],
                span["end"],
                normalized_entity_type(span["entity_type"]),
            )
            preserve = span["expect"] == "preserve_detection"
            baseline_retained = key in baseline_keys
            current_retained = key in current_keys
            for group in groups:
                _record(group["baseline"], preserve, baseline_retained)
                _record(group["current"], preserve, current_retained)
                group["new_sensitive_losses"] += int(
                    preserve and baseline_retained and not current_retained
                )
                group["recovered_sensitive_candidates"] += int(
                    preserve and not baseline_retained and current_retained
                )

    return {
        "overall": overall,
        "by_language": by_language,
        "by_category": by_category,
        "by_language_category": by_language_category,
    }


def _git_output(*arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        raise ValidationError(
            f"CLI comparison requires a Git checkout containing baseline {BASELINE_REVISION}"
        ) from None
    return result.stdout


def _load_policy(source: bytes, label: str, filename: str) -> PolicyFilter:
    digest = hashlib.sha256(source).hexdigest()
    module_name = f"detect._context_guard_validation_{label}_{digest[:16]}"
    module = ModuleType(module_name)
    module.__file__ = filename
    module.__package__ = "detect"
    sys.modules[module_name] = module
    root = str(REPOSITORY_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        # Execute only the explicitly selected local/repository policy source.
        exec(compile(source.decode("utf-8"), filename, "exec"), module.__dict__)  # noqa: S102
        policy = module.__dict__["filter_context_spans"]
    except Exception as error:  # noqa: BLE001 - avoid leaking source exception details
        sys.modules.pop(module_name, None)
        raise ValidationError(
            f"Unable to load {label} policy: {type(error).__name__}"
        ) from None
    _require(callable(policy), f"{label} policy entry point is not callable")
    return policy


def load_current_filter() -> PolicyFilter:
    """Load only the current standalone filter, without requiring Git history."""
    source_path = REPOSITORY_ROOT / POLICY_SOURCE_PATH
    return _load_policy(source_path.read_bytes(), "current", str(source_path))


def build_report(fixture_path: Path | str = DEFAULT_FIXTURE) -> dict[str, Any]:
    """Compare the pinned historical filter with the current source, model-free.

    Policy source is read only when this function is explicitly called.  Merely
    importing the module or validating the fixture does not load either policy.
    """
    fixture = load_fixture(fixture_path)
    source_path = POLICY_SOURCE_PATH.as_posix()
    baseline_source = _git_output("show", f"{BASELINE_REVISION}:{source_path}")
    current_source = (REPOSITORY_ROOT / POLICY_SOURCE_PATH).read_bytes()
    baseline_filter = _load_policy(
        baseline_source, "baseline", f"git:{BASELINE_REVISION}:{source_path}"
    )
    current_filter = _load_policy(current_source, "current", str(REPOSITORY_ROOT / POLICY_SOURCE_PATH))
    results = evaluate_cases(fixture["cases"], baseline_filter, current_filter)
    candidates = [span for case in fixture["cases"] for span in case["spans"]]
    try:
        fixture_label = Path(fixture_path).resolve().relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        fixture_label = Path(fixture_path).name
    return {
        "schema_version": 1,
        "evaluation_scope": EVALUATION_SCOPE,
        "fixture": {
            "path": fixture_label,
            "sha256": FROZEN_FIXTURE_SHA256,
            "scope": fixture["scope"],
            "cases": len(fixture["cases"]),
            "candidates": len(candidates),
            "by_language": dict(Counter(case["language"] for case in fixture["cases"])),
            "by_category": dict(Counter(case["category"] for case in fixture["cases"])),
        },
        "candidate_contract": {
            "entity_type_normalization": dict(ENTITY_TYPE_NORMALIZATION),
            "normalization_applied_identically_to": ["baseline", "current"],
            "normalized_candidates": sum(
                span["entity_type"] in ENTITY_TYPE_NORMALIZATION for span in candidates
            ),
            "score": 0.9,
            "retention_key": ["start", "end", "entity_type"],
        },
        "policies": {
            "baseline": {
                "requested_revision": BASELINE_REVISION,
                "commit": _git_output("rev-parse", f"{BASELINE_REVISION}^{{commit}}").decode().strip(),
                "source_path": source_path,
                "source_sha256": hashlib.sha256(baseline_source).hexdigest(),
            },
            "current": {
                "revision": "working tree",
                "head_commit": _git_output("rev-parse", "HEAD").decode().strip(),
                "source_path": source_path,
                "source_sha256": hashlib.sha256(current_source).hexdigest(),
            },
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Path to the exact frozen fixture; its SHA256 is always enforced",
    )
    parser.add_argument("--out", type=Path, help="Save the aggregate JSON report")
    arguments = parser.parse_args(argv)
    if arguments.out and arguments.out.exists():
        parser.exit(2, "Holdout validation failed: output report already exists\n")
    try:
        report = build_report(arguments.fixture)
        serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if arguments.out:
            arguments.out.parent.mkdir(parents=True, exist_ok=True)
            with arguments.out.open("x", encoding="utf-8", newline="\n") as destination:
                destination.write(serialized)
    except (OSError, ValidationError) as error:
        parser.exit(2, f"Holdout validation failed: {error}\n")
    sys.stdout.write(serialized)
    overall = report["results"]["overall"]
    if overall["current"]["preserve_dropped"] or overall["new_sensitive_losses"]:
        sys.stderr.write("Privacy gate failed: sensitive supplied candidates were dropped\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
