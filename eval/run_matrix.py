"""Run every free detection method over every dataset we have.

    python -m eval.run_matrix --out /path/to/outputs/runs

Datasets: fake (our generator, through the real extractors), tab (court
judgments, expert spans), turku (Finnish news, name spans), ai4privacy
(AI-written PII text, EN and FI) and real-uk (public files, no labels).

Writes, under --out:
    <dataset>/<method>/<doc-id>_anonymized.md   redacted text, labels as [TYPE]
    results.csv                                 recall counts, one row per group
    detections_real_uk.csv                      detections per type, no recall
    runtime.csv                                 detection seconds per dataset/method
    summary.md                                  tables and caveats

Outputs contain anonymized real text and must not be committed. Only code and
aggregate numbers belong in git.

Type vocabulary
---------------
results.csv uses one entity_type column across datasets. Where two schemes
mean the same thing they are renamed to the corpus word (PERSON, COMPANY,
ADDRESS, DATE, EMAIL, PHONE, IBAN); everything else keeps the dataset's own
name. The tables below are the whole mapping and are deliberately visible.
"""

import argparse
import collections
import csv
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from detect.methods import METHODS, get_detector

CORPUS_ROOT = Path("~/Desktop/anonymization-corpus/external").expanduser()
REAL_UK = Path("~/code/data-anonymization/corpus/real").expanduser()

METHOD_NAMES = [*METHODS, "gliner"]
DATASETS = ["fake", "tab", "turku", "ai4privacy", "real-uk"]

# Which detector entity types count as a hit for each scored type. A type with
# no entry accepts a detection of ANY type: the value was redacted, which is
# what protection needs, even if the placeholder says something different.
ACCEPT = {
    "PERSON": {"PERSON"},
    "COMPANY": {"ORGANIZATION"},
    "ADDRESS": {"LOCATION"},
    "CITY": {"LOCATION"},
    "STREET": {"LOCATION"},
    "DATE": {"DATE_TIME"},
    "EMAIL": {"EMAIL_ADDRESS"},
    "PHONE": {"PHONE_NUMBER"},
    "IBAN": {"IBAN_CODE"},
    "CREDITCARD": {"CREDIT_CARD"},
}

# TAB (ECHR judgments). NO_MASK mentions are not required to be hidden and are
# skipped. CODE (case numbers), DEM (nationality, occupation), QUANTITY and
# MISC have no Presidio counterpart, so any detection over them counts.
TAB_TYPES = {"PERSON": "PERSON", "ORG": "COMPANY", "LOC": "ADDRESS", "DATETIME": "DATE",
             "CODE": "CODE", "DEM": "DEM", "QUANTITY": "QUANTITY", "MISC": "MISC"}

# Turku NER. PRO (products) and EVENT are not personal data and are skipped.
TURKU_TYPES = {"PER": "PERSON", "ORG": "COMPANY", "LOC": "ADDRESS", "DATE": "DATE"}

# ai4privacy. TITLE, GENDER and SEX are attributes rather than identifiers and
# are skipped. Address parts are scored against Presidio LOCATION, which
# rarely fires on a street or a house number. ID-like classes accept any type.
AI4P_TYPES = {
    "GIVENNAME": "PERSON", "SURNAME": "PERSON", "EMAIL": "EMAIL", "TELEPHONENUM": "PHONE",
    "DATE": "DATE", "CITY": "CITY", "STREET": "STREET", "ZIPCODE": "ZIPCODE",
    "BUILDINGNUM": "BUILDINGNUM", "AGE": "AGE", "CREDITCARDNUMBER": "CREDITCARD",
    "IDCARDNUM": "IDCARDNUM", "PASSPORTNUM": "PASSPORTNUM", "DRIVERLICENSENUM": "DRIVERLICENSENUM",
    "TAXNUM": "TAXNUM", "SOCIALNUM": "SOCIALNUM",
}

MAX_CHUNK = 100_000
RESULT_COLUMNS = ["dataset", "method", "entity_type", "language", "planted", "covered", "partial",
                  "location", "identifier_type", "format"]


# ---------------------------------------------------------------- pure helpers

def accepts(corpus_type: str, detected_type: str) -> bool:
    allowed = ACCEPT.get(corpus_type)
    return True if allowed is None else detected_type in allowed


