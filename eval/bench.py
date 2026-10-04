#!/usr/bin/env python3
"""Score a detector against the labelled corpus.

Reads the plain text the generator saved beside each document, so this measures
the detector on its own. Identifiers planted in metadata, speaker notes and
hidden sheets are not in that text and are skipped here on purpose: they are an
extraction question, and mixing the two hides which stage lost the value.

    python3 -m spacy download en_core_web_sm
    python3 -m spacy download fi_core_news_sm
    python3 corpus/generate.py --out ./bench --n 25
    python3 eval/bench.py ./bench

Writes eval/results/, which git ignores. Pass --baseline to write the
committed eval/baselines/presidio.json instead, which is only for runs over
the synthetic corpus: its values are invented and safe to publish, and real
documents must never end up in a tracked file.
"""

import argparse
import collections
import csv
import hashlib
import importlib.metadata
import json
import os
import sys

# Presidio's entity names on the left, the corpus label types on the right.
# A benchmark cheats here if anywhere, so the whole mapping stays visible.
TYPE_MAP = {
    "PERSON": "PERSON",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "IBAN_CODE": "IBAN",
    "LOCATION": "ADDRESS",
    "ORGANIZATION": "COMPANY",
    "DATE_TIME": "DATE",
    "FI_PERSONAL_IDENTITY_CODE": "PERSONAL_ID",
    # Custom recognizers from detect/pattern_recognizers.py, used with --custom.
    "PLATE": "PLATE",
    "INVOICE": "INVOICE",
    "PERSONAL_ID": "PERSONAL_ID",
}

MODEL_SETS = {
    "sm": {"en": "en_core_web_sm", "fi": "fi_core_news_sm"},
    "lg": {"en": "en_core_web_lg", "fi": "fi_core_news_lg"},
}

# Presidio's own default. Recorded because raising it trades recall for
# precision, and two runs at different thresholds are not comparable.
THRESHOLD = 0.0


def result_name(size, custom):
    """Output file stem. The default configuration keeps its original name."""
    if size == "sm" and not custom:
        return "presidio"
    return "presidio" + ("-custom" if custom else "") + f"-{size}"


def build_analyzer(models=None, custom=False):
    """Presidio with the given spaCy models; small models and defaults if omitted."""
    models = MODEL_SETS["sm"] if models is None else models
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": c, "model_name": m} for c, m in models.items()],
    }
    engine = NlpEngineProvider(nlp_configuration=config).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=engine, supported_languages=list(models))
    if custom:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from detect.pattern_recognizers import register_project_recognizers
        register_project_recognizers(analyzer, list(models))
    return analyzer


def found(text, value, results):
    """How well a detection of the right type covers this value in the text.

    Returns "covered" when every occurrence is held whole by a span, "partial"
    when something was found but part of the value survives somewhere, and ""
    for nothing.

    Both rules are strict for the same reason. Presidio returns only the city
    out of a full street address, and one label stands for every occurrence of
    that value, so a company name caught in the first row and missed in the
    second is still readable in the second.
    """
    states = []
    start = text.find(value)
    while start >= 0:
        end = start + len(value)
        if any(r.start <= start and r.end >= end for r in results):
            states.append("covered")
        elif any(r.start < end and r.end > start for r in results):
            states.append("partial")
        else:
            states.append("")
        start = text.find(value, start + 1)

    if states and all(s == "covered" for s in states):
        return "covered"
    return "partial" if any(states) else ""


def verdict(entity_type, planted, covered, partial, recognized=None):
    """A word per type, so a future run is readable without reading the code.

    `recognized` is the set of corpus types the analyzer actually has a
    recognizer for. Without it, every type in TYPE_MAP is assumed loaded.
    """
    if recognized is None:
        recognized = set(TYPE_MAP.values())
    if not planted:
        return "not in corpus"
    if covered == 0:
        if partial:
            return "partial only"
        return "no recognizer" if entity_type not in recognized else "recognizer rejects all"
    return "good" if covered / planted >= 0.95 else "weak"


def main(root, baseline=False, size="sm", custom=False):
    models = MODEL_SETS[size]
    analyzer = build_analyzer(models, custom)
    # (lang, fmt, type) -> [planted, covered, partial]
    counts = collections.defaultdict(lambda: [0, 0, 0])
    misses = []

    # Driven from the manifest rather than the directory listing. A smaller --n
    # into a used output directory leaves older documents behind, and scoring
    # those against the new corpus.json describes two different corpora.
    stems = manifest(root)
    for stem in stems:
        with open(os.path.join(root, "labels", f"{stem}.json"), encoding="utf-8") as f:
            doc = json.load(f)
        lang, fmt = doc["language"], doc["format"]
        with open(os.path.join(root, "text", f"{stem}.txt"), encoding="utf-8") as f:
            text = f.read()

        results = analyzer.analyze(text=text, language=lang, score_threshold=THRESHOLD)
        by_type = collections.defaultdict(list)
        for r in results:
            by_type[TYPE_MAP.get(r.entity_type)].append(r)

        # Body labels only. A value planted in metadata often appears in the body
        # as well, and counting that copy would score extraction's job as this
        # benchmark's and inflate the denominator.
        for e in doc["entities"]:
            if e["location"] != "body":
                continue
            how = found(text, e["value"], by_type[e["type"]])
            counts[(lang, fmt, e["type"])][0] += 1
            counts[(lang, fmt, e["type"])][1] += how == "covered"
            counts[(lang, fmt, e["type"])][2] += how == "partial"
            if how != "covered":
                misses.append({"file": doc["file"], "type": e["type"],
                               "value": e["value"], "detected": how or "nothing"})

    with open(os.path.join(root, "corpus.json"), encoding="utf-8") as f:
        corpus = json.load(f)
    actual = fingerprint(root, stems)
    if actual != corpus.get("corpus_sha256"):
        raise SystemExit(
            f"Corpus does not match its own provenance.\n"
            f"  corpus.json says {corpus.get('corpus_sha256')}\n"
            f"  the scored files are {actual}\n"
            f"Regenerate it; a result carrying the wrong digest is worse than none."
        )
    report(counts, misses, corpus, baseline, size, custom,
           {TYPE_MAP[e] for lang in models
            for e in getattr(analyzer, "get_supported_entities", lambda _: [])(lang)
            if e in TYPE_MAP})


