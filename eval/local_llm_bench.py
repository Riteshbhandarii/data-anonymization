"""Score a local LLM on generated body text, optionally after a base detector.

    python -m eval.local_llm_bench outputs/local-corpus --model qwen-local \
        --out outputs/local-qwen.json

No extraction score is claimed. The same whole-value recall and typed overlap
precision rules as eval.bench apply. Failures remain in recall denominators.
Only aggregate results are written; no document text or returned strings.
"""

import argparse
import collections
import hashlib
import json
import platform
import time
from pathlib import Path

from detect.local_llm import FinalPassDetector, LocalLLMDetector
from eval.bench import TYPE_MAP, fingerprint, found, judge, manifest, occurrences
from redact import validate_spans


def _merge(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def union_state(text, value, spans):
    """covered/partial/"" for a value against the union of spans of any type."""
    merged = _merge((s.start, s.end) for s in spans)
    states = []
    start = text.find(value)
    while start >= 0:
        end = start + len(value)
        if any(a <= start and b >= end for a, b in merged):
            states.append("covered")
        elif any(a < end and b > start for a, b in merged):
            states.append("partial")
        else:
            states.append("")
        start = text.find(value, start + 1)
    if states and all(x == "covered" for x in states):
        return "covered"
    return "partial" if any(states) else ""


def over_masking(text, entities, spans):
    """(characters masked outside all body labels, spans touching no label)."""
    body = _merge((a, b) for a, b, _ in occurrences(
        text, [e for e in entities if e["location"] == "body"]))
    masked = _merge((s.start, s.end) for s in spans)
    inside = 0
    for a, b in masked:
        for c, d in body:
            inside += max(0, min(b, d) - max(a, c))
    outside = sum(b - a for a, b in masked) - inside
    labelled = occurrences(text, entities)
    orphans = sum(1 for s in spans if not any(s.start < b and s.end > a for a, b, _ in labelled))
    return outside, orphans


def spans_out_path(path):
    """Raw span text may be written only beneath this repository's outputs/."""
    outputs = (Path(__file__).resolve().parent.parent / "outputs").resolve()
    resolved = Path(path).resolve()
    if outputs not in resolved.parents:
        raise ValueError(f"--spans-out must be under {outputs}")
    return resolved


def benchmark(root, detector, spans_log=None):
    root = Path(root)
    stems = manifest(root)
    corpus = json.loads((root / "corpus.json").read_text(encoding="utf-8"))
    if fingerprint(root, stems) != corpus.get("corpus_sha256"):
        raise ValueError("Corpus digest does not match the scored files")
    if not stems:
        raise ValueError("Corpus contains no documents")
    recall = collections.defaultdict(lambda: [0, 0, 0])
    precision = collections.defaultdict(lambda: [0, 0, 0])
    runtimes = collections.defaultdict(lambda: [0, 0.0])
    any_recall = collections.defaultdict(lambda: [0, 0, 0])
    masking = collections.defaultdict(lambda: [0, 0, 0])  # outside chars, total chars, orphan spans
    errors = collections.Counter()
    for stem in stems:
        document = json.loads((root / "labels" / f"{stem}.json").read_text(encoding="utf-8"))
        text = (root / "text" / f"{stem}.txt").read_text(encoding="utf-8")
        lang = document["language"]
        started = time.perf_counter()
        try:
            spans = validate_spans(text, detector.detect(text, lang))
        except (OSError, ValueError, KeyError, TypeError, IndexError, RuntimeError) as error:
            # Deliberately omit error messages: providers can echo private text.
            errors[type(error).__name__] += 1
            spans = []
        runtimes[lang][0] += 1
        runtimes[lang][1] += time.perf_counter() - started
        by_type = collections.defaultdict(list)
        for span in spans:
            by_type[TYPE_MAP.get(span.entity_type, span.entity_type)].append(span)
        outside, orphans = over_masking(text, document["entities"], spans)
        for key in (lang, "all"):
            masking[key][0] += outside
            masking[key][1] += len(text)
            masking[key][2] += orphans
        if spans_log is not None:
            spans_log.append({"document": stem, "language": lang,
                              "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                              "spans": [{"start": s.start, "end": s.end, "entity_type": s.entity_type,
                                         "text": text[s.start:s.end]} for s in spans]})
        for entity in document["entities"]:
            if entity["location"] != "body":
                continue
            state = union_state(text, entity["value"], spans)
            row = any_recall[(lang, entity["type"])]
            row[0] += 1
            row[1] += state == "covered"
            row[2] += state == "partial"
            state = found(text, entity["value"], by_type[entity["type"]])
            row = recall[(lang, entity["type"])]
            row[0] += 1
            row[1] += state == "covered"
            row[2] += state == "partial"
        labelled = occurrences(text, document["entities"])
        for span in spans:
            kind = TYPE_MAP.get(span.entity_type, span.entity_type)
            state = judge(span, kind, labelled)
            row = precision[(lang, kind)]
            row[0] += 1
            row[1] += state == "correct"
            row[2] += state == "other type"
    return {
        "schema_version": 1, "corpus": corpus,
        "scope": "Body labels only; no extraction measurement. All occurrences must be covered. "
                 "QUASI_IDENTIFIER has no synthetic ground truth; its effectiveness is unmeasured.",
        "documents": len(stems), "failed_documents": sum(errors.values()), "error_types": dict(errors),
        "recall": [{"language": lang, "entity_type": kind, "planted": row[0],
                    "covered": row[1], "partial": row[2]} for (lang, kind), row in sorted(recall.items())],
        "recall_any_type": [{"language": lang, "entity_type": kind, "planted": row[0],
                             "covered": row[1], "partial": row[2]}
                            for (lang, kind), row in sorted(any_recall.items())],
        "over_masking": {key: {"characters_outside_body_labels": row[0], "total_characters": row[1],
                               "share": row[0] / row[1] if row[1] else 0.0, "spans_touching_no_label": row[2]}
                         for key, row in sorted(masking.items())},
        "precision": [{"language": lang, "entity_type": kind, "detections": row[0],
                       "correct": row[1], "other_type": row[2], "unlabelled": row[0] - row[1] - row[2]}
                      for (lang, kind), row in sorted(precision.items())],
        "runtime": [{"language": lang, "documents": row[0], "seconds": row[1],
                     "seconds_per_document": row[1] / row[0]} for lang, row in sorted(runtimes.items())],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--model", required=True, help="Explicit identifier already loaded in LM Studio")
    parser.add_argument("--base-url", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--base-method", choices=["rules", "combined", "gliner2"],
                        help="Mask this detector's spans before the final LLM pass")
    parser.add_argument("--base-cache", type=Path,
                        help="Replay frozen base spans without loading GLiNER beside the LLM")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--spans-out", type=Path,
                        help="Write every returned span with its text (synthetic corpus only); "
                             "must be under outputs/")
    args = parser.parse_args(argv)
    spans_path = spans_out_path(args.spans_out) if args.spans_out else None
    if args.base_cache and not args.base_method:
        parser.error("--base-cache requires --base-method")
    detector = LocalLLMDetector(args.model, base_url=args.base_url)
    if args.base_method:
        if args.base_cache:
            from eval.local_base_cache import CachedDetector
            base = CachedDetector(args.base_cache, args.corpus, args.base_method)
        else:
            from detect.methods import get_detector
            base = get_detector(args.base_method)
        detector = FinalPassDetector(base, detector)
    spans_log = [] if spans_path else None
    report = benchmark(args.corpus, detector, spans_log)
    report.update(model=args.model, base_method=args.base_method, temperature=0, reasoning_effort="none",
                  host={"platform": platform.platform(), "machine": platform.machine()},
                  window_characters=4000, overlap_characters=400, score="1.0 flag; uncalibrated")
    if args.base_cache:
        report.update(base_cache_sha256=hashlib.sha256(args.base_cache.read_bytes()).hexdigest(),
                      base_runtime=base.cache["baseline"]["runtime"],
                      base_construction_seconds=base.cache["construction_seconds"],
                      runtime_scope="LLM final pass and cached-span replay; base detection and "
                                    "construction recorded separately. LLM loading excluded.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if spans_path:
        spans_path.parent.mkdir(parents=True, exist_ok=True)
        spans_path.write_text(json.dumps(spans_log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    planted = sum(row["planted"] for row in report["recall"])
    covered = sum(row["covered"] for row in report["recall"])
    print(f"{covered}/{planted} body identifiers covered; {report['failed_documents']} failed documents")
    print(f"Aggregate report: {args.out}")
    return int(bool(report["failed_documents"]))


if __name__ == "__main__":
    raise SystemExit(main())
