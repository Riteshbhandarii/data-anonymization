#!/usr/bin/env python3
"""Verify generated labels against document parts and rendered-image evidence.

This validates fixture ground truth, not OCR quality. OCR recall is measured
separately by pipeline.validation using actual extractor output.
"""

import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

if __package__:
    from .image_helpers import verified_image_text
else:
    from image_helpers import verified_image_text

WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
LOCATIONS = {"body", "metadata", "notes", "hidden_sheet", "header", "footer",
             "comment", "tracked_change", "embedded_image"}


def _xml_text(root):
    """Join runs within paragraphs, preserving escaped XML text correctly."""
    paragraphs = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "p"]
    if paragraphs:
        return "\n".join("".join(node.text or "" for node in paragraph.iter()
                                  if node.tag.rsplit("}", 1)[-1] in {"t", "delText"})
                          for paragraph in paragraphs)
    return " ".join(root.itertext())


def _word_location(path, location):
    with zipfile.ZipFile(path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))
        if location == "tracked_change":
            revisions = [element for element in document.iter()
                         if element.tag in {WORD + "ins", WORD + "del"}]
            return "\n".join(f"{element.get(WORD + 'author', '')} {_xml_text(element)}"
                             for element in revisions)
        relationships = ElementTree.fromstring(archive.read("word/_rels/document.xml.rels"))
        parts = {relation.get("Id"): relation for relation in relationships}
        if location in {"header", "footer"}:
            selected = [parts[reference.get(REL + "id")].get("Target")
                        for reference in document.iter(WORD + location + "Reference")]
        else:
            selected = [relation.get("Target") for relation in parts.values()
                        if relation.get("Type", "").endswith("/comments")]
        text = []
        anchored_comments = {reference.get(WORD + "id")
                             for reference in document.iter(WORD + "commentReference")}
        for target in selected:
            name = target.lstrip("/") if target.startswith("/") else "word/" + target
            part = ElementTree.fromstring(archive.read(name))
            if location == "comment":
                text += [f"{comment.get(WORD + 'author', '')} {_xml_text(comment)}"
                         for comment in part.iter(WORD + "comment")
                         if comment.get(WORD + "id") in anchored_comments]
            else:
                text.append(_xml_text(part))
        return "\n".join(text)


def text_at(path, location):
    """Read the labelled location without calling the pipeline's extractors."""
    source = Path(path)
    ext = source.suffix.lower()
    if location not in LOCATIONS:
        raise ValueError(f"Unknown label location: {location}")
    if ext == ".png" and location == "body":
        from PIL import Image
        with Image.open(source) as image:
            return verified_image_text(source, [image])
    if location == "embedded_image":
        from PIL import Image
        images = []
        if ext == ".pptx":
            from pptx import Presentation
            for slide in Presentation(source).slides:
                for shape in slide.shapes:
                    if hasattr(shape, "image"):
                        with Image.open(io.BytesIO(shape.image.blob)) as image:
                            images.append(image.copy())
        elif ext == ".pdf":
            from pypdf import PdfReader
            images = [image.image for page in PdfReader(source).pages for image in page.images]
        else:
            raise ValueError(f"Embedded-image evidence is not supported for {ext}")
        return verified_image_text(source, images)
    if location in {"header", "footer", "comment", "tracked_change"}:
        if ext != ".docx":
            raise ValueError(f"Location {location} requires a DOCX file")
        return _word_location(source, location)
    if location == "metadata":
        if ext == ".pdf":
            from pypdf import PdfReader
            return " ".join(str(value) for value in (PdfReader(source).metadata or {}).values())
        with zipfile.ZipFile(source) as archive:
            return " ".join(_xml_text(ElementTree.fromstring(archive.read(name)))
                            for name in archive.namelist()
                            if name.startswith("docProps/") and name.endswith(".xml"))
    if location == "notes":
        with zipfile.ZipFile(source) as archive:
            return "\n".join(_xml_text(ElementTree.fromstring(archive.read(name)))
                             for name in archive.namelist()
                             if name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml"))
    if location == "hidden_sheet" or ext == ".xlsx":
        import openpyxl
        workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
        try:
            hidden = location == "hidden_sheet"
            return " ".join(str(cell) for sheet in workbook.worksheets
                            if (sheet.sheet_state != "visible") == hidden
                            for row in sheet.iter_rows(values_only=True) for cell in row if cell is not None)
        finally:
            workbook.close()
    if location != "body":
        raise ValueError(f"Location {location} is not supported for {ext}")
    if ext == ".docx":
        import docx
        return "\n".join(paragraph.text for paragraph in docx.Document(source).paragraphs)
    if ext == ".pptx":
        from pptx import Presentation
        return "\n".join(shape.text_frame.text for slide in Presentation(source).slides
                         for shape in slide.shapes if shape.has_text_frame)
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(source).pages)
    if ext in {".txt", ".md", ".csv"}:
        return source.read_text(encoding="utf-8")
    raise ValueError(f"Unsupported document type: {ext}")


