"""Compare local OCR readers on the same labelled synthetic PNG documents."""

import argparse
import csv
import hashlib
import json
import platform
import time
import unicodedata
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path


def normalize(text: str) -> str:
    """Ignore layout whitespace and Unicode composition, not recognition errors."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def edit_distance(reference: str, hypothesis: str) -> int:
    """Return character-level Levenshtein distance with linear working memory."""
    previous = list(range(len(hypothesis) + 1))
    for index, expected in enumerate(reference, start=1):
        current = [index]
        for position, actual in enumerate(hypothesis, start=1):
            current.append(min(current[-1] + 1, previous[position] + 1,
                               previous[position - 1] + (expected != actual)))
        previous = current
    return previous[-1]


def image_cases(root: Path) -> list[dict]:
    """Load indexed PNG cases and references; never pass references to readers."""
    root = root.resolve()  # macOS temp dirs are symlinks (/var -> /private/var)
    with (root / "index.csv").open(encoding="utf-8", newline="") as handle:
        entries = [entry for entry in csv.DictReader(handle) if entry["format"] == "png"]
    if not entries:
        raise ValueError("The corpus manifest contains no PNG documents")
    cases = []
    seen = set()
    for entry in entries:
        source = (root / entry["file"]).resolve()
        if not source.is_relative_to(root) or source in seen:
            raise ValueError(f"Invalid or duplicate image path: {entry['file']}")
        seen.add(source)
        label = json.loads((root / "labels" / f"{source.stem}.json").read_text(encoding="utf-8"))
        evidence = json.loads((root / "evidence" / f"{source.stem}.json").read_text(encoding="utf-8"))
        for field in ("file", "language", "format", "quality"):
            if label[field] != entry[field]:
                raise ValueError(f"Manifest and labels disagree on {field}: {source.name}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != evidence["document_sha256"]:
            raise ValueError(f"Image differs from its generated reference: {source.name}")
        if len(evidence["images"]) != 1:
            raise ValueError(f"Expected one rendered image reference: {source.name}")
        recipe = evidence["images"][0]
        reference = normalize("\n".join([recipe["title"], *recipe["body"]]))
        if not reference or not label["entities"]:
            raise ValueError(f"Empty image reference or labels: {source.name}")
        for entity in label["entities"]:
            if (entity["location"] != "body" or not isinstance(entity["value"], str)
                    or not normalize(entity["value"])):
                raise ValueError(f"Invalid standalone-image entity label: {source.name}")
        cases.append({**label, "source": source, "reference": reference, "sha256": digest})
    return cases


def summarize(documents: list[dict]) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for document in documents:
        key = (document["language"], document["quality"])
        row = groups.setdefault(key, {
            "language": key[0], "quality": key[1], "documents": 0, "planted": 0,
            "returned": 0, "reference_characters": 0, "character_edits": 0,
            "seconds": 0.0, "errors": 0,
        })
        row["documents"] += 1
        row["planted"] += len(document["entities"])
        row["returned"] += sum(entity["returned"] for entity in document["entities"])
        row["reference_characters"] += document["reference_characters"]
        row["character_edits"] += document["character_edits"]
        row["seconds"] += document["seconds"]
        row["errors"] += bool(document["error"])
    rows = []
    for key in sorted(groups):
        row = groups[key]
        row["recall"] = row["returned"] / row["planted"]
        row["cer"] = row["character_edits"] / row["reference_characters"]
        row["seconds_per_document"] = row["seconds"] / row["documents"]
        rows.append(row)
    return rows


def evaluate(corpus_root: str | Path, reader: Callable[[Path], str], *, engine: str,
             configuration: dict | None = None) -> dict:
    """Measure OCR text without using reference text as input to the reader."""
    root = Path(corpus_root).resolve()
    documents = []
    for case in image_cases(root):
        started = time.perf_counter()
        text, error = "", None
        try:
            text = reader(case["source"])
            if not isinstance(text, str):
                raise TypeError("OCR readers must return a string")
        except Exception as exc:  # noqa: BLE001 - Preserve failed images in the denominator.
            text, error = "", f"{type(exc).__name__}: {exc}"
        elapsed = time.perf_counter() - started
        hypothesis = normalize(text)
        documents.append({
            "file": case["file"], "language": case["language"], "quality": case["quality"],
            "sha256": case["sha256"], "text": text, "error": error, "seconds": elapsed,
            "reference_characters": len(case["reference"]),
            "character_edits": edit_distance(case["reference"], hypothesis),
            "entities": [{**entity, "returned": bool(normalize(entity["value"]) in hypothesis)}
                         for entity in case["entities"]],
        })
    return {
        "engine": engine, "configuration": configuration or {},
        "corpus_root": str(root), "python": platform.python_version(),
        "corpus": (json.loads((root / "corpus.json").read_text(encoding="utf-8"))
                   if (root / "corpus.json").is_file() else None),
        "platform": platform.platform(), "documents": documents,
        "summary": summarize(documents),
    }


def make_reader(engine: str, *, paddle_detector: str = "PP-OCRv5_mobile_det") -> tuple[Callable[[Path], str], dict]:
    """Initialize a local engine once; model download/load time is excluded."""
    if engine == "tesseract":
        import pytesseract
        from PIL import Image

        def tesseract(path: Path) -> str:
            with Image.open(path) as image:
                return pytesseract.image_to_string(image, lang="eng+fin")

        return tesseract, {"version": str(pytesseract.get_tesseract_version()),
                           "languages": "eng+fin", "device": "cpu"}
    if engine == "paddleocr":
        from paddleocr import PaddleOCR

        model = PaddleOCR(
            device="cpu",
            text_detection_model_name=paddle_detector,
            text_recognition_model_name="latin_PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False, use_doc_unwarping=False,
            use_textline_orientation=False, enable_mkldnn=False,
        )

        def paddleocr(path: Path) -> str:
            return "\n".join(text for result in model.predict(str(path))
                             for text in result["rec_texts"])

        return paddleocr, {"version": version("paddleocr"), "paddle": version("paddlepaddle"),
                           "languages": "multilingual Latin (includes Finnish)", "device": "cpu",
                           "model": "PP-OCRv5", "document_preprocessing": False,
                           "detector": paddle_detector,
                           "recognizer": "latin_PP-OCRv5_mobile_rec",
                           "enable_mkldnn": False}
    if engine == "easyocr":
        import easyocr

        # EasyOCR does not list Finnish. Swedish+English is an explicitly
        # labelled Latin-script approximation, not a native Finnish setting.
        model = easyocr.Reader(["sv", "en"], gpu=False, verbose=False)

        def easyocr_reader(path: Path) -> str:
            return "\n".join(model.readtext(str(path), detail=0, paragraph=False))

        return easyocr_reader, {"version": version("easyocr"), "torch": version("torch"),
                                "languages": "sv,en",
                                "device": "cpu", "finnish_mode": "Latin approximation"}
    raise ValueError(f"Unknown OCR engine: {engine}")


def write_report(report: dict, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "details.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
    with (destination / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report["summary"][0]))
        writer.writeheader()
        writer.writerows(report["summary"])
    lines = [f"# OCR comparison: {report['engine']}", "",
             "| Language | Quality | Documents | Returned / planted | Recall | CER | Seconds / document | Errors |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in report["summary"]:
        lines.append(f"| {row['language']} | {row['quality']} | {row['documents']} | "
                     f"{row['returned']} / {row['planted']} | {row['recall']:.2%} | "
                     f"{row['cer']:.2%} | {row['seconds_per_document']:.2f} | {row['errors']} |")
    lines.extend(["", "Recall uses exact labelled values after whitespace and NFC normalization.",
                  "CER is total character edits divided by total reference characters; lower is better.",
                  "Reader failures count as missing text. Timing excludes model initialization."])
    (destination / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--engine", choices=("tesseract", "paddleocr", "easyocr"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--paddle-detector", default="PP-OCRv5_mobile_det",
                        choices=("PP-OCRv5_mobile_det", "PP-OCRv5_server_det"),
                        help="PaddleOCR detection model; mobile is the local CPU default")
    args = parser.parse_args()
    try:
        reader, configuration = make_reader(args.engine, paddle_detector=args.paddle_detector)
        report = evaluate(args.corpus, reader, engine=args.engine, configuration=configuration)
        write_report(report, args.out)
    except (OSError, ValueError, ImportError, RuntimeError) as exc:
        parser.exit(2, f"OCR benchmark could not run: {exc}\n")
    print((args.out / "summary.md").read_text(encoding="utf-8"))
    return int(any(document["error"] for document in report["documents"]))


if __name__ == "__main__":
    raise SystemExit(main())
