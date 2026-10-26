"""Replay or capture the frozen synthetic fixture using actual offline CPU detectors.

Raw text/spans and cache metadata stay under ignored outputs/. The safe aggregate
contains counts, version information and hashes only. Capture requires already
cached models; no model downloads or external inference requests are made.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import types
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.context_guard_validation import (
    BASELINE_REVISION,
    DEFAULT_FIXTURE,
    FROZEN_FIXTURE_SHA256,
    ValidationError,
    load_fixture,
    normalized_entity_type,
)

OUT = ROOT / "outputs/context-model-validation"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def serialized(spans):
    return [{"start": int(s.start), "end": int(s.end), "entity_type": s.entity_type,
             "score": float(s.score)} for s in spans]


def load_module(name, source):
    module = types.ModuleType(name)
    exec(compile(source, str(OUT / (name + ".py")), "exec"), module.__dict__)  # noqa: S102
    return module


def capture(fixture, fixture_hash):
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", GLINER_DEVICE="cpu")
    import torch
    torch.set_num_threads(4)
    from detect.combined import route
    from detect.methods import get_detector

    combined = get_detector("combined")
    captured = []
    for index, case in enumerate(fixture["cases"], 1):
        text, language = case["text"], case["language"]
        presidio = combined.presidio.detect(text, language)
        model = combined.model.detect(text, language)
        routed = route(presidio, model)
        captured.append({**case, "text_sha256": sha(text.encode("utf-8")),
                         "presidio": serialized(presidio), "model": serialized(model),
                         "routed": serialized(routed)})
        print(f"Captured {index}/{len(fixture['cases'])}: {case['id']}", flush=True)
    save("raw_components.json", {"created_utc": datetime.now(UTC).isoformat(),
                                  "fixture_sha256": fixture_hash, "documents": captured})
    from huggingface_hub import try_to_load_from_cache

    packages = ("torch", "gliner", "spacy", "presidio-analyzer", "presidio-anonymizer",
                "fi-core-news-sm", "en-core-web-sm", "transformers", "huggingface-hub")
    config = try_to_load_from_cache(combined.model.model_name, "gliner_config.json")
    revisions = {Path(config).parent.name: {}} if isinstance(config, str) else {}
    components = ("detect/combined.py", "detect/gliner_detector.py", "detect/adapter.py", "eval/bench.py")
    save("provenance.json", {
        "raw_sha256": sha((OUT / "raw_components.json").read_bytes()),
        "fixture_sha256": fixture_hash, "device": combined.device, "offline": True,
        "python": sys.version.split()[0],
        "torch_threads": torch.get_num_threads(), "gliner_model": combined.model.model_name,
        "gliner_threshold": combined.model.threshold,
        "presidio_threshold": combined.presidio.score_threshold,
        "versions": {p: importlib.metadata.version(p) for p in packages},
        "component_source_hashes": {p: sha((ROOT / p).read_bytes()) for p in components},
        "gliner_snapshots": revisions,
    })


def overlap(candidate, target):
    return candidate.start < target["end"] and candidate.end > target["start"]


def coverage(candidates, target):
    """A union of touching redaction intervals can cover the complete target."""
    right = target["start"]
    for item in sorted(candidates, key=lambda s: (s.start, s.end)):
        if item.start <= right:
            right = max(right, item.end)
    return right >= target["end"]


def metrics(spans, target, normalized_kind):
    touched = [s for s in spans if overlap(s, target)]
    typed = [s for s in touched if s.entity_type == normalized_kind]
    return {"any_overlap": bool(touched), "typed_overlap": bool(typed),
            "any_full_coverage": coverage(touched, target),
            "typed_full_coverage": coverage(typed, target),
            "overlapping_candidates": len(touched), "typed_overlapping_candidates": len(typed)}


def has_privacy_regression(report):
    """Reject losses of raw or baseline protection, including partial/type loss."""
    overall = report["groups"]["overall"]
    # Without separately adjudicated PII targets, conservatively protect every
    # character in a supplied sensitive range. Mixed candidate ranges can be
    # assessed separately without changing the original fixture or predictions.
    retention = report.get("independent_privacy_targets",
                           report.get("candidate_range_character_retention", {}))
    target_metrics = retention.get("groups", {}).get("overall", {})
    return (any(overall.get(f"current_sensitive_losses_vs_{reference}_{metric}", 0)
                for reference in ("routed", "baseline")
                for metric in ("any_overlap", "typed_overlap", "any_full_coverage", "typed_full_coverage"))
            or any(target_metrics.get(f"current_lost_{mode}_characters_vs_{reference}", 0)
                   for reference in ("routed", "baseline") for mode in ("any", "typed")))


def _require(condition, message):
    if not condition:
        raise ValidationError(message)


def load_privacy_targets(path, expected_sha256, fixture, fixture_hash):
    """Pin separate sensitive ranges to the exact fixture, case IDs and texts."""
    raw = Path(path).read_bytes()
    _require(isinstance(expected_sha256, str) and len(expected_sha256) == 64
             and sha(raw) == expected_sha256, "Privacy-target SHA256 mismatch")
    data = json.loads(raw)
    _require(set(data) == {"schema_version", "fixture_sha256", "scope", "cases"}
             and type(data["schema_version"]) is int and data["schema_version"] == 1
             and data["fixture_sha256"] == fixture_hash
             and isinstance(data["scope"], str) and bool(data["scope"].strip()),
             "Privacy-target schema, scope or fixture SHA256 mismatch")
    originals = {case["id"]: case for case in fixture["cases"]}
    _require(isinstance(data["cases"], list) and len(data["cases"]) == len(originals),
             "Privacy-target case count mismatch")
    by_id = {}
    for case in data["cases"]:
        _require(isinstance(case, dict) and set(case) == {"id", "text_sha256", "targets"}
                 and case["id"] in originals and case["id"] not in by_id,
                 "Privacy-target case IDs mismatch")
        text = originals[case["id"]]["text"]
        _require(case["text_sha256"] == sha(text.encode("utf-8"))
                 and isinstance(case["targets"], list), "Privacy-target text SHA256 mismatch")
        seen = set()
        for target in case["targets"]:
            _require(isinstance(target, dict) and set(target) == {"start", "end", "entity_type"}
                     and type(target["start"]) is int and type(target["end"]) is int
                     and 0 <= target["start"] < target["end"] <= len(text)
                     and isinstance(target["entity_type"], str) and bool(target["entity_type"]),
                     "Privacy-target offsets or entity type invalid")
            key = (target["start"], target["end"], target["entity_type"])
            _require(key not in seen, "Duplicate privacy target")
            seen.add(key)
        by_id[case["id"]] = case["targets"]
    return data, by_id


def privacy_character_metrics(stages, targets):
    """Detect exact character loss even when overlap/full-coverage flags agree."""
    count = Counter(targets=len(targets), target_characters=sum(t["end"] - t["start"] for t in targets))
    for target in targets:
        for mode in ("any", "typed"):
            covered = {}
            for stage, spans in stages.items():
                covered[stage] = {offset for span in spans
                                  if mode == "any" or span.entity_type == normalized_entity_type(target["entity_type"])
                                  for offset in range(max(span.start, target["start"]), min(span.end, target["end"]))}
                label = "baseline" if stage == "old" else stage
                count[f"{label}_{mode}_masked_characters"] += len(covered[stage])
                count[f"{label}_{mode}_fully_masked_targets"] += len(covered[stage]) == target["end"] - target["start"]
            for reference in ("routed", "old"):
                label = "baseline" if reference == "old" else reference
                lost = covered[reference] - covered["current"]
                count[f"current_lost_{mode}_characters_vs_{label}"] += len(lost)
                count[f"current_targets_losing_{mode}_characters_vs_{label}"] += bool(lost)
    return count


def score(fixture, fixture_hash, current_source, *, baseline_ref=BASELINE_REVISION,
          evaluation_stage="development-replay", privacy_targets=None, privacy_targets_sha256=None):
    _require((privacy_targets is None) == (privacy_targets_sha256 is None),
             "Privacy-target path and expected SHA256 must be supplied together")
    annotation, privacy_by_id = (load_privacy_targets(privacy_targets, privacy_targets_sha256, fixture, fixture_hash)
                                 if privacy_targets is not None else (None, None))

    old_source = subprocess.check_output(
        ["git", "show", f"{baseline_ref}:detect/context_rules.py"], cwd=ROOT)
    (OUT / "old_policy.py").write_bytes(old_source)
    (OUT / "frozen_policy.py").write_bytes(current_source)
    old = load_module("old_policy", old_source)
    current = load_module("frozen_policy", current_source)
    raw_path = OUT / "raw_components.json"
    captured = json.loads(raw_path.read_text(encoding="utf-8"))
    provenance = json.loads((OUT / "provenance.json").read_text(encoding="utf-8"))
    _require(captured["fixture_sha256"] == fixture_hash,
             "Raw cache fixture SHA256 mismatch")
    _require(provenance["fixture_sha256"] == fixture_hash,
             "Capture provenance fixture SHA256 mismatch")
    _require(len(captured["documents"]) == len(fixture["cases"]),
             "Raw cache case count mismatch")
    _require(sha(raw_path.read_bytes()) == provenance["raw_sha256"],
             "Raw cache SHA256 mismatch with capture provenance")
    case_lookup = {case["id"]: case for case in fixture["cases"]}
    _require({case["id"] for case in captured["documents"]} == set(case_lookup),
             "Raw cache case IDs mismatch")
    safe_groups, local = defaultdict(Counter), []
    candidate_characters, privacy_characters = defaultdict(Counter), defaultdict(Counter)
    for case in captured["documents"]:
        original = case_lookup[case["id"]]
        _require(all(case[key] == original[key] for key in (
            "text", "spans", "language", "category")), "Raw cache case content mismatch")
        _require(case["text_sha256"] == sha(case["text"].encode("utf-8")),
                 "Raw cache text SHA256 mismatch")
        raw = [types.SimpleNamespace(**s) for s in case["routed"]]
        # Separate objects prevent an accidental policy mutation from leaking
        # across paired comparisons or changing the frozen raw cache in memory.
        old_raw = [types.SimpleNamespace(**s) for s in case["routed"]]
        current_raw = [types.SimpleNamespace(**s) for s in case["routed"]]
        stages = {"routed": raw, "old": old.filter_context_spans(case["text"], old_raw),
                  "current": current.filter_context_spans(case["text"], current_raw)}
        raw_keys = {(s.start, s.end, s.entity_type, s.score) for s in raw}
        _require(all((s.start, s.end, s.entity_type, s.score) in raw_keys
                     for name in ("old", "current") for s in stages[name]),
                 "A policy returned an unsupplied raw candidate")
        group_names = ("overall", "language/" + case["language"], "category/" + case["category"],
                       "language_category/" + case["language"] + "/" + case["category"])
        candidate_counts = privacy_character_metrics(stages, [t for t in case["spans"] if t["expect"] == "preserve_detection"])
        privacy_counts = privacy_character_metrics(stages, privacy_by_id[case["id"]]) if privacy_by_id is not None else {}
        for group in group_names:
            candidate_characters[group].update(candidate_counts)
            privacy_characters[group].update(privacy_counts)
        targets = []
        for target in case["spans"]:
            kind = normalized_entity_type(target["entity_type"])
            values = {name: metrics(spans, target, kind) for name, spans in stages.items()}
            targets.append({"target": target, "normalized_kind": kind, "stages": values})
            sensitive = target["expect"] == "preserve_detection"
            prefix = "sensitive" if sensitive else "discard"
            for group in group_names:
                count = safe_groups[group]
                count["targets"] += 1
                count[prefix + "_targets"] += 1
                for name, stage in values.items():
                    for metric, value in stage.items():
                        count[name + "_" + prefix + "_" + metric] += value
                if sensitive:
                    count["pre_existing_routed_sensitive_no_overlap"] += not values["routed"]["any_overlap"]
                    count["pre_existing_routed_sensitive_no_typed_overlap"] += not values["routed"]["typed_overlap"]
                    for name in ("old", "current"):
                        for metric in ("any_overlap", "typed_overlap", "any_full_coverage", "typed_full_coverage"):
                            count[name + "_sensitive_losses_vs_routed_" + metric] += (
                                values["routed"][metric] and not values[name][metric])
                    for metric in ("any_overlap", "typed_overlap", "any_full_coverage", "typed_full_coverage"):
                        count["current_sensitive_losses_vs_baseline_" + metric] += (
                            values["old"][metric] and not values["current"][metric])
        local.append({"id": case["id"], "language": case["language"], "category": case["category"],
                      "text": case["text"], "targets": targets,
                      "stage_spans": {name: serialized(spans) for name, spans in stages.items()}})

    safe = {
        "scope": f"Synthetic actual-model {evaluation_stage}; not real-world accuracy",
        "evaluation_stage": evaluation_stage,
        "evaluation_scope": fixture["scope"],
        "fixture_scope": fixture["scope"],
        "baseline_ref": baseline_ref,
        "baseline_commit": subprocess.check_output(
            ["git", "rev-parse", f"{baseline_ref}^{{commit}}"], cwd=ROOT).decode().strip(),
        "scoring_contract": {
            "primary_sensitive": "Any routed span overlaps supplied sensitive target; report losses of this protection after filtering",
            "primary_discard": "Any span overlaps supplied nonsensitive target, indicating unwanted masking",
            "secondary": "Also report normalized-type overlap and union coverage separately",
            "entity_normalization": {"AGE": "DATE_TIME"},
            "pipelines": f"Actual raw components once, unchanged route, then {baseline_ref} or frozen current filter; no business/glossary additions",
        },
        "created_utc": datetime.now(UTC).isoformat(), "cases": len(local),
        "fixture_sha256": fixture_hash, "raw_sha256": sha(raw_path.read_bytes()),
        "old_policy_sha256": sha(old_source), "current_policy_sha256": sha(current_source),
        "runner_sha256": sha(Path(__file__).read_bytes()),
        "groups": {group: dict(values) for group, values in sorted(safe_groups.items())},
    }
    safe["runtime"] = {key: provenance[key] for key in (
        "device", "offline", "torch_threads", "gliner_model", "gliner_threshold", "presidio_threshold")}
    # Historical caches lack this field: unknown is more accurate than claiming
    # that the machine replaying this cache performed its original inference.
    safe["runtime"]["python"] = provenance.get("python")
    safe["capture_created_utc"] = captured.get("created_utc")
    safe["versions"] = provenance["versions"]
    safe["model_snapshot_revisions"] = sorted(provenance.get("gliner_snapshots", {}))
    safe["component_source_hashes"] = provenance["component_source_hashes"]
    safe["candidate_range_character_retention"] = {
        "scope": "Candidate ranges may cross nonsensitive context; their character loss alone does not establish personal-data loss",
        "groups": {group: dict(values) for group, values in sorted(candidate_characters.items())},
    }
    if annotation is not None:
        safe["independent_privacy_targets"] = {
            "sha256": privacy_targets_sha256, "fixture_sha256": fixture_hash,
            "scope": annotation["scope"],
            "annotation_timing": "Independent annotation after original raw capture; not pre-frozen detector labels",
            "groups": {group: dict(values) for group, values in sorted(privacy_characters.items())},
        }
        if candidate_characters["overall"].get("current_lost_any_characters_vs_baseline", 0):
            safe["candidate_range_caveat"] = (
                "Supplied candidate ranges include nonsensitive context. Their character loss "
                "is reported separately from independently annotated personal-data loss.")
    save("local_detailed_results.json", local)
    save("safe_aggregate.json", safe)
    lines = [f"# Frozen-policy actual-model {evaluation_stage}", "", safe["scope"], "",
             "Primary: any target overlap. Secondary type/coverage metrics are in safe_aggregate.json.", "",
             "| Group | Sensitive targets | Raw protection | Old | Current | Old new losses | Current new losses | Discard targets | Raw unwanted masks | Old | Current |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for group, count in safe["groups"].items():
        if group.startswith("language_category/"):
            continue
        keys = ("sensitive_targets", "routed_sensitive_any_overlap", "old_sensitive_any_overlap",
                "current_sensitive_any_overlap", "old_sensitive_losses_vs_routed_any_overlap",
                "current_sensitive_losses_vs_routed_any_overlap", "discard_targets",
                "routed_discard_any_overlap", "old_discard_any_overlap", "current_discard_any_overlap")
        lines.append("| " + group + " | " + " | ".join(str(count.get(key, 0)) for key in keys) + " |")
    lines += ["", "All text and spans remain only in ignored local files.",
              "Baseline revision: " + baseline_ref,
              "", "Policy SHA256: " + safe["current_policy_sha256"],
              "Fixture SHA256: " + fixture_hash, "Raw SHA256: " + safe["raw_sha256"]]
    (OUT / "safe_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(safe["groups"]["overall"], indent=2), flush=True)
    return safe


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-policy-sha", required=True)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--fixture-sha", default=FROZEN_FIXTURE_SHA256)
    parser.add_argument("--baseline-ref", default=BASELINE_REVISION)
    parser.add_argument("--privacy-targets", type=Path)
    parser.add_argument("--privacy-targets-sha")
    parser.add_argument("--evaluation-stage", default="development-replay",
                        choices=("development-replay", "post-freeze-holdout"))
    parser.add_argument("--capture", action="store_true",
                        help="Run cached CPU models and create a new raw cache")
    parser.add_argument("--score-only", action="store_true",
                        help="Replay existing cache (the default)")
    args = parser.parse_args()
    if (args.privacy_targets is None) != (args.privacy_targets_sha is None):
        parser.error("Privacy-target path and expected SHA256 must be supplied together")
    OUT = args.out.resolve()
    if not OUT.is_relative_to((ROOT / "outputs").resolve()):
        parser.error("Raw artifacts must stay under the ignored outputs/ directory")
    if args.capture and args.score_only:
        parser.error("Choose capture or replay")
    OUT.mkdir(parents=True, exist_ok=True)
    if args.capture and (OUT / "raw_components.json").exists():
        parser.error("Capture refuses to overwrite an existing raw cache")
    current_source = (ROOT / "detect/context_rules.py").read_bytes()
    if sha(current_source) != args.expected_policy_sha:
        raise RuntimeError("Frozen policy SHA mismatch; fixture has not been loaded")
    fixture = load_fixture(args.fixture, expected_sha256=args.fixture_sha)
    if args.capture:
        capture(fixture, args.fixture_sha)
    report = score(fixture, args.fixture_sha, current_source,
                   baseline_ref=args.baseline_ref, evaluation_stage=args.evaluation_stage,
                   privacy_targets=args.privacy_targets, privacy_targets_sha256=args.privacy_targets_sha)
    if has_privacy_regression(report):
        raise SystemExit("Privacy gate failed: filtering lost raw-model sensitive protection")