def manifest_documents(root):
    """Read only manifest entries and validate labels, counts and fingerprint."""
    root = Path(root).resolve()
    with (root / "index.csv").open(encoding="utf-8", newline="") as stream:
        entries = list(csv.DictReader(stream))
    if not entries:
        raise ValueError("Corpus manifest has no documents")
    documents, seen, digest = [], set(), hashlib.sha256()
    for entry in entries:
        source = (root / entry["file"]).resolve()
        if not source.is_relative_to(root) or source in seen:
            raise ValueError(f"Invalid or duplicate manifest path: {entry['file']}")
        seen.add(source)
        raw_labels = (root / "labels" / f"{source.stem}.json").read_bytes()
        payload = json.loads(raw_labels)
        entities = payload["entities"]
        if payload["file"] != entry["file"] or payload["format"] != entry["format"]:
            raise ValueError(f"Labels do not match manifest: {entry['file']}")
        if (payload["language"] != entry["language"]
                or payload.get("quality", "standard") != entry.get("quality", "standard")):
            raise ValueError(f"Label language or quality does not match manifest: {entry['file']}")
        if not entities or len(entities) != int(entry["entities"]):
            raise ValueError(f"Missing or inconsistent labels: {entry['file']}")
        if sum(entity["location"] != "body" for entity in entities) != int(entry["hidden"]):
            raise ValueError(f"Location counts do not match manifest: {entry['file']}")
        for entity in entities:
            if entity["location"] not in LOCATIONS or not isinstance(entity["value"], str) or not entity["value"]:
                raise ValueError(f"Invalid label: {entry['file']}")
        digest.update(raw_labels)
        digest.update((root / "text" / f"{source.stem}.txt").read_bytes())
        documents.append(payload)
    provenance = json.loads((root / "corpus.json").read_text(encoding="utf-8"))
    if provenance["documents"] != len(documents):
        raise ValueError("Manifest document count does not match corpus.json")
    if provenance["identifiers"] != sum(len(document["entities"]) for document in documents):
        raise ValueError("Manifest label count does not match corpus.json")
    if provenance["corpus_sha256"] != digest.hexdigest():
        raise ValueError("Labels or saved text do not match the corpus fingerprint")
    return documents


def verify_corpus(root):
    """Return checked-label count, document count and all validation failures."""
    documents = manifest_documents(root)
    checked, bad = 0, []
    for document in documents:
        path = Path(root) / document["file"]
        cache = {}
        for entity in document["entities"]:
            checked += 1
            location = entity["location"]
            if location not in cache:
                try:
                    cache[location] = text_at(path, location)
                except Exception as error:  # noqa: BLE001 - malformed files must fail verification.
                    cache[location] = None
                    bad.append(f"{document['file']} ({location}): {type(error).__name__}: {error}")
            if cache[location] is not None and entity["value"] not in cache[location]:
                bad.append(f"{document['file']}: {entity['type']} not found in {location}: {entity['value'][:40]}")
    return checked, len(documents), bad


def main(root):
    try:
        checked, documents, bad = verify_corpus(root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Corpus verification failed: {error}", file=sys.stderr)
        return 1
    print(f"checked {checked} labels across {documents} documents")
    if bad:
        print(f"\n{len(bad)} mismatches:")
        for message in bad[:20]:
            print(f"  {message}")
        return 1
    print("every labelled value is where its label says")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "./corpus-out"))
