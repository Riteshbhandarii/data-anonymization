"""Check synthetic document locations and image evidence without grading OCR."""

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageChops

from corpus.image_helpers import evidence_path, render_text_image
from corpus.verify import manifest_documents, text_at, verify_corpus

REPOSITORY = Path(__file__).resolve().parents[1]


class CorpusLocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.generated.cleanup)
        cls.fixture = Path(cls.generated.name) / "corpus"
        cls.generate(cls.fixture)

    @staticmethod
    def generate(destination):
        result = subprocess.run(
            [sys.executable, str(REPOSITORY / "corpus" / "generate.py"),
             "--out", str(destination), "--n", "1", "--seed", "42"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise AssertionError(result.stderr)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "corpus"
        shutil.copytree(self.fixture, self.root)

    def labels(self, stem):
        return json.loads((self.root / "labels" / f"{stem}.json").read_text(encoding="utf-8"))

    def rewrite_zip(self, source, replacements):
        with zipfile.ZipFile(source) as archive:
            content = {name: archive.read(name) for name in archive.namelist()}
        content.update(replacements)
        with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in content.items():
                archive.writestr(name, data)

    def test_generated_locations_and_quality_variants_verify(self):
        checked, count, failures = verify_corpus(self.root)
        self.assertEqual([], failures)
        self.assertEqual(14, count)
        self.assertGreater(checked, 150)
        documents = manifest_documents(self.root)
        self.assertEqual({"body", "metadata", "notes", "hidden_sheet", "header", "footer",
                          "comment", "tracked_change", "embedded_image"},
                         {entity["location"] for document in documents for entity in document["entities"]})
        for language in ("en", "fi"):
            clean = self.labels(f"{language}_png_00_clean")
            degraded = self.labels(f"{language}_png_00_low_resolution")
            self.assertEqual(clean["entities"], degraded["entities"])
            with Image.open(self.root / clean["file"]) as high, Image.open(self.root / degraded["file"]) as low:
                self.assertEqual(high.width // 2, low.width)
                self.assertEqual(high.height // 2, low.height)
            document = self.labels(f"{language}_docx_00")
            body = text_at(self.root / document["file"], "body")
            for entity in document["entities"]:
                if entity["location"] in {"header", "footer", "comment", "tracked_change"}:
                    self.assertNotIn(entity["value"], body)

    def test_same_seed_preserves_labels_saved_text_and_fingerprint(self):
        second = Path(self.temporary.name) / "second"
        self.generate(second)
        for folder in ("labels", "text"):
            for source in (self.root / folder).iterdir():
                self.assertEqual(source.read_bytes(), (second / folder / source.name).read_bytes())
        self.assertEqual((self.root / "corpus.json").read_bytes(), (second / "corpus.json").read_bytes())

    def test_stale_files_outside_manifest_are_not_verified(self):
        (self.root / "labels" / "obsolete.json").write_text("invalid stale JSON", encoding="utf-8")
        checked, count, failures = verify_corpus(self.root)
        self.assertEqual(14, count)
        self.assertGreater(checked, 0)
        self.assertEqual([], failures)

    def test_missing_labels_make_command_fail(self):
        (self.root / "labels" / "en_docx_00.json").unlink()
        result = subprocess.run(
            [sys.executable, str(REPOSITORY / "corpus" / "verify.py"), str(self.root)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("Corpus verification failed", result.stderr)

    def test_removed_word_locations_are_reported(self):
        source = self.root / "docx" / "en_docx_00.docx"
        document = self.labels("en_docx_00")
        with zipfile.ZipFile(source) as archive:
            replacements = {}
            for location, part in (("header", "word/header1.xml"), ("footer", "word/footer1.xml"),
                                   ("comment", "word/comments.xml"), ("tracked_change", "word/document.xml")):
                data = archive.read(part)
                for entity in document["entities"]:
                    if entity["location"] == location:
                        data = data.replace(entity["value"].encode("utf-8"), b"REMOVED")
                replacements[part] = data
        self.rewrite_zip(source, replacements)
        _, _, failures = verify_corpus(self.root)
        for location in ("header", "footer", "comment", "tracked_change"):
            self.assertTrue(any(f"not found in {location}:" in failure for failure in failures), failures)

    def test_image_evidence_rejects_modified_text_recipe(self):
        source = self.root / "png" / "en_png_00_clean.png"
        sidecar = evidence_path(source)
        evidence = json.loads(sidecar.read_text(encoding="utf-8"))
        evidence["images"][0]["body"] = ["This text was never rendered into the image."]
        sidecar.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "actual image pixels"):
            text_at(source, "body")

    def test_image_evidence_rejects_corrupted_source_bytes(self):
        source = self.root / "png" / "en_png_00_clean.png"
        with Image.open(source) as image:
            altered = image.copy()
        altered.putpixel((0, 0), (0, 0, 0))
        altered.save(source)
        with self.assertRaisesRegex(ValueError, "document SHA-256"):
            text_at(source, "body")

    def test_embedded_image_pixels_are_checked_even_if_document_hash_is_updated(self):
        source = self.root / "pptx" / "en_pptx_00.pptx"
        with zipfile.ZipFile(source) as archive:
            name = next(name for name in archive.namelist() if name.startswith("ppt/media/"))
            with Image.open(io.BytesIO(archive.read(name))) as original:
                blank = Image.new("RGB", original.size, "white")
        buffer = io.BytesIO()
        blank.save(buffer, format="PNG")
        self.rewrite_zip(source, {name: buffer.getvalue()})
        sidecar = evidence_path(source)
        evidence = json.loads(sidecar.read_text(encoding="utf-8"))
        evidence["document_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        sidecar.write_text(json.dumps(evidence), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "actual image pixels"):
            text_at(source, "embedded_image")

    def test_long_text_and_finnish_characters_have_canvas_margins(self):
        for quality in ("clean", "low_resolution"):
            image = render_text_image("Ääkköset: pitkä otsikko " * 8,
                                      ["Yhteystiedot: Väinö Mäkinen", "identifier_" * 100], quality)
            ink = ImageChops.difference(image, Image.new("RGB", image.size, "white")).getbbox()
            self.assertIsNotNone(ink)
            left, top, right, bottom = ink
            self.assertGreater(left, 0)
            self.assertGreater(top, 0)
            self.assertLess(right, image.width)
            self.assertLess(bottom, image.height)


if __name__ == "__main__":
    unittest.main()
