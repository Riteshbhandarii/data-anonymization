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

import collections
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
}

MODELS = {"en": "en_core_web_sm", "fi": "fi_core_news_sm"}

# Presidio's own default. Recorded because raising it trades recall for
# precision, and two runs at different thresholds are not comparable.
THRESHOLD = 0.0


def build_analyzer():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": c, "model_name": m} for c, m in MODELS.items()],
    }
    engine = NlpEngineProvider(nlp_configuration=config).create_engine()
    return AnalyzerEngine(nlp_engine=engine, supported_languages=list(MODELS))


def found(text, value, results):
    """True when a detection of the right type overlaps this value in the text.

    Every occurrence counts, not just the first. Company names in particular
    repeat, and finding the second one is still finding it.
    """
    start = text.find(value)
    while start >= 0:
        end = start + len(value)
        if any(r.start < end and r.end > start for r in results):
            return True
        start = text.find(value, start + 1)
    return False


def verdict(entity_type, planted, hit):
    """A word per type, so a future run is readable without reading the code."""
    if not planted:
        return "not in corpus"
    if hit == 0:
        return "no recognizer" if entity_type not in TYPE_MAP.values() else "recognizer rejects all"
    return "good" if hit / planted >= 0.95 else "weak"


def main(root, baseline=False):
    analyzer = build_analyzer()
    counts = collections.defaultdict(lambda: [0, 0])  # (lang, fmt, type) -> [planted, hit]
    misses = []

    for name in sorted(os.listdir(os.path.join(root, "labels"))):
        with open(os.path.join(root, "labels", name), encoding="utf-8") as f:
            doc = json.load(f)
        lang, fmt = doc["language"], doc["format"]
        with open(os.path.join(root, "text", f"{name[:-5]}.txt"), encoding="utf-8") as f:
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
            hit = found(text, e["value"], by_type[e["type"]])
            counts[(lang, fmt, e["type"])][0] += 1
            counts[(lang, fmt, e["type"])][1] += hit
            if not hit:
                misses.append({"file": doc["file"], "type": e["type"], "value": e["value"]})

    with open(os.path.join(root, "corpus.json"), encoding="utf-8") as f:
        corpus = json.load(f)
    report(counts, misses, corpus, baseline)


def totals(counts, *keys):
    """Planted and found, summed over whichever parts of the key are fixed."""
    out = collections.defaultdict(lambda: [0, 0])
    for key, (planted, hit) in counts.items():
        picked = tuple(key[i] for i in keys)
        out[picked][0] += planted
        out[picked][1] += hit
    return out


def report(counts, misses, corpus, baseline):
    by_lang_type = totals(counts, 0, 2)
    types = sorted({t for _, _, t in counts})
    langs = sorted({lang for lang, _, _ in counts})
    order = ["no recognizer", "recognizer rejects all", "weak", "good", "not in corpus"]
    recall = {}

    print(f"{'type':<14}" + "".join(f"{lang:>14}" for lang in langs) + "   verdict")
    for t in types:
        row = f"{t:<14}"
        for lang in langs:
            planted, hit = by_lang_type.get((lang, t), [0, 0])
            recall[f"{lang}/{t}"] = {"planted": planted, "found": hit,
                                     "verdict": verdict(t, planted, hit)}
            row += f"{hit:>5}/{planted:<4}{hit / planted:>5.0%}" if planted else f"{'-':>14}"
        worst = min((recall[f"{lang}/{t}"]["verdict"] for lang in langs), key=order.index)
        print(f"{row}   {worst}")

    total = sum(p for p, _ in counts.values())
    hits = sum(h for _, h in counts.values())
    print(f"\n{hits}/{total} body identifiers found, {hits / total:.0%} recall")

    models = {p: importlib.metadata.version(p) for p in ("presidio-analyzer", "spacy")}
    # The model weights are their own packages. Updating them changes every
    # number while the spacy version stays put, so they are recorded too.
    models.update({m: importlib.metadata.version(m) for m in MODELS.values()})

    # ../docs/evaluation.md asks for recall per entity type and per document
    # format. The table above is the readable cut; the format cut lives here.
    by_fmt_type = totals(counts, 1, 2)
    write(os.path.join("baselines" if baseline else "results", "presidio.json"), {
        "detector": "presidio-analyzer",
        "versions": models,
        "models": MODELS,
        "score_threshold": THRESHOLD,
        "corpus": corpus,
        "scope": "body labels only, metadata/notes/hidden sheets need extraction",
        "recall": recall,
        "recall_by_format": {f"{fmt}/{t}": {"planted": p, "found": h}
                             for (fmt, t), (p, h) in sorted(by_fmt_type.items())},
    })
    # Every failure individually, which is what you read to decide what to fix.
    # It grows with the corpus and regenerates in seconds, so it stays untracked.
    # The values are verbatim, so treat it like the documents it came from.
    write(os.path.join("results", "presidio-misses.json"), misses)


def write(name, payload):
    path = os.path.join(os.path.dirname(__file__), name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"-> {path}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--baseline"]
    main(args[0] if args else "./bench", baseline="--baseline" in sys.argv)