def mention_state(start: int, end: int, corpus_type: str, spans) -> str:
    """covered when one accepted span holds the whole mention, partial on overlap."""
    state = ""
    for span in spans:
        if not accepts(corpus_type, span.entity_type):
            continue
        if span.start <= start and span.end >= end:
            return "covered"
        if span.start < end and span.end > start:
            state = "partial"
    return state


def split_text(text: str, limit: int = MAX_CHUNK):
    """Yield (offset, piece) with pieces under the limit, cut at line breaks."""
    start = 0
    while start < len(text):
        end = min(len(text), start + limit)
        if end < len(text):
            cut = text.rfind("\n", start, end)
            if cut > start:
                end = cut + 1
        yield start, text[start:end]
        start = end


class Offset:
    """A span shifted into whole-document coordinates."""

    def __init__(self, span, offset):
        self.start, self.end = span.start + offset, span.end + offset
        self.entity_type, self.score = span.entity_type, span.score


def detect_long(detector, text: str, language: str):
    """Detect piecewise so one huge spreadsheet cannot exceed spaCy's limit."""
    if len(text) <= MAX_CHUNK:
        return list(detector.detect(text, language=language))
    spans = []
    for offset, piece in split_text(text):
        spans.extend(Offset(s, offset) for s in detector.detect(piece, language=language))
    return spans


def merge_rows(path: Path, columns: list[str], keys: tuple[str, ...], replace: set[tuple],
               new_rows: list[dict]):
    """Rewrite a CSV keeping rows whose key was not rerun, so partial reruns merge."""
    kept = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            kept = [r for r in csv.DictReader(f) if tuple(r.get(k) for k in keys) not in replace]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(kept + new_rows)


def tally(records, dataset: str, method: str) -> list[dict]:
    """Group per-label states into results.csv rows."""
    groups = collections.defaultdict(lambda: [0, 0, 0])
    for r in records:
        key = (r["entity_type"], r["language"], r.get("location", "body"),
               r.get("identifier_type", ""), r.get("format", ""))
        groups[key][0] += 1
        groups[key][1] += r["state"] == "covered"
        groups[key][2] += r["state"] == "partial"
    return [{"dataset": dataset, "method": method, "entity_type": t, "language": lang,
             "planted": p, "covered": c, "partial": q, "location": loc,
             "identifier_type": ident, "format": fmt}
            for (t, lang, loc, ident, fmt), (p, c, q) in sorted(groups.items())]


def safe_name(doc_id: str) -> str:
    return re.sub(r"[^\w.-]+", "_", doc_id)


# ---------------------------------------------------------------- datasets

@dataclass
class Doc:
    doc_id: str
    language: str
    text: str
    mentions: list = field(default_factory=list)  # dicts: type,start,end,identifier_type
    labels: list = field(default_factory=list)    # fake only: value-based labels
    source: Path | None = None
    format: str = ""


def load_fake(args) -> list[Doc]:
    import subprocess

    from pipeline.extractors import extract_to_markdown
    from pipeline.normalization import normalize_markdown

    root = Path(args.fake_dir) if args.fake_dir else Path(args.out).parent / "fake-corpus"
    if not (root / "index.csv").exists():
        subprocess.run([sys.executable, "corpus/generate.py", "--out", str(root),
                        "--n", "10", "--seed", "42"], check=True)
    docs = []
    with (root / "index.csv").open(encoding="utf-8") as f:
        files = [row["file"] for row in csv.DictReader(f)]
    for rel in files:
        label = json.loads((root / "labels" / f"{Path(rel).stem}.json").read_text(encoding="utf-8"))
        source = (root / rel).resolve()
        try:
            text = normalize_markdown(extract_to_markdown(source, ocr_language="eng+fin"))
        except Exception as exc:  # noqa: BLE001 - keep the labels in the denominator
            print(f"  extraction failed {rel}: {exc}", flush=True)
            text = ""
        docs.append(Doc(Path(rel).stem, label["language"], text, labels=label["entities"],
                        source=source, format=label["format"]))
    return docs


