"""Reproduce the fixed screenshot/PDF OCR smoke samples; no random seed is used.

Run from the repository root: python -m eval.screenshot_smoke --out outputs/smoke
Requires Pillow, PyMuPDF, pytesseract, Arial and Tesseract with eng+fin data.
Only --method combined additionally loads detector dependencies and weights.
"""

import argparse
import hashlib
import io
import json
import os
from importlib.metadata import version
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageDraw, ImageFont

from pipeline.errors import PipelineError
from pipeline.extractors import extract_to_markdown
from redact.image import layout, ocr_words

SAMPLES = (
    ("en", "Contact Alice Example\nEmail alice@example.test\nCall +358 40 123 4567",
     ("Alice Example", "alice@example.test")),
    ("fi", "Yhteystiedot Väinö Mäkinen\nSähköposti vaino@example.test\nPuhelin +358 40 123 4567",
     ("Väinö Mäkinen", "vaino@example.test")),
)
SCAN_VALUES = ("scan-one@example.test", "scan-two@example.test", "scan-three@example.test")


def resolve_font(font: Path | None) -> Path:
    """Find Arial by an exact path; never substitute another font silently."""
    if font is None:
        candidates = (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/arial.ttf",
                      Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
                      Path("/Library/Fonts/Arial.ttf"),
                      Path("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"),
                      Path("/usr/share/fonts/truetype/msttcorefonts/arial.ttf"))
        font = next((path for path in candidates if path.is_file()), None)
    if font is None or not Path(font).is_file():
        raise FileNotFoundError("Arial font not found; pass --font /path/to/arial.ttf. No fallback is used.")
    ImageFont.truetype(str(font), 12)  # Fail explicitly for an unreadable font.
    return Path(font).resolve()


def run_smoke(out: Path, font: Path | None, *, method: str | None = None) -> tuple[list[dict], dict]:
    """Save identical fixture pixels and report actual OCR, with optional detection."""
    font = resolve_font(font)
    provenance = {"font_file": str(font), "font_sha256": hashlib.sha256(font.read_bytes()).hexdigest(),
                  "font_name": ImageFont.truetype(str(font), 12).getname(),
                  "tesseract": str(pytesseract.get_tesseract_version()),
                  **{package: version(package) for package in ("pytesseract", "pillow", "pymupdf")}}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for size in (12, 14):
        for language, text, values in SAMPLES:
            image = Image.new("RGB", (640, 140), "white")
            ImageDraw.Draw(image).multiline_text((16, 16), text, fill="black", spacing=12,
                                                font=ImageFont.truetype(str(font), size))
            image.save(out / f"small-{language}-{size}px.png")
            for scale in (1, 2):
                actual = layout(ocr_words(image, "eng+fin", scale=scale))[0]
                rows.append({"language": language, "font_px": size, "scale": scale,
                             "found": sum(value in actual for value in values), "total": len(values),
                             "ocr": actual, "values": [{"value": value, "extracted": value in actual}
                                                       for value in values], "provenance": provenance})
    pdf = out / "scanned-smoke.pdf"
    with pymupdf.open() as document:
        for value in SCAN_VALUES:
            image = Image.new("RGB", (1000, 300), "white")
            ImageDraw.Draw(image).text((30, 100), "Email " + value, fill="black",
                                      font=ImageFont.truetype(str(font), 32))
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            page = document.new_page(width=500, height=150)
            page.insert_image(page.rect, stream=buffer.getvalue())
        document.save(pdf)
        native_text_empty = [not page.get_text().strip() for page in document]
    text = extract_to_markdown(pdf, ocr_language="eng+fin")
    (out / "scanned-smoke.md").write_text(text, encoding="utf-8")
    values = [{"value": value, "extracted": value in text, "detected": None} for value in SCAN_VALUES]
    if method is not None:
        from detect.methods import get_detector
        from eval.bench import found

        spans = get_detector(method).detect(text, language="en")
        for entity in values:
            entity["detected"] = found(text, entity["value"], spans) == "covered"
    scanned = {"pages": 3, "native_text_empty": native_text_empty, "values": values,
               "method": method, "detection_status": "not_run" if method is None else "completed",
               "provenance": provenance}
    for name, report in (("small-text-smoke.json", rows), ("scanned-smoke.json", scanned)):
        (out / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows, scanned


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Directory for fixtures and JSON reports")
    parser.add_argument("--font", type=Path, help="Exact font file; use Arial to reproduce the recorded samples")
    parser.add_argument("--method", choices=("combined",), help="Also test detection on extracted PDF text")
    args = parser.parse_args(argv)
    try:
        run_smoke(args.out, args.font, method=args.method)
    except (OSError, ValueError, RuntimeError, ImportError, PipelineError) as exc:
        parser.exit(2, f"Screenshot smoke could not run: {exc}\n")
    print(f"Smoke fixtures and reports saved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
