"""Prepare combined utility packs, or replay their base spans for a local final pass.

Run base preparation with every LLM unloaded. Let that process exit, then load
one LLM and use --base-cache plus --model. No GLiNER is built in replay mode.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

from eval.local_base_cache import source_digest, text_key
from eval.study import prepare
from eval.utility_bench import build_pack
from redact import validate_spans


def check_suite(suite, expected):
    if hashlib.sha256(suite.read_bytes()).hexdigest() != expected["suite_sha256"]:
        raise ValueError("Utility suite differs from frozen base cache")
    specification = json.loads(suite.read_text(encoding="utf-8"))
    for doc in specification["documents"]:
        path = (suite.parent / doc["file"]).resolve()
        if not path.is_relative_to(suite.parent.resolve()):
            raise ValueError("Document path leaves the utility suite")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected["document_sha256"][doc["id"]]:
            raise ValueError("Utility document differs from frozen base cache")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--english-suite", type=Path, required=True)
    parser.add_argument("--finnish-suite", type=Path, default=Path("eval/utility_fi/suite.json"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--base-cache", type=Path)
    parser.add_argument("--model")
    args = parser.parse_args()
    if bool(args.model) != bool(args.base_cache):
        parser.error("--model and --base-cache must be supplied together")
    args.out.mkdir(parents=True, exist_ok=True)
    if args.base_cache:
        cache_bytes = args.base_cache.read_bytes()
        cache = json.loads(cache_bytes)
        if cache["method"] != "combined" or cache["detector_source_sha256"] != source_digest():
            raise ValueError("Utility base cache detector configuration does not match")
        for lang, suite in (("en", args.english_suite), ("fi", args.finnish_suite)):
            check_suite(suite, cache["suites"][lang])
    else:
        from detect.methods import get_detector
        detector = get_detector("combined")
        cache = {"method": "combined", "detector_source_sha256": source_digest(),
                 "suites": {}, "spans": {}}

    class Base:
        def detect(self, text, language="en"):
            key = text_key(text, language)
            if args.base_cache:
                return validate_spans(text, [SimpleNamespace(**row) for row in cache["spans"][key]])
            spans = validate_spans(text, detector.detect(text, language))
            cache["spans"][key] = [{field: getattr(span, field) for field in
                                   ("start", "end", "entity_type", "score")} for span in spans]
            return spans

    active = Base()
    if args.base_cache:
        from detect.local_llm import FinalPassDetector, LocalLLMDetector
        active = FinalPassDetector(active, LocalLLMDetector(args.model))
    for lang, suite in (("en", args.english_suite), ("fi", args.finnish_suite)):
        started = time.perf_counter()
        plan = prepare(suite, active, alias_scope="document")
        plan["detector_configuration"].update(method=args.tag, source_commit="e148240",
                                              source_sha256=source_digest(), final_model=args.model)
        if args.base_cache:
            plan["detector_configuration"]["base_cache_sha256"] = hashlib.sha256(cache_bytes).hexdigest()
        else:
            cache["suites"][lang] = {"suite_sha256": plan["suite_sha256"],
                                      "document_sha256": plan["document_sha256"],
                                      "preparation_seconds": time.perf_counter() - started}
        with (args.out / f"{lang}-{args.tag}-plan.json").open("x", encoding="utf-8") as stream:
            json.dump(plan, stream, ensure_ascii=False, indent=2)
        build_pack(plan, args.out / f"{lang}-{args.tag}-pack")
        print(f"Prepared {lang}/{args.tag}")
    if not args.base_cache:
        with (args.out / "combined-spans.json").open("x", encoding="utf-8") as stream:
            json.dump(cache, stream, indent=2)


if __name__ == "__main__":
    main()