def load_tab(args) -> list[Doc]:
    data = json.loads((CORPUS_ROOT / "tab" / "echr_test.json").read_text(encoding="utf-8"))
    data = sorted(data, key=lambda d: d["doc_id"])[::3][: args.tab_docs]
    docs = []
    for d in data:
        mentions = {}
        annotator = min(d["annotations"])
        for m in d["annotations"][annotator]["entity_mentions"]:
            if m["identifier_type"] == "NO_MASK" or m["entity_type"] not in TAB_TYPES:
                continue
            mentions[(m["start_offset"], m["end_offset"])] = {
                "type": TAB_TYPES[m["entity_type"]], "start": m["start_offset"],
                "end": m["end_offset"], "identifier_type": m["identifier_type"]}
        docs.append(Doc(d["doc_id"], "en", d["text"], list(mentions.values())))
    return docs


def load_turku(args) -> list[Doc]:
    folder = CORPUS_ROOT / "turku-ner" / "data" / "standoff" / "test"
    docs, sentences = [], 0
    for ann in sorted(folder.glob("*.ann")):
        text = ann.with_suffix(".txt").read_text(encoding="utf-8")
        mentions = []
        for line in ann.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) < 3 or not parts[0].startswith("T"):
                continue
            kind, start, end = parts[1].split()[:3]
            if kind in TURKU_TYPES:
                mentions.append({"type": TURKU_TYPES[kind], "start": int(start), "end": int(end)})
        docs.append(Doc(ann.stem, "fi", text, mentions))
        sentences += len(re.findall(r"[.!?](\s|$)", text))
        if sentences >= args.turku_sentences:
            break
    return docs


def load_ai4privacy(args) -> list[Doc]:
    docs = []
    for lang in ("en", "fi"):
        rows = (CORPUS_ROOT / "ai4privacy" / f"validation_{lang}.jsonl").read_text(
            encoding="utf-8").splitlines()
        picked = random.Random(42).sample(rows, min(args.ai4p_rows, len(rows)))
        for line in picked:
            row = json.loads(line)
            mentions = [{"type": AI4P_TYPES[m["label"]], "start": m["start"], "end": m["end"]}
                        for m in row["privacy_mask"] if m["label"] in AI4P_TYPES]
            docs.append(Doc(f"{lang}_{row['uid']}", lang, row["source_text"], mentions))
    return docs


