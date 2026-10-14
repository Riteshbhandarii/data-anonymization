"""Score a local LLM on generated body text, optionally after a base detector.

    python -m eval.local_llm_bench outputs/local-corpus --model qwen-local \
        --out outputs/local-qwen.json

No extraction score is claimed. The same whole-value recall and typed overlap
precision rules as eval.bench apply. Failures remain in recall denominators.
Only aggregate results are written; no document text or returned strings.
"""

import argparse
import collections
import json
import platform
import time
from pathlib import Path

from detect.local_llm import FinalPassDetector, LocalLLMDetector
from eval.bench import TYPE_MAP, fingerprint, found, judge, manifest, occurrences
from redact import validate_spans


def benchmark(root, detector):
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
        for entity in document["entities"]:
            if entity["location"] != "body":
                continue
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
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    detector = LocalLLMDetector(args.model, base_url=args.base_url)
    if args.base_method:
        from detect.methods import get_detector
        detector = FinalPassDetector(get_detector(args.base_method), detector)
    report = benchmark(args.corpus, detector)
    report.update(model=args.model, base_method=args.base_method, temperature=0, reasoning_effort="none",
                  host={"platform": platform.platform(), "machine": platform.machine()},
                  window_characters=4000, overlap_characters=400, score="1.0 flag; uncalibrated")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    planted = sum(row["planted"] for row in report["recall"])
    covered = sum(row["covered"] for row in report["recall"])
    print(f"{covered}/{planted} body identifiers covered; {report['failed_documents']} failed documents")
    print(f"Aggregate report: {args.out}")
    return int(bool(report["failed_documents"]))


if __name__ == "__main__":
    raise SystemExit(main())
