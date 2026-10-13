"""The UI and benchmark select the same detectors without loading model weights."""

import subprocess
import sys
import unittest
from unittest.mock import patch

from detect.methods import METHODS, get_detector
from eval.bench import MODEL_SETS
from eval.run_matrix import METHOD_NAMES, get_method


class MethodTests(unittest.TestCase):
    def setUp(self):
        get_detector.cache_clear()

    def tearDown(self):
        get_detector.cache_clear()

    def test_gliner_uses_its_detector_without_building_presidio(self):
        with patch("detect.gliner_detector.GlinerDetector") as gliner, \
                patch("detect.methods.build_analyzer") as analyzer:
            detector = get_detector("gliner")
            self.assertIs(detector, gliner.return_value)
            self.assertIs(detector, get_detector("gliner"))
            gliner.assert_called_once_with()
            analyzer.assert_not_called()

    def test_presidio_methods_keep_their_model_and_pattern_settings(self):
        for method, model_set, custom in (
            ("basic", "sm", False), ("rules", "sm", True), ("rules-lg", "lg", True),
        ):
            with self.subTest(method=method), \
                    patch("detect.methods.build_analyzer") as analyzer, \
                    patch("detect.methods.PresidioDetector") as presidio:
                detector = get_detector(method)
                self.assertIs(detector, presidio.return_value)
                analyzer.assert_called_once_with(MODEL_SETS[model_set], custom)
                presidio.assert_called_once_with(analyzer.return_value)

    def test_unknown_method_does_not_load_a_detector(self):
        with patch("detect.methods.build_analyzer") as analyzer:
            with self.assertRaisesRegex(KeyError, "Unknown method"):
                get_detector("missing")
            analyzer.assert_not_called()

    def test_benchmark_methods_match_the_ui_registry_without_duplicates(self):
        self.assertEqual(list(METHODS), METHOD_NAMES)
        self.assertEqual(1, METHOD_NAMES.count("gliner"))
        with patch("eval.run_matrix.get_detector") as factory:
            for method in METHOD_NAMES:
                self.assertIs(factory.return_value, get_method(method))
            self.assertEqual(METHOD_NAMES, [call.args[0] for call in factory.call_args_list])

    def test_importing_the_registry_does_not_require_optional_gliner_packages(self):
        script = """
import builtins

original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name.split('.')[0] in {'gliner', 'torch', 'transformers'}:
        raise AssertionError(f'Unexpected optional import: {name}')
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from detect.methods import METHODS
assert 'gliner' in METHODS
"""
        subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
