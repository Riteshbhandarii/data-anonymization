"""Measure how much of a screenshot image redaction actually hides.

    python corpus/generate.py --out outputs/screenshot/corpus --n 10 --seed 42
    python -m eval.screenshot_bench outputs/screenshot/corpus --out outputs/screenshot/report

For every synthetic PNG and method: OCR the original as an attacker would,
redact the image, then judge each labelled value on the redacted pixels.

    unread   OCR could not read the whole value even before redaction
    leaked   OCR still reads the whole value after redaction
    partial  not leaked, but a word of it is not fully covered by black
    hidden   every word of every occurrence is covered by black

Image recall is hidden / readable before. Coverage is checked on the output
pixels rather than on the boxes a tool reports, so every tool is judged the
same way. Over-redaction is the share of OCR words that were blacked out.
Text recall runs the same detector on the generator's text for each image.
"""

import argparse
import csv
import importlib.metadata
import json
import time
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from PIL import Image

from eval.bench import found
from eval.ocr_bench import image_cases, normalize
from eval.run_matrix import METHOD_NAMES, get_method
from redact.image import Word, layout, ocr_words, redact_image

OCR_LANGUAGE = "eng+fin"
IMAGE_REDACTOR = {"presidio-image": "basic", "presidio-image-rules": "rules"}
METHODS = [*METHOD_NAMES, *IMAGE_REDACTOR]

# A word counts as blacked out when nearly all of its box is near-black.
# Uncovered dark text fills well under half of its own box.
DARK = 32
COVERED = 0.9


def find_occurrences(words: Sequence[Word], value: str) -> list[list[int]]:
    """Word indices of every place the OCR text contains the whole value."""
    text, ranges = layout([replace(word, text=normalize(word.text)) for word in words])
    text = text.replace("\n", " ")
    needle = normalize(value)
    occurrences = []
    position = text.find(needle)
    while needle and position >= 0:
        end = position + len(needle)
        occurrences.append([index for index, (start, stop) in enumerate(ranges)
                            if start < end and stop > position])
        position = text.find(needle, position + 1)
    return occurrences


def blacked(gray: Image.Image, box: tuple[int, int, int, int]) -> bool:
    """Whether a box in a greyscale image is almost entirely near-black."""
    left, top, right, bottom = box
    region = gray.crop((left, top, max(right, left + 1), max(bottom, top + 1)))
    return sum(region.histogram()[:DARK + 1]) >= COVERED * region.width * region.height


def value_state(occurrences: list[list[int]], covered: Sequence[bool], still_read: bool) -> str:
    if not occurrences:
        return "unread"
    if still_read:
        return "leaked"
    if all(covered[index] for occurrence in occurrences for index in occurrence):
        return "hidden"
    return "partial"


def score_image(words: Sequence[Word], after: Image.Image, after_words: Sequence[Word],
                entities: list[dict]) -> dict:
    """Value states and word counts for one redacted image."""
    gray = after.convert("L")
    covered = [blacked(gray, word.box) for word in words]
    after_text = normalize(layout(after_words)[0])
    states, label_words = [], set()
    for entity in entities:
        occurrences = find_occurrences(words, entity["value"])
        label_words.update(index for occurrence in occurrences for index in occurrence)
        still_read = bool(occurrences) and normalize(entity["value"]) in after_text
        states.append({"type": entity["type"], "value": entity["value"],
                       "state": value_state(occurrences, covered, still_read)})
    other = [index for index in range(len(words)) if index not in label_words]
    return {"entities": states, "words": len(words), "words_blacked": sum(covered),
            "other_words": len(other), "other_words_blacked": sum(covered[index] for index in other)}


