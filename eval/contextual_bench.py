"""Does a local LLM pass catch contextual identifiers that rules + NER miss?

Scores the corpus from ``eval.contextual_corpus`` in two stages so GLiNER and an
LLM never share memory:

    python -m eval.contextual_bench base CORPUS --out outputs/contextual-llm/base.json
    python -m eval.contextual_bench llm CORPUS --base outputs/contextual-llm/base.json \\
        --model gemma-local --prompt contextual --out outputs/contextual-llm/gemma-contextual.json

A value counts as covered when the union of all spans, of any type, hides all of
it: for privacy the label does not matter. Decoys are values that must stay
visible; any overlap with them counts as over-masking. Reports hold aggregates
only; ``--spans-out`` may write span text, and only under ``outputs/``.
"""

import argparse
import collections
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_corpus(root):
    root = Path(root)
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    entries = index["documents"] if isinstance(index, dict) else index
    docs = []
    for entry in entries:
        doc_id = entry["id"]
        labels = json.loads((root / f"{doc_id}.json").read_text(encoding="utf-8"))
        with open(root / f"{doc_id}.md", encoding="utf-8", newline="") as stream:
            text = stream.read()  # offsets are code points in the file as written
        docs.append({"id": doc_id, "language": labels["language"], "split": labels["split"],
                     "text": text, "labels": labels["labels"], "decoys": labels["decoys"]})
    return docs


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def masked_chars(spans, length):
    hidden = bytearray(length)
    for start, end in spans:
        hidden[max(start, 0):min(end, length)] = b"\x01" * (min(end, length) - max(start, 0))
    return hidden


def score(docs, spans_by_id):
    """Any-type coverage per category and split, decoy hits and masking outside labels."""
    out = {}
    for split in ("dev", "test", "all"):
        cats = collections.defaultdict(lambda: [0, 0, 0])  # planted, covered, partial
        decoys = [0, 0]  # total, masked
        outside = total_chars = 0
        for doc in docs:
            if split != "all" and doc["split"] != split:
                continue
            hidden = masked_chars(spans_by_id.get(doc["id"], []), len(doc["text"]))
            for label in doc["labels"]:
                row = cats[label["category"]]
                part = hidden[label["start"]:label["end"]]
                row[0] += 1
                row[1] += all(part)
                row[2] += any(part) and not all(part)
            for decoy in doc["decoys"]:
                decoys[0] += 1
                decoys[1] += any(hidden[decoy["start"]:decoy["end"]])
            in_label = bytearray(len(doc["text"]))
            for label in doc["labels"]:
                in_label[label["start"]:label["end"]] = b"\x01" * (label["end"] - label["start"])
            outside += sum(1 for h, lab in zip(hidden, in_label) if h and not lab)
            total_chars += len(doc["text"])
        contextual = [v for k, v in cats.items() if k != "STANDARD"]
        out[split] = {
            "categories": {k: {"planted": v[0], "covered": v[1], "partial": v[2]} for k, v in sorted(cats.items())},
            "contextual": {"planted": sum(v[0] for v in contextual), "covered": sum(v[1] for v in contextual),
                           "partial": sum(v[2] for v in contextual)},
            "decoys": {"total": decoys[0], "masked": decoys[1]},
            "masked_outside_labels": {"characters": outside, "share": round(outside / total_chars, 4) if total_chars else 0},
        }
    return out


def corpus_digest(docs):
    blob = json.dumps([[d["id"], text_sha(d["text"]), d["labels"], d["decoys"]] for d in docs], sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def write_spans(path, docs, spans_by_id):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT / "outputs").resolve()):
        raise ValueError("--spans-out must be under outputs/: span text may contain document content")
    rows = {d["id"]: [{"start": s, "end": e, "type": t, "text": d["text"][s:e]}
                      for s, e, t in spans_by_id.get(d["id"], [])] for d in docs}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def run_base(args):
    from detect.methods import get_detector
    from eval.local_base_cache import source_digest
    from redact import validate_spans

    docs = load_corpus(args.corpus)
    detector = get_detector(args.method)
    spans, started = {}, time.perf_counter()
    for doc in docs:
        found = validate_spans(doc["text"], detector.detect(doc["text"], doc["language"]))
        spans[doc["id"]] = [[s.start, s.end, s.entity_type] for s in found]
    seconds = time.perf_counter() - started
    report = {"schema_version": 1, "stage": "base", "method": args.method, "corpus_sha256": corpus_digest(docs),
              "detector_source_sha256": source_digest(), "text_sha256": {d["id"]: text_sha(d["text"]) for d in docs},
              "detect_seconds": round(seconds, 3), "spans": spans,
              "score": score(docs, {k: [(s, e) for s, e, _ in v] for k, v in spans.items()})}
    write_report(args.out, report)
    if args.spans_out:
        write_spans(args.spans_out, docs, spans)
    print_summary(report)