def manifest(root):
    """The document stems this corpus actually declares, in index.csv order."""
    with open(os.path.join(root, "index.csv"), encoding="utf-8") as f:
        return [os.path.splitext(os.path.basename(row["file"]))[0]
                for row in csv.DictReader(f)]


def fingerprint(root, stems):
    """Recompute the corpus digest from the files actually about to be scored.

    Deliberately a second implementation rather than a shared one. A hash the
    verifier takes on trust from the thing it verifies proves nothing, and a
    result carrying a digest that was never checked is decoration.
    """
    digest = hashlib.sha256()
    for stem in stems:
        for part in (f"labels/{stem}.json", f"text/{stem}.txt"):
            with open(os.path.join(root, part), "rb") as f:
                digest.update(f.read())
    return digest.hexdigest()


def totals(counts, *keys):
    """Planted, covered and partial, summed over the parts of the key kept."""
    out = collections.defaultdict(lambda: [0, 0, 0])
    for key, values in counts.items():
        picked = tuple(key[i] for i in keys)
        for i, v in enumerate(values):
            out[picked][i] += v
    return out


def report(counts, misses, corpus, baseline, size, custom, recognized):
    models_used = MODEL_SETS[size]
    by_lang_type = totals(counts, 0, 2)
    types = sorted({t for _, _, t in counts})
    langs = sorted({lang for lang, _, _ in counts})
    order = ["no recognizer", "recognizer rejects all", "partial only", "weak",
             "good", "not in corpus"]
    recall = {}

    print(f"{'type':<13}" + "".join(f"{lang:>17}" for lang in langs) + "   verdict")
    for t in types:
        row = f"{t:<13}"
        for lang in langs:
            planted, covered, partial = by_lang_type.get((lang, t), [0, 0, 0])
            recall[f"{lang}/{t}"] = {"planted": planted, "covered": covered,
                                     "partial": partial,
                                     "verdict": verdict(t, planted, covered, partial, recognized)}
            row += (f"{covered:>5}/{planted:<4}{covered / planted:>4.0%}{partial:>4}p"
                    if planted else f"{'-':>17}")
        worst = min((recall[f"{lang}/{t}"]["verdict"] for lang in langs), key=order.index)
        print(f"{row}   {worst}")

    total = sum(p for p, _, _ in counts.values())
    hits = sum(c for _, c, _ in counts.values())
    part = sum(p for _, _, p in counts.values())
    print(f"\n{hits}/{total} body identifiers fully covered, {hits / total:.0%}. "
          f"{part} more were partly detected, which still leaks the rest.")

    name = result_name(size, custom)
    models = {p: importlib.metadata.version(p) for p in ("presidio-analyzer", "spacy")}
    # The model weights are their own packages. Updating them changes every
    # number while the spacy version stays put, so they are recorded too.
    models.update({m: importlib.metadata.version(m) for m in models_used.values()})

    # ../docs/evaluation.md asks for recall per entity type and per document
    # format. The table above is the readable cut; the format cut lives here.
    by_fmt_type = totals(counts, 1, 2)
    write(os.path.join("baselines" if baseline else "results", f"{name}.json"), {
        "detector": "presidio-analyzer",
        "versions": models,
        "models": models_used,
        "custom_recognizers": custom,
        "score_threshold": THRESHOLD,
        "corpus": corpus,
        "scope": ("body labels only, metadata/notes/hidden sheets need extraction. "
                  "Template sentences with generated names, so these are an upper "
                  "bound and real documents will score lower."),
        "counts": "covered means a detection held the whole value; partial left some of it",
        "recall": recall,
        "recall_by_format": {f"{fmt}/{t}": {"planted": p, "covered": c, "partial": q}
                             for (fmt, t), (p, c, q) in sorted(by_fmt_type.items())},
    })
    # Every failure individually, which is what you read to decide what to fix.
    # It grows with the corpus and regenerates in seconds, so it stays untracked.
    # The values are verbatim, so treat it like the documents it came from.
    write(os.path.join("results", f"{name}-misses.json"), misses)


def write(name, payload):
    path = os.path.join(os.path.dirname(__file__), name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"-> {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("root", nargs="?", default="./bench")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--models", choices=sorted(MODEL_SETS), default="sm")
    parser.add_argument("--custom", action="store_true",
                        help="add the plate, invoice and identity code recognizers")
    a = parser.parse_args()
    main(a.root, baseline=a.baseline, size=a.models, custom=a.custom)
