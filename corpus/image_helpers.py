"""Deterministic text images and rendering evidence for synthetic fixtures.

Evidence checks generator output; it is never an OCR result. The verifier
re-renders the recorded text and compares pixels with the document's images.
"""

import hashlib
import io
import json
from pathlib import Path

import reportlab
from PIL import Image, ImageDraw, ImageFont

QUALITIES = ("clean", "low_resolution")
RENDERER_VERSION = 1


def pixel_digest(image):
    """Hash dimensions and RGB pixels, independently of PNG/PDF encoding."""
    rgb = image.convert("RGB")
    digest = hashlib.sha256(f"{rgb.width}x{rgb.height}:RGB:".encode())
    digest.update(rgb.tobytes())
    return digest.hexdigest()


def render_text_image(title, body, quality="clean"):
    """Grow the canvas to fit complete lines without wrapping identifiers."""
    if quality not in QUALITIES:
        raise ValueError(f"Unknown image quality: {quality}")
    font_root = Path(reportlab.__file__).parent / "fonts"
    font = ImageFont.truetype(str(font_root / "Vera.ttf"), 32)
    title_font = ImageFont.truetype(str(font_root / "VeraBd.ttf"), 38)
    padding = 48
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    entries = [(line, title_font, 60) for line in str(title).splitlines()]
    entries += [("", font, 22)]
    for paragraph in body:
        entries += [(line, font, 48) for line in str(paragraph).splitlines()]
        entries.append(("", font, 18))
    # Keep complete identifiers on one line, including long addresses and names.
    width = max(1600, int(max(measure.textlength(t, font=f) for t, f, _ in entries)) + 2 * padding + 1)
    image = Image.new("RGB", (width, 2 * padding + sum(h for _, _, h in entries)), "white")
    draw = ImageDraw.Draw(image)
    y = padding
    for text, selected_font, height in entries:
        draw.text((padding, y), text, font=selected_font, fill="black", anchor="lt")
        y += height
    if quality == "low_resolution":
        image = image.resize((image.width // 2, image.height // 2), Image.Resampling.LANCZOS)
    return image


def image_payload(title, body, quality="clean"):
    """Return a PNG stream for embedding plus a reproducible rendering recipe."""
    image = render_text_image(title, body, quality)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    recipe = {"renderer": RENDERER_VERSION, "title": title, "body": list(body),
              "quality": quality, "pixel_sha256": pixel_digest(image)}
    return buffer, recipe


def evidence_path(document):
    source = Path(document)
    return source.parent.parent / "evidence" / f"{source.stem}.json"


def save_evidence(document, recipes):
    """Bind rendering recipes to the exact saved source document."""
    source = Path(document)
    destination = evidence_path(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({
        "document_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "images": recipes,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def verified_image_text(document, images):
    """Read ground truth only after both the source bytes and pixels agree."""
    source = Path(document)
    evidence = json.loads(evidence_path(source).read_text(encoding="utf-8"))
    if evidence["document_sha256"] != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError("Rendering evidence does not match the document SHA-256")
    actual = [pixel_digest(image) for image in images]
    recipes = evidence["images"]
    if len(actual) != len(recipes) or not actual:
        raise ValueError("Rendering evidence image count does not match the document")
    text = []
    for recipe in recipes:
        if recipe["renderer"] != RENDERER_VERSION:
            raise ValueError("Unknown rendering evidence version")
        expected = pixel_digest(render_text_image(recipe["title"], recipe["body"], recipe["quality"]))
        if expected != recipe["pixel_sha256"] or expected not in actual:
            raise ValueError("Rendering evidence text does not match the actual image pixels")
        actual.remove(expected)
        text.extend([recipe["title"], *recipe["body"]])
    return "\n".join(text)