def run_llm(args):
    from detect.local_llm import LocalLLMDetector

    docs = load_corpus(args.corpus)
    if args.base:
        base = json.loads(Path(args.base).read_text(encoding="utf-8"))
        if base["corpus_sha256"] != corpus_digest(docs):
            raise SystemExit("Base cache does not match this corpus; rebuild it with the base stage")
    else:
        base = {"method": None, "spans": {d["id"]: [] for d in docs}}
    detector = LocalLLMDetector(args.model, base_url=args.base_url, prompt=args.prompt, strict=False)
    spans, errors, seconds = {}, collections.Counter(), 0.0
    for doc in docs:
        base_spans = [tuple(s) for s in base["spans"][doc["id"]]]
        masked = list(doc["text"])
        for start, end, _ in base_spans:
            for i in range(start, end):
                if masked[i] not in "\n\r":
                    masked[i] = "█"
        started = time.perf_counter()
        try:
            extra = [(s.start, s.end, s.entity_type) for s in detector.detect("".join(masked), doc["language"])]
        except (OSError, ValueError, KeyError, TypeError, IndexError, RuntimeError) as error:
            errors[type(error).__name__] += 1  # messages omitted: providers can echo text
            extra = []
        seconds += time.perf_counter() - started
        spans[doc["id"]] = [list(s) for s in base_spans] + [list(s) for s in extra]
    report = {"schema_version": 1, "stage": "llm", "model": args.model, "prompt": args.prompt,
              "base_method": base["method"],
              "base_sha256": hashlib.sha256(Path(args.base).read_bytes()).hexdigest() if args.base else None,
              "corpus_sha256": corpus_digest(docs), "failed_documents": sum(errors.values()),
              "error_types": dict(errors), "dropped_entities": detector.dropped,
              "llm_seconds": round(seconds, 3), "runtime_scope": "LLM requests only; model loading excluded",
              "temperature": 0, "reasoning_effort": "none",
              "score": score(docs, {k: [(s, e) for s, e, _ in v] for k, v in spans.items()})}
    write_report(args.out, report)
    if args.spans_out:
        write_spans(args.spans_out, docs, spans)
    print_summary(report)


def run_union(args):
    """Score base spans together with an LLM-alone run on the original text."""
    docs = load_corpus(args.corpus)
    base = json.loads(Path(args.base).read_text(encoding="utf-8"))
    llm = json.loads(Path(args.llm).read_text(encoding="utf-8"))
    if base["corpus_sha256"] != corpus_digest(docs) or llm["corpus_sha256"] != corpus_digest(docs):
        raise SystemExit("Base or LLM report does not match this corpus")
    if llm["base_method"] is not None:
        raise SystemExit("--llm must be an LLM-alone report (run without --base)")
    extra = json.loads(Path(args.llm_spans).read_text(encoding="utf-8"))
    spans = {d["id"]: [(s, e) for s, e, _ in base["spans"][d["id"]]]
             + [(r["start"], r["end"]) for r in extra[d["id"]]] for d in docs}
    report = {"schema_version": 1, "stage": "union", "base_method": base["method"], "model": llm["model"],
              "prompt": llm["prompt"], "corpus_sha256": corpus_digest(docs),
              "failed_documents": llm["failed_documents"], "dropped_entities": llm["dropped_entities"],
              "llm_seconds": llm["llm_seconds"], "base_detect_seconds": base["detect_seconds"],
              "score": score(docs, spans)}
    write_report(args.out, report)
    print_summary(report)


def write_report(path, report):
    path = Path(path)
    if path.exists():
        raise SystemExit(f"{path} exists; write a new report instead of overwriting")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"-> {path}")


def print_summary(report):
    for split in ("dev", "test"):
        s = report["score"][split]
        c = s["contextual"]
        print(f"{split}: contextual {c['covered']}/{c['planted']} (+{c['partial']} partial), "
              f"decoys masked {s['decoys']['masked']}/{s['decoys']['total']}, "
              f"outside labels {s['masked_outside_labels']['share']:.1%}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="stage", required=True)
    base = sub.add_parser("base", help="Run the rules + NER detector and freeze its spans")
    base.add_argument("corpus", type=Path)
    base.add_argument("--method", default="combined")
    base.add_argument("--out", type=Path, required=True)
    base.add_argument("--spans-out", type=Path)
    llm = sub.add_parser("llm", help="Mask the frozen base spans, then run a local LLM pass")
    llm.add_argument("corpus", type=Path)
    llm.add_argument("--base", type=Path, help="Frozen base spans to mask first; omit for the LLM alone")
    llm.add_argument("--model", required=True, help="Identifier already loaded in LM Studio")
    llm.add_argument(
        "--prompt",
        choices=["identifiers", "contextual", "original_contextual"],
        default="contextual",
    )
    llm.add_argument("--base-url", default="http://127.0.0.1:1234/v1")
    llm.add_argument("--out", type=Path, required=True)
    llm.add_argument("--spans-out", type=Path)
    union = sub.add_parser("union", help="Score frozen base spans together with an LLM-alone run")
    union.add_argument("corpus", type=Path)
    union.add_argument("--base", type=Path, required=True)
    union.add_argument("--llm", type=Path, required=True, help="LLM-alone report")
    union.add_argument("--llm-spans", type=Path, required=True, help="That run's --spans-out file")
    union.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    {"base": run_base, "llm": run_llm, "union": run_union}[args.stage](args)


if __name__ == "__main__":
    main()
