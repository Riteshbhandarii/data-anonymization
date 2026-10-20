"""Compare the old combined routing with context corrections on frozen inputs.

Generate the n=1 seed-42 corpus, contextual corpus and English utility suite
under ROOT first (see docs/role1-fixes.md). Model predictions are shared between
policies: only the routing/postprocessing changes. No LLM answers are generated
or scored by this command. Detailed cached spans stay in ignored outputs/.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

from detect.combined import CombinedDetector, route
from eval.contextual_bench import corpus_digest, load_corpus, score
from eval.local_llm_bench import benchmark
from redact import redact


def digest(value):
    return hashlib.sha256(value).hexdigest()


def prediction_provenance():
    """Record inference versions at capture time, not at a later cache replay."""
    project = Path(__file__).resolve().parents[1]
    return {
        "versions": {name: importlib.metadata.version(name) for name in
                     ("spacy", "gliner", "torch", "presidio-analyzer",
                      "en-core-web-sm", "fi-core-news-sm")},
        "model_source_sha256": {name: digest((project / name).read_bytes()) for name in
                                ("detect/adapter.py", "detect/gliner_detector.py",
                                 "detect/pattern_recognizers.py", "eval/bench.py")},
    }


def capture(root):
    """Freeze each family's actual predictions before comparing postprocessing."""
    from detect.methods import get_detector
    from pipeline.extractors import extract_to_markdown

    documents = []
    for path in sorted((root / "corpus/labels").glob("*.json")):
        label = json.loads(path.read_text(encoding="utf-8"))
        documents.append({"id": "body/" + path.stem, "language": label["language"],
                          "text": (root / "corpus/text" / f"{path.stem}.txt").read_text(encoding="utf-8")})
    documents.extend({"id": "contextual/" + d["id"], "language": d["language"], "text": d["text"]}
                     for d in load_corpus(root / "contextual"))
    project = Path(__file__).resolve().parents[1]
    for language, suite in (("en", root / "utility/suite.json"),
                            ("fi", project / "eval/utility_fi/suite.json")):
        for doc in json.loads(suite.read_text(encoding="utf-8"))["documents"]:
            documents.append({"id": f"utility/{language}/{doc['id']}", "language": language,
                              "text": (suite.parent / doc["file"]).read_text(encoding="utf-8")})
    documents.append({"id": "company/extracted", "language": "fi", "text": extract_to_markdown(
        root / "corpus/docx/fi_docx_00.docx")})
    detector = get_detector("combined")
    for index, doc in enumerate(documents, 1):
        for name, family in (("presidio", detector.presidio), ("model", detector.model)):
            doc[name] = [{key: getattr(span, key) for key in ("start", "end", "entity_type", "score")}
                         for span in family.detect(doc["text"], doc["language"])]
        print(f"Captured {index}/{len(documents)}", flush=True)
    return {"source_commit": "61eb73f", "documents": documents,
            "prediction_provenance": prediction_provenance()}


def compare(root, components):
    if "prediction_provenance" not in components:
        raise ValueError("Prediction versions are absent from the cache; capture a new cache")
    documents = components["documents"]
    lookup = {(d["text"], d["language"]): d for d in documents}

    class Family:
        def __init__(self, name):
            self.name = name

        def detect(self, text, language="en"):
            return [SimpleNamespace(**s) for s in lookup[text, language][self.name]]

    class Before:
        def detect(self, text, language="en"):
            return route(Family("presidio").detect(text, language),
                         Family("model").detect(text, language))

    policies = {"before": Before(),
                "after": CombinedDetector(Family("presidio"), Family("model"))}
    contextual = load_corpus(root / "contextual")
    report = {"baseline_commit": components["source_commit"],
              "scope": "Shared frozen raw model predictions; routing/context changes only. "
                       "Hours retention measures available text, not LLM answer accuracy.",
              "contextual_corpus_sha256": corpus_digest(contextual), "policies": {}}
    for name, detector in policies.items():
        body = benchmark(root / "corpus", detector)
        # Cached lookup duration is not model runtime and must not be compared
        # with historical inference timings.
        body.pop("runtime", None)
        body.pop("runtimes", None)
        if body["failed_documents"]:
            raise ValueError("Frozen predictions do not cover all body inputs")
        spans = {d["id"]: [(s.start, s.end) for s in detector.detect(d["text"], d["language"])]
                 for d in contextual}
        hours = {}
        for language in ("en", "fi"):
            quantities = retained = 0
            for doc in documents:
                if not doc["id"].startswith(f"utility/{language}/"):
                    continue
                values = re.findall(r"(?:allocated hours|varattu aika) (\d+)", doc["text"])
                cleaned = redact(doc["text"], detector.detect(doc["text"], language))
                quantities += len(values)
                retained += sum(bool(re.search(r"(?<!\d)" + value + r"(?!\d)", cleaned))
                                for value in values)
            if quantities != 6:
                raise ValueError("Expected two hour quantities in each of three memos per language")
            hours[language] = {"quantities": quantities, "retained": retained}
        report["policies"][name] = {"body": body, "contextual": score(contextual, spans),
                                    "utility_hours": hours}
    # Audit every body label, rather than accepting an unchanged aggregate that
    # could conceal a new miss compensated by an unrelated improvement.
    losses = []
    from eval.bench import TYPE_MAP, found
    for path in sorted((root / "corpus/labels").glob("*.json")):
        label = json.loads(path.read_text(encoding="utf-8"))
        text = (root / "corpus/text" / f"{path.stem}.txt").read_text(encoding="utf-8")
        by_policy = {name: detector.detect(text, label["language"])
                     for name, detector in policies.items()}
        for entity in label["entities"]:
            if entity["location"] != "body":
                continue
            state = {name: found(text, entity["value"], [s for s in spans
                     if TYPE_MAP.get(s.entity_type, s.entity_type) == entity["type"]])
                     for name, spans in by_policy.items()}
            if state["before"] == "covered" and state["after"] != "covered":
                losses.append({"document": path.stem, "type": entity["type"]})
    report["new_body_label_losses"] = losses
    report.update(components["prediction_provenance"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--components", type=Path, required=True,
                        help="Replay this cache, or capture it if it does not exist; outputs/ only")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.components.resolve().is_relative_to(
            (Path(__file__).resolve().parents[1] / "outputs").resolve()):
        parser.error("Raw component predictions must stay under ignored outputs/")
    if not args.components.exists():
        # A reproduction may download weights beforehand; scoring itself is
        # local. Explicitly select CPU unless the operator already selected one.
        os.environ.setdefault("GLINER_DEVICE", "cpu")
        payload = capture(args.root)
        args.components.parent.mkdir(parents=True, exist_ok=True)
        with args.components.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
    raw = args.components.read_bytes()
    report = compare(args.root, json.loads(raw))
    report["frozen_components_sha256"] = digest(raw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(args.out)
    if report["new_body_label_losses"]:
        raise SystemExit("Context corrections lost previously covered body identifiers")


if __name__ == "__main__":
    main()
