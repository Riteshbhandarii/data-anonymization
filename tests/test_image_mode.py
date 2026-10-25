"""Check screenshot review and downloads without loading detector models."""

import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image, PngImagePlugin
from streamlit.testing.v1 import AppTest

from app import image_mode
from redact.image import Word

WORDS = [
    Word("Alice", 10, 10, 30, 12, (1, 1, 1)),
    Word("Example", 45, 10, 45, 12, (1, 1, 1)),
    Word("Public", 10, 35, 40, 12, (1, 1, 2)),
]


class FixtureDetector:
    def detect(self, text, language="en"):
        start = text.index("Alice")
        return [SimpleNamespace(start=start, end=start + 5,
                                entity_type="PERSON", score=1.0)]


class ImageModeHelpersTests(unittest.TestCase):
    def image(self):
        return Image.new("RGB", (120, 60), "white")

    def test_load_composites_transparency_and_discards_source_metadata(self):
        source = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        source.putpixel((1, 0), (255, 0, 0, 255))
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Author", "Synthetic private author")
        buffer = io.BytesIO()
        source.save(buffer, format="PNG", pnginfo=metadata)

        image = image_mode.load_image(buffer.getvalue())

        self.assertEqual("RGB", image.mode)
        self.assertEqual((255, 255, 255), image.getpixel((0, 0)))
        self.assertEqual((255, 0, 0), image.getpixel((1, 0)))
        self.assertEqual({}, image.info)
        self.assertEqual({}, dict(image.getexif()))

    def test_load_applies_exif_orientation_before_ocr(self):
        source = Image.new("RGB", (2, 3), "white")
        exif = Image.Exif()
        exif[274] = 6
        buffer = io.BytesIO()
        source.save(buffer, format="JPEG", exif=exif)

        image = image_mode.load_image(buffer.getvalue())

        self.assertEqual((3, 2), image.size)
        self.assertEqual({}, image.info)
        self.assertEqual({}, dict(image.getexif()))

    def test_load_rejects_multiple_frames_instead_of_exporting_only_the_first(self):
        first = self.image()
        second = Image.new("RGB", first.size, "red")
        buffer = io.BytesIO()
        first.save(buffer, format="GIF", save_all=True, append_images=[second])
        with self.assertRaises(ValueError):
            image_mode.load_image(buffer.getvalue())

    def test_png_download_preserves_pixels_without_source_metadata(self):
        source = self.image()
        source.putpixel((5, 5), (0, 0, 0))
        source.info["Author"] = "Synthetic private author"
        with Image.open(io.BytesIO(image_mode.png_bytes(source))) as output:
            self.assertEqual("PNG", output.format)
            self.assertEqual(source.size, output.size)
            self.assertEqual(source.tobytes(), output.tobytes())
            self.assertEqual({}, output.info)

    def test_analysis_selects_detected_words_and_passes_ocr_scale(self):
        image = self.image()
        with patch.object(image_mode, "ocr_words", return_value=WORDS) as ocr:
            result = image_mode.analyze_image(image, FixtureDetector(), ocr_scale=2)
        self.assertEqual(WORDS, result["words"])
        self.assertEqual([0], result["automatic"])
        self.assertEqual([0], result["selected"])
        self.assertEqual(2, ocr.call_args.kwargs["scale"])
        self.assertEqual((255, 255, 255), image.getpixel((15, 15)))

    def test_whole_lines_selects_neighboring_words_but_not_another_line(self):
        with patch.object(image_mode, "ocr_words", return_value=WORDS):
            result = image_mode.analyze_image(self.image(), FixtureDetector(), whole_lines=True)
        self.assertEqual([0, 1], result["automatic"])
        self.assertEqual([0, 1], result["selected"])

    def test_empty_ocr_result_has_no_automatic_masks(self):
        detector = SimpleNamespace(detect=lambda text, language: [])
        with patch.object(image_mode, "ocr_words", return_value=[]):
            result = image_mode.analyze_image(self.image(), detector)
        self.assertEqual([], result["words"])
        self.assertEqual([], result["automatic"])
        self.assertEqual([], result["selected"])

    def test_manual_selection_sorts_and_deduplicates_without_mutating_input(self):
        selected = [2, 0, 2]
        self.assertEqual([0, 2], image_mode.validate_selection(selected, len(WORDS)))
        self.assertEqual([], image_mode.validate_selection([], len(WORDS)))
        self.assertEqual([2, 0, 2], selected)

    def test_manual_selection_rejects_out_of_range_and_non_integer_indices(self):
        for index in (-1, len(WORDS), "1", True, False, 1.5, None):
            with self.subTest(index=index), self.assertRaises(ValueError):
                image_mode.validate_selection([0, index], len(WORDS))

    def test_manual_selection_requires_a_list(self):
        for selected in (None, True, 0, "0", (0,), {0}, {"selected": [0]}):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                image_mode.validate_selection(selected, len(WORDS))


class ImageModeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.editor = patch.object(image_mode, "_word_editor", return_value=None)
        self.editor_mock = self.editor.start()
        self.addCleanup(self.editor.stop)
        self.ocr = patch.object(image_mode, "ocr_words", return_value=WORDS)
        self.ocr_mock = self.ocr.start()
        self.addCleanup(self.ocr.stop)
        self.download = patch("streamlit.download_button", return_value=False)
        self.download_mock = self.download.start()
        self.addCleanup(self.download.stop)
        self.app = AppTest.from_string('''
from types import SimpleNamespace
from app.image_mode import render_image_mode
def detect(text, language="en"):
    start = text.index("Alice")
    return [SimpleNamespace(start=start, end=start + 5, entity_type="PERSON", score=1.0)]
render_image_mode(lambda: {}, lambda method: SimpleNamespace(detect=detect))
''', default_timeout=30)
        source = Image.new("RGB", (120, 60), "white")
        self.input_bytes = image_mode.png_bytes(source)

    def button(self, label):
        return next(button for button in self.app.button if button.label == label)

    def run_image(self):
        self.app.run()
        self.app.file_uploader[0].set_value(
            ("Synthetic_Alice.png", self.input_bytes, "image/png")
        ).run()
        self.button("Run image").click().run()
        self.assertEqual([], list(self.app.exception))

    def downloaded_image(self):
        call = self.download_mock.call_args
        self.assertEqual("anonymized.png", call.kwargs["file_name"])
        self.assertEqual("image/png", call.kwargs["mime"])
        return Image.open(io.BytesIO(call.args[1]))

    def test_uploaded_image_download_contains_only_selected_masks(self):
        self.run_image()
        self.assertEqual([0], self.app.session_state["image_result"]["selected"])
        with self.downloaded_image() as output:
            self.assertEqual((0, 0, 0), output.getpixel((20, 16)))
            self.assertEqual((255, 255, 255), output.getpixel((55, 16)))
            self.assertEqual({}, output.info)

    def test_crop_change_hides_download_until_rerun_then_removes_top_pixels(self):
        self.run_image()
        self.download_mock.reset_mock()
        self.app.slider[0].set_value(10).run()
        self.assertEqual([], list(self.app.exception))
        self.download_mock.assert_not_called()
        self.assertTrue(any("settings changed" in item.value for item in self.app.info))
        self.button("Run image").click().run()
        self.assertEqual([], list(self.app.exception))
        self.assertEqual((120, 50), self.ocr_mock.call_args.args[0].size)
        with self.downloaded_image() as output:
            self.assertEqual((120, 50), output.size)

    def test_replacement_upload_hides_previous_image_download(self):
        self.run_image()
        self.download_mock.reset_mock()
        replacement = image_mode.png_bytes(Image.new("RGB", (120, 60), "red"))
        self.app.file_uploader[0].set_value(
            ("Synthetic_Alice.png", replacement, "image/png")
        ).run()
        self.assertEqual([], list(self.app.exception))
        self.download_mock.assert_not_called()
        self.assertTrue(any("settings changed" in item.value for item in self.app.info))

    def test_failed_ocr_clears_previous_result_and_does_not_download_input(self):
        self.run_image()
        self.download_mock.reset_mock()
        self.ocr_mock.side_effect = RuntimeError("Synthetic OCR failure")
        self.button("Run image").click().run()
        self.assertEqual([], list(self.app.exception))
        self.assertNotIn("image_result", self.app.session_state)
        self.download_mock.assert_not_called()
        self.assertTrue(any("Synthetic OCR failure" in item.value for item in self.app.error))

    def test_click_selection_is_applied_once_and_restore_and_mask_all_work(self):
        self.run_image()
        result = self.app.session_state["image_result"]
        event = {"selected": [0, 1], "revision": result["revision"], "nonce": "first-click"}
        self.editor_mock.return_value = event
        self.app.run()
        self.assertEqual([], list(self.app.exception))
        self.assertEqual([0, 1], self.app.session_state["image_result"]["selected"])
        self.app.run()
        self.assertEqual([0, 1], self.app.session_state["image_result"]["selected"])
        self.button("Restore automatic masks").click().run()
        self.assertEqual([0], self.app.session_state["image_result"]["selected"])
        self.button("Mask all words").click().run()
        self.assertEqual([0, 1, 2], self.app.session_state["image_result"]["selected"])
        self.assertEqual([], list(self.app.exception))

    def test_coalesced_clicks_apply_the_last_complete_selection(self):
        self.run_image()
        revision = self.app.session_state["image_result"]["revision"]
        # The browser masks words 1 and 2 quickly; only the last event arrives.
        self.editor_mock.return_value = {
            "selected": [0, 1, 2], "revision": revision, "nonce": "last-mask-click",
        }
        self.app.run()
        self.assertEqual([0, 1, 2], self.app.session_state["image_result"]["selected"])
        # Likewise, two rapid unmask clicks remove 0 and 1 in the final snapshot.
        self.editor_mock.return_value = {
            "selected": [2], "revision": revision, "nonce": "last-unmask-click",
        }
        self.app.run()
        self.assertEqual([], list(self.app.exception))
        self.assertEqual([2], self.app.session_state["image_result"]["selected"])
        with self.downloaded_image() as output:
            self.assertEqual((255, 255, 255), output.getpixel((20, 16)))
            self.assertEqual((255, 255, 255), output.getpixel((55, 16)))
            self.assertEqual((0, 0, 0), output.getpixel((20, 40)))

    def test_invalid_selection_does_not_replace_valid_masks(self):
        self.run_image()
        revision = self.app.session_state["image_result"]["revision"]
        self.editor_mock.return_value = {
            "selected": [False], "revision": revision, "nonce": "invalid-click",
        }
        self.app.run()
        self.assertEqual([], list(self.app.exception))
        self.assertEqual([0], self.app.session_state["image_result"]["selected"])
        self.assertTrue(any("selection" in item.value for item in self.app.error))

    def test_stale_editor_event_cannot_modify_a_new_run(self):
        self.run_image()
        old_result = self.app.session_state["image_result"]
        self.editor_mock.return_value = {
            "selected": [0, 1], "revision": old_result["revision"], "nonce": "stale-click",
        }
        self.button("Run image").click().run()
        self.assertEqual([], list(self.app.exception))
        self.assertEqual([0], self.app.session_state["image_result"]["selected"])
        self.assertNotEqual(old_result["revision"], self.app.session_state["image_result"]["revision"])


if __name__ == "__main__":
    unittest.main()
