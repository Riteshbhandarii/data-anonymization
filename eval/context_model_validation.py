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
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    save("raw_components.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
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


def score(fixture, fixture_hash, current_source):
    from eval.context_guard_validation import normalized_entity_type

    old_source = subprocess.check_output(["git", "show", "c07a2e8:detect/context_rules.py"], cwd=ROOT)
    (OUT / "old_policy.py").write_bytes(old_source)
    (OUT / "frozen_policy.py").write_bytes(current_source)
    old = load_module("old_policy", old_source)
    current = load_module("frozen_policy", current_source)
    raw_path = OUT / "raw_components.json"
    captured = json.loads(raw_path.read_text(encoding="utf-8"))
    assert captured["fixture_sha256"] == fixture_hash
    assert len(captured["documents"]) == len(fixture["cases"])
    assert sha(raw_path.read_bytes()) == json.loads(
        (OUT / "provenance.json").read_text(encoding="utf-8"))["raw_sha256"]
    case_lookup = {case["id"]: case for case in fixture["cases"]}
    assert {case["id"] for case in captured["documents"]} == set(case_lookup)
    safe_groups, local = defaultdict(Counter), []
    for case in captured["documents"]:
        original = case_lookup[case["id"]]
        assert case["text"] == original["text"] and case["spans"] == original["spans"]
        raw = [types.SimpleNamespace(**s) for s in case["routed"]]
        stages = {"routed": raw, "old": old.filter_context_spans(case["text"], raw),
                  "current": current.filter_context_spans(case["text"], raw)}
        raw_keys = {(s.start, s.end, s.entity_type, s.score) for s in raw}
        assert all((s.start, s.end, s.entity_type, s.score) in raw_keys
                   for name in ("old", "current") for s in stages[name])
        group_names = ("overall", "language/" + case["language"], "category/" + case["category"],
                       "language_category/" + case["language"] + "/" + case["category"])
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
        local.append({"id": case["id"], "language": case["language"], "category": case["category"],
                      "text": case["text"], "targets": targets,
                      "stage_spans": {name: serialized(spans) for name, spans in stages.items()}})

    safe = {
        "scope": "Independent synthetic actual-model probe, after policy freeze; not real-world accuracy",
        "scoring_contract": {
            "primary_sensitive": "Any routed span overlaps supplied sensitive target; report losses of this protection after filtering",
            "primary_discard": "Any span overlaps supplied nonsensitive target, indicating unwanted masking",
            "secondary": "Also report normalized-type overlap and union coverage separately",
            "entity_normalization": {"AGE": "DATE_TIME"},
            "pipelines": "Actual raw components once, unchanged route, then c07a2e8 or frozen current filter; no business/glossary additions",
        },
        "created_utc": datetime.now(timezone.utc).isoformat(), "cases": len(local),
        "fixture_sha256": fixture_hash, "raw_sha256": sha(raw_path.read_bytes()),
        "old_policy_sha256": sha(old_source), "current_policy_sha256": sha(current_source),
        "runner_sha256": sha(Path(__file__).read_bytes()),
        "groups": {group: dict(values) for group, values in sorted(safe_groups.items())},
    }
    provenance = json.loads((OUT / "provenance.json").read_text(encoding="utf-8"))
    safe["runtime"] = {key: provenance[key] for key in (
        "device", "offline", "torch_threads", "gliner_model", "gliner_threshold", "presidio_threshold")}
    safe["runtime"]["python"] = sys.version.split()[0]
    safe["versions"] = provenance["versions"]
    safe["model_snapshot_revisions"] = sorted(provenance.get("gliner_snapshots", {}))
    safe["component_source_hashes"] = provenance["component_source_hashes"]
    save("local_detailed_results.json", local)
    save("safe_aggregate.json", safe)
    lines = ["# Frozen-policy actual-model holdout probe", "", safe["scope"], "",
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
    lines += ["", "All text and spans remain only in ignored local files. No detector/policy/fixture was tuned after freeze.",
              "", "Policy SHA256: " + safe["current_policy_sha256"],
              "Fixture SHA256: " + fixture_hash, "Raw SHA256: " + safe["raw_sha256"]]
    (OUT / "safe_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(safe["groups"]["overall"], indent=2), flush=True)
    return safe


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-policy-sha", required=True)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--capture", action="store_true",
                        help="Run cached CPU models and create a new raw cache")
    parser.add_argument("--score-only", action="store_true",
                        help="Replay existing cache (the default)")
    args = parser.parse_args()
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
    from eval.context_guard_validation import FROZEN_FIXTURE_SHA256, load_fixture
    fixture = load_fixture()
    if args.capture:
        capture(fixture, FROZEN_FIXTURE_SHA256)
    report = score(fixture, FROZEN_FIXTURE_SHA256, current_source)
    if any(report["groups"]["overall"].get("current_sensitive_losses_vs_routed_" + metric, 0)
           for metric in ("any_overlap", "typed_overlap", "any_full_coverage", "typed_full_coverage")):
        raise SystemExit("Privacy gate failed: filtering lost raw-model sensitive protection")
