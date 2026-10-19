"""Freeze base detections so GLiNER and a local LLM never share memory.

The cache contains offsets, types and scores, never document text. Corpus and
detector-source hashes prevent replay against changed inputs or detector code.
"""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

from eval.bench import fingerprint, manifest
from redact import validate_spans


def source_digest():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted((root / "detect").glob("*.py")) + [root / "eval/bench.py"]:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def text_key(text, language):
    return f"{language}:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


class CachedDetector:
    def __init__(self, path, corpus, method):
        self.cache = json.loads(Path(path).read_text(encoding="utf-8"))
        actual = fingerprint(corpus, manifest(corpus))
        if (self.cache["method"] != method or self.cache["corpus_sha256"] != actual
                or self.cache["detector_source_sha256"] != source_digest()):
            raise ValueError("Base cache method, corpus or detector source does not match")

    def detect(self, text, language="en"):
        rows = self.cache["spans"][text_key(text, language)]
        return validate_spans(text, [SimpleNamespace(**row) for row in rows])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--method", default="combined", choices=["combined", "rules", "gliner2"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    from detect.methods import get_detector
    from eval.local_llm_bench import benchmark

    started = time.perf_counter()
    detector = get_detector(args.method)
    construction_seconds = time.perf_counter() - started
    rows = {}

    class RecordingDetector:
        def detect(self, text, language):
            spans = validate_spans(text, detector.detect(text, language))
            rows[text_key(text, language)] = [
                {key: getattr(span, key) for key in ("start", "end", "entity_type", "score")}
                for span in spans]
            return spans

    report = benchmark(args.corpus, RecordingDetector())
    if report["failed_documents"]:
        raise RuntimeError("Base benchmark failed; cache was not written")
    payload = {
        "schema_version": 1, "method": args.method,
        "corpus_sha256": report["corpus"]["corpus_sha256"],
        "detector_source_sha256": source_digest(), "spans": rows,
        "configuration": {"GLINER_DEVICE": os.environ.get("GLINER_DEVICE"),
                          "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE")},
        "construction_seconds": construction_seconds, "baseline": report,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")
    covered = sum(row["covered"] for row in report["recall"])
    planted = sum(row["planted"] for row in report["recall"])
    print(f"{covered}/{planted} body identifiers; cache: {args.out}")


if __name__ == "__main__":
    main()
