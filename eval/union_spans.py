"""Score the union of saved span logs on the local-LLM corpus, without a model.

    python -m eval.union_spans outputs/local-corpus \\
        --spans combined-spans.json qwen-alone-spans.json --out union.json

Each input is a ``--spans-out`` file from ``eval.local_llm_bench``. Spans are
matched to documents by text hash, so a log from a different corpus is
rejected. The report has the same aggregate fields as the benchmark.
"""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from eval.local_llm_bench import benchmark


class ReplaySpans:
    def __init__(self, paths):
        self.by_hash = {}
        for path in paths:
            for row in json.loads(Path(path).read_text(encoding="utf-8")):
                self.by_hash.setdefault(row["text_sha256"], []).extend(row["spans"])

    def detect(self, text, language="en"):
        import hashlib
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key not in self.by_hash:
            raise KeyError("No saved spans for this document text")
        return [SimpleNamespace(start=s["start"], end=s["end"], entity_type=s["entity_type"], score=1.0)
                for s in self.by_hash[key]]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--spans", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = benchmark(args.corpus, ReplaySpans(args.spans))
    report["inputs"] = [p.name for p in args.spans]
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; write a new report instead of overwriting")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    covered = sum(r["covered"] for r in report["recall_any_type"])
    planted = sum(r["planted"] for r in report["recall_any_type"])
    print(f"any-type {covered}/{planted}; outside labels {report['over_masking']['all']['share']:.2%}; "
          f"{report['failed_documents']} failed documents")


if __name__ == "__main__":
    raise SystemExit(main())