def summarize(documents: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups = {}
    for document in documents:
        key = tuple(document[name] for name in keys)
        row = groups.setdefault(key, {
            **dict(zip(keys, key, strict=True)), "documents": 0, "planted": 0, "unread": 0,
            "hidden": 0, "partial": 0, "leaked": 0, "words": 0, "words_blacked": 0,
            "other_words": 0, "other_words_blacked": 0, "text_hidden": 0, "seconds": 0.0,
        })
        row["documents"] += 1
        row["planted"] += len(document["entities"])
        for entity in document["entities"]:
            row[entity["state"]] += 1
            row["text_hidden"] += entity.get("text_hidden", False)
        for field in ("words", "words_blacked", "other_words", "other_words_blacked", "seconds"):
            row[field] += document[field]
    rows = []
    for key in sorted(groups):
        row = groups[key]
        readable = row["planted"] - row["unread"]
        row["readable_before"] = readable
        row["image_recall"] = row["hidden"] / readable if readable else 0.0
        row["hidden_of_planted"] = row["hidden"] / row["planted"]
        row["text_recall"] = row["text_hidden"] / row["planted"]
        row["over_redaction"] = row["words_blacked"] / row["words"] if row["words"] else 0.0
        row["other_words_redacted"] = (row["other_words_blacked"] / row["other_words"]
                                       if row["other_words"] else 0.0)
        row["seconds_per_image"] = row.pop("seconds") / row["documents"]
        rows.append(row)
    return rows


def make_redactor(method: str, *, whole_lines: bool = False, ocr_scale: int = 1):
    """Return the method's text detector and redact(image, language) -> redacted image.

    Both kinds of redactor run their own OCR, so the timings are comparable.
    """
    if method in IMAGE_REDACTOR and (whole_lines or ocr_scale != 1):
        raise ValueError("Whole-line masking and OCR scaling require a repository image redactor")
    detector = get_method(IMAGE_REDACTOR.get(method, method))
    if method in IMAGE_REDACTOR:
        from presidio_image_redactor import ImageAnalyzerEngine, ImageRedactorEngine

        # Same analyzer and threshold as the text method, so only the OCR
        # handling and box drawing differ.
        engine = ImageRedactorEngine(ImageAnalyzerEngine(analyzer_engine=detector.analyzer))
        return detector, lambda image, language: engine.redact(
            image, ocr_kwargs={"lang": OCR_LANGUAGE}, language=language,
            score_threshold=detector.score_threshold)
    return detector, lambda image, language: redact_image(
        image, detector, language=language, ocr_language=OCR_LANGUAGE,
        whole_lines=whole_lines, ocr_scale=ocr_scale)[0]


def evaluate(corpus_root: Path, methods: list[str], image_dir: Path | None = None, *,
             whole_lines: bool = False, ocr_scale: int = 1) -> list[dict]:
    """Score every method on every image, and its detector on the same text.

    The text score uses the generator's saved text for the image and counts a
    value when detections cover all of it, of any type, as a box would.
    Reference and post-redaction OCR remain at 1x for comparable denominators;
    ``ocr_scale`` changes only the redactor's OCR.
    """
    root = Path(corpus_root).resolve()
    originals = []
    for case in image_cases(root):
        with Image.open(case["source"]) as image:
            image = image.convert("RGB")
        text = (root / "text" / f"{case['source'].stem}.txt").read_text(encoding="utf-8")
        originals.append((case, image, ocr_words(image, OCR_LANGUAGE), text))
    documents = []
    for method in methods:
        print(f"== {method}", flush=True)
        detector, redactor = make_redactor(method, whole_lines=whole_lines, ocr_scale=ocr_scale)
        for case, image, words, text in originals:
            started = time.perf_counter()
            after = redactor(image, case["language"])
            seconds = time.perf_counter() - started
            if image_dir is not None:
                (image_dir / method).mkdir(parents=True, exist_ok=True)
                after.save(image_dir / method / case["source"].name)
            scores = score_image(words, after, ocr_words(after, OCR_LANGUAGE), case["entities"])
            spans = detector.detect(text, language=case["language"])
            for entity in scores["entities"]:
                entity["text_hidden"] = found(text, entity["value"], spans) == "covered"
            documents.append({"method": method, "file": case["file"], "language": case["language"],
                              "quality": case["quality"], "seconds": seconds, **scores})
    return documents


def versions() -> dict:
    import pytesseract

    used = {}
    for package in ("presidio-analyzer", "presidio-image-redactor", "gliner", "pytesseract"):
        try:
            used[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            used[package] = None
    used["tesseract"] = str(pytesseract.get_tesseract_version())
    return used


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def format_summary(by_group: list[dict], by_method: list[dict], used: dict, *,
                   whole_lines: bool = False, ocr_scale: int = 1) -> str:
    lines = ["# Screenshot redaction benchmark", "",
             (f"Masking: {'whole OCR lines' if whole_lines else 'detected words'}. "
              f"Redactor OCR: {ocr_scale}x. Reference and output OCR: 1x."), "",
             ("| Method | Language | Quality | Readable / planted | Hidden | Partial | Leaked | Image recall | "
              "Hidden / planted | Text recall | Words blacked | Non-label words blacked | Seconds / image |"),
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in [*by_group, *({**row, "language": "all", "quality": "all"} for row in by_method)]:
        lines.append(f"| {row['method']} | {row['language']} | {row['quality']} | "
                     f"{row['readable_before']} / {row['planted']} | {row['hidden']} | {row['partial']} | "
                     f"{row['leaked']} | {row['image_recall']:.1%} | {row['hidden_of_planted']:.1%} | "
                     f"{row['text_recall']:.1%} | {row['over_redaction']:.1%} | "
                     f"{row['other_words_redacted']:.1%} | {row['seconds_per_image']:.2f} |")
    lines.extend(["", "Image recall is hidden / readable before redaction. Partial means a word of the",
                  "value is still visible; leaked means OCR still reads the whole value. Text recall",
                  "runs the same detector on the generator's text for the image, any type counting.",
                  "", "Versions: " + ", ".join(f"{name} {value}" for name, value in used.items())])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--methods", nargs="+", default=METHODS, choices=METHODS)
    parser.add_argument("--no-images", action="store_true", help="do not save the redacted PNGs")
    parser.add_argument("--whole-lines", action="store_true",
                        help="mask every OCR word on a line containing a detection")
    parser.add_argument("--ocr-scale", type=int, choices=(1, 2, 3), default=1,
                        help="upscale only the redactor's OCR; scoring OCR stays at 1x")
    args = parser.parse_args()
    if (args.whole_lines or args.ocr_scale != 1) and any(m in IMAGE_REDACTOR for m in args.methods):
        parser.error("--whole-lines/--ocr-scale require --methods without presidio-image variants")
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        documents = evaluate(args.corpus, args.methods, None if args.no_images else args.out / "redacted",
                             whole_lines=args.whole_lines, ocr_scale=args.ocr_scale)
    except (OSError, ValueError, ImportError) as exc:
        parser.exit(2, f"Screenshot benchmark could not run: {exc}\n")
    by_group = summarize(documents, ("method", "language", "quality"))
    by_method = summarize(documents, ("method",))
    used = versions()
    write_csv(args.out / "summary.csv", by_group)
    write_csv(args.out / "by_method.csv", by_method)
    write_csv(args.out / "values.csv", [{"method": d["method"], "file": d["file"], **entity}
                                        for d in documents for entity in d["entities"]])
    configuration = {"whole_lines": args.whole_lines, "ocr_scale": args.ocr_scale,
                     "scoring_ocr_scale": 1}
    (args.out / "details.json").write_text(json.dumps({"versions": used, "configuration": configuration,
                                                      "documents": documents},
                                                      ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = format_summary(by_group, by_method, used,
                             whole_lines=args.whole_lines, ocr_scale=args.ocr_scale)
    (args.out / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
