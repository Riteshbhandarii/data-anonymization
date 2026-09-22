#!/usr/bin/env python3
"""Score a detector against the labelled corpus.

Reads the plain text the generator saved beside each document, so this measures
the detector on its own. Identifiers planted in metadata, speaker notes and
hidden sheets are not in that text and are skipped here on purpose: they are an
extraction question, and mixing the two hides which stage lost the value.

    python3 corpus/generate.py --out ./bench --n 25
    python3 eval/bench.py ./bench

Writes eval/baselines/presidio.json, which is committed. Results over the
synthetic corpus hold invented values and are safe to publish; anything run
over real documents belongs in eval/results/, which git ignores.
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
    """True when a detection of the right type overlaps this value in the text."""
    start = text.find(value)
    if start < 0:
        return None  # not in the visible text, so not this benchmark's business
    end = start + len(value)
    return any(r.start < end and r.end > start for r in results)


def verdict(entity_type, planted, hit):
    """A word per type, so a future run is readable without reading the code."""
    if not planted:
        return "not in corpus"
    if hit == 0:
        return "no recognizer" if entity_type not in TYPE_MAP.values() else "recognizer rejects all"
    return "good" if hit / planted >= 0.95 else "weak"


def main(root):
    analyzer = build_analyzer()
    counts = collections.defaultdict(lambda: [0, 0])  # (lang, type) -> [planted, hit]
    misses = []

    for name in sorted(os.listdir(os.path.join(root, "labels"))):
        with open(os.path.join(root, "labels", name), encoding="utf-8") as f:
            doc = json.load(f)
        lang = doc["language"]
        with open(os.path.join(root, "text", f"{name[:-5]}.txt"), encoding="utf-8") as f:
            text = f.read()

        results = analyzer.analyze(text=text, language=lang, score_threshold=THRESHOLD)
        by_type = collections.defaultdict(list)
        for r in results:
            by_type[TYPE_MAP.get(r.entity_type)].append(r)

        for e in doc["entities"]:
            hit = found(text, e["value"], by_type[e["type"]])
            if hit is None:
                continue
            counts[(lang, e["type"])][0] += 1
            counts[(lang, e["type"])][1] += hit
            if not hit:
                misses.append({"file": doc["file"], "type": e["type"], "value": e["value"]})

    with open(os.path.join(root, "corpus.json"), encoding="utf-8") as f:
        corpus = json.load(f)
    report(counts, misses, corpus)


def report(counts, misses, corpus):
    types = sorted({t for _, t in counts})
    langs = sorted({lang for lang, _ in counts})
    recall = {}

    print(f"{'type':<14}" + "".join(f"{lang:>14}" for lang in langs) + "   verdict")
    for t in types:
        row = f"{t:<14}"
        for lang in langs:
            planted, hit = counts.get((lang, t), [0, 0])
            recall[f"{lang}/{t}"] = {"planted": planted, "found": hit,
                                     "verdict": verdict(t, planted, hit)}
            row += f"{hit:>5}/{planted:<4}{hit / planted:>5.0%}" if planted else f"{'-':>14}"
        order = ["no recognizer", "recognizer rejects all", "weak", "good", "not in corpus"]
        worst = min((recall[f"{lang}/{t}"]["verdict"] for lang in langs), key=order.index)
        print(f"{row}   {worst}")

    total = sum(p for p, _ in counts.values())
    hits = sum(h for _, h in counts.values())
    print(f"\n{hits}/{total} body identifiers found, {hits / total:.0%} recall")

    out = os.path.join(os.path.dirname(__file__), "baselines", "presidio.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "detector": "presidio-analyzer",
            "versions": {p: importlib.metadata.version(p) for p in ("presidio-analyzer", "spacy")},
            "models": MODELS,
            "score_threshold": THRESHOLD,
            "corpus": corpus,
            "scope": "body labels only, metadata/notes/hidden sheets need extraction",
            "recall": recall,
            "misses": misses,
        }, f, ensure_ascii=False, indent=2)
    print(f"-> {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "./bench")