def load_real_uk(args) -> list[Doc]:
    from pipeline.extractors import extract_to_markdown
    from pipeline.normalization import normalize_markdown

    docs = []
    with (REAL_UK / "manifest.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        path = REAL_UK / row["filename"]
        try:
            text = normalize_markdown(extract_to_markdown(path, ocr_language="eng"))
        except Exception as exc:  # noqa: BLE001
            print(f"  extraction failed {row['filename']}: {exc}", flush=True)
            continue
        if args.max_chars and len(text) > args.max_chars:
            print(f"  {path.name}: truncated {len(text)} -> {args.max_chars} characters", flush=True)
            text = text[: args.max_chars]
        docs.append(Doc(path.stem, "en", text, format=row["format"].lower()))
    return docs


LOADERS = {"fake": load_fake, "tab": load_tab, "turku": load_turku,
           "ai4privacy": load_ai4privacy, "real-uk": load_real_uk}


# ---------------------------------------------------------------- scoring

def score_doc(dataset: str, doc: Doc, spans) -> list[dict]:
    """One record per label or mention: entity_type, language, location, state."""
    records = []
    if dataset == "fake":
        from eval.pipeline_bench import score_label
        from pipeline.validation import location_ranges

        ranges = location_ranges(doc.text, doc.source) if doc.text else []
        for entity in doc.labels:
            s = score_label(doc.text, entity, spans, ranges, expected=1)
            state = "covered" if s["whole"] else "partial" if s["partial"] else ""
            records.append({"entity_type": entity["type"], "language": doc.language,
                            "location": entity["location"], "format": doc.format, "state": state})
        return records
    for m in doc.mentions:
        records.append({"entity_type": m["type"], "language": doc.language, "location": "body",
                        "identifier_type": m.get("identifier_type", ""),
                        "state": mention_state(m["start"], m["end"], m["type"], spans)})
    return records


def get_method(name: str):
    if name == "gliner":
        from detect.gliner_detector import GlinerDetector
        return GlinerDetector()
    return get_detector(name)


def run_dataset(dataset: str, methods: list[str], args, out: Path):
    from redact import redact, validate_spans

    print(f"\n== {dataset}: loading", flush=True)
    t_extract = time.time()
    docs = LOADERS[dataset](args)
    extract_seconds = round(time.time() - t_extract, 1)  # once per dataset, shared by all methods
    if args.limit:
        docs = docs[: args.limit]
    print(f"   {len(docs)} documents", flush=True)
    rows, detections, runtimes = [], [], []
    for method in methods:
        detector = get_method(method)
        t0 = time.time()
        for lang in {d.language for d in docs}:  # model load stays out of the timing
            detector.detect("Warm up.", language=lang)
        load_seconds = time.time() - t0
        folder = out / dataset / method
        folder.mkdir(parents=True, exist_ok=True)
        records, seconds, chars = [], 0.0, 0
        counts = collections.defaultdict(collections.Counter)
        for i, doc in enumerate(docs, 1):
            t = time.time()
            spans = validate_spans(doc.text, detect_long(detector, doc.text, doc.language)) \
                if doc.text else []
            seconds += time.time() - t
            chars += len(doc.text)
            (folder / f"{safe_name(doc.doc_id)}_anonymized.md").write_text(
                redact(doc.text, spans) if spans else doc.text, encoding="utf-8", newline="\n")
            records.extend(score_doc(dataset, doc, spans))
            for s in spans:
                counts[doc.doc_id][s.entity_type] += 1
            if i % 25 == 0 or i == len(docs):
                print(f"   {dataset}/{method}: {i}/{len(docs)} docs, {seconds:.0f}s", flush=True)
        if dataset == "real-uk":
            detections += [{"doc": d, "method": method, "entity_type": t, "count": n}
                           for d, c in counts.items() for t, n in sorted(c.items())]
        else:
            rows += tally(records, dataset, method)
        runtimes.append({"dataset": dataset, "method": method, "documents": len(docs),
                         "characters": chars, "detect_seconds": round(seconds, 1),
                         "model_load_seconds": round(load_seconds, 1),
                         "extract_seconds": extract_seconds,
                         "device": getattr(detector, "device", "cpu")})
        print(f"   {dataset}/{method} done in {seconds:.0f}s (+{load_seconds:.0f}s load)", flush=True)
    return rows, detections, runtimes


# ---------------------------------------------------------------- summary

def recall(rows, **where):
    chosen = [r for r in rows if all(r[k] == v for k, v in where.items())]
    planted = sum(int(r["planted"]) for r in chosen)
    covered = sum(int(r["covered"]) for r in chosen)
    partial = sum(int(r["partial"]) for r in chosen)
    return planted, covered, partial


def cell(rows, **where) -> str:
    planted, covered, _ = recall(rows, **where)
    return f"{covered / planted:.1%} ({covered}/{planted})" if planted else "-"


def table(header, body):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(map(str, r)) + " |" for r in body]
    return "\n".join(lines)


def write_summary(out: Path):
    with (out / "results.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    runtime = []
    if (out / "runtime.csv").exists():
        with (out / "runtime.csv").open(encoding="utf-8") as f:
            runtime = list(csv.DictReader(f))
    methods = [m for m in METHOD_NAMES if any(r["method"] == m for r in rows)]
    lines = ["# Dataset runs", "",
             ("Whole-value recall: a mention counts only when one correctly typed detection "
             "holds all of it. Partial detections are counted separately and still leak."), "",
             "## Headline recall", ""]
    view = [("fake, all locations", {"dataset": "fake"}),
            ("fake, body only", {"dataset": "fake", "location": "body"}),
            ("tab, all masked mentions", {"dataset": "tab"}),
            ("tab, DIRECT", {"dataset": "tab", "identifier_type": "DIRECT"}),
            ("tab, QUASI", {"dataset": "tab", "identifier_type": "QUASI"}),
            ("turku (fi names, orgs, places, dates)", {"dataset": "turku"}),
            ("ai4privacy, en", {"dataset": "ai4privacy", "language": "en"}),
            ("ai4privacy, fi", {"dataset": "ai4privacy", "language": "fi"})]
    lines.append(table(["dataset", *methods],
                       [[name, *[cell(rows, method=m, **w) for m in methods]] for name, w in view]))

    def breakdown(title, dataset, key, **extra):
        keys = sorted({r[key] for r in rows if r["dataset"] == dataset and r[key]})
        if not keys:
            return
        lines.extend(["", f"## {title}", ""])
        lines.append(table([key, *methods], [[k, *[cell(rows, dataset=dataset, method=m, **{key: k}, **extra)
                                                   for m in methods]] for k in keys]))

    breakdown("Fake corpus by entity type (all locations)", "fake", "entity_type")
    breakdown("Fake corpus by location", "fake", "location")
    breakdown("Fake corpus by language", "fake", "language")
    breakdown("Fake corpus by format", "fake", "format")
    breakdown("TAB by entity type (masked mentions)", "tab", "entity_type")
    breakdown("TAB by identifier type", "tab", "identifier_type")
    breakdown("Turku by entity type", "turku", "entity_type")
    breakdown("ai4privacy by entity type", "ai4privacy", "entity_type")
    if runtime:
        lines.extend(["", "## Runtime (detection only, models already loaded)", ""])
        lines.append(table(["dataset", "method", "device", "documents", "characters", "extract s (shared)",
                            "detect s", "load s"],
                           [[r["dataset"], r["method"], r.get("device", ""), r["documents"],
                             r["characters"], r.get("extract_seconds", ""), r["detect_seconds"],
                             r["model_load_seconds"]] for r in runtime]))
    lines.extend(["", "## Caveats", "",
                  ("- The fake corpus is template text with generated names. It is an upper bound; "
                  "real documents score lower."),
                  ("- PLATE, INVOICE and PERSONAL_ID are scored against recognizers written for "
                  "the generator's own formats, so they score well by construction."),
                  ("- TAB, Turku and ai4privacy label different things (court-case identifiers, "
                  "Finnish named entities, synthetic PII classes). Their numbers are not "
                  "comparable across datasets."),
                  ("- Types without a Presidio counterpart (TAB CODE, DEM, QUANTITY, MISC; "
                  "ai4privacy ID numbers, ZIPCODE, BUILDINGNUM, AGE) accept a detection of any "
                  "type, which flatters them."),
                  ("- Presidio LOCATION is mostly cities and countries, so ADDRESS, CITY and "
                  "STREET recall measures partial luck as much as design."),
                  ("- Sampled subsets: TAB test split every third document, Turku test files up "
                  "to a sentence budget, ai4privacy 300 random rows per language (seed 42)."),
                  ("- real-uk has no labels. Its counts are in detections_real_uk.csv and say "
                  "what was found, not whether it was right."),
                  "- Large spreadsheets may be truncated (see --max-chars) to keep run time sane."])
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", required=True, help="the runs/ directory to write")
    p.add_argument("--datasets", nargs="+", default=DATASETS, choices=DATASETS)
    p.add_argument("--methods", nargs="+", default=METHOD_NAMES, choices=METHOD_NAMES)
    p.add_argument("--limit", type=int, default=0, help="documents per dataset, for smoke tests")
    p.add_argument("--fake-dir", help="existing generated fake corpus; generated if omitted")
    p.add_argument("--tab-docs", type=int, default=40)
    p.add_argument("--turku-sentences", type=int, default=300)
    p.add_argument("--ai4p-rows", type=int, default=300)
    p.add_argument("--max-chars", type=int, default=400_000,
                   help="truncate real-uk documents beyond this length (0 = never)")
    p.add_argument("--pack", help="also build the manual-testing pack in this directory")
    args = p.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for dataset in args.datasets:
        rows, detections, runtimes = run_dataset(dataset, args.methods, args, out)
        merge_rows(out / "results.csv", RESULT_COLUMNS, ("dataset", "method"),
                   {(dataset, m) for m in args.methods}, rows)
        if dataset == "real-uk":
            merge_rows(out / "detections_real_uk.csv", ["doc", "method", "entity_type", "count"],
                       ("method",), {(m,) for m in args.methods}, detections)
        merge_rows(out / "runtime.csv", ["dataset", "method", "documents", "characters",
                                         "detect_seconds", "model_load_seconds", "extract_seconds",
                                         "device"],
                   ("dataset", "method"), {(dataset, m) for m in args.methods}, runtimes)
        if (out / "results.csv").exists():
            write_summary(out)
    if args.pack:
        from eval.make_pack import build_pack
        build_pack(out, Path(args.pack))


if __name__ == "__main__":
    main()
