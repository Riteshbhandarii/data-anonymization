"""Reject stale utility caches before sending any model prompt."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from eval.prepare_utility_rerun import check_suite


class UtilitySuiteCacheTests(unittest.TestCase):
    def test_changed_suite_or_document_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "memo.md"
            source.write_text("Fictional memo")
            suite = root / "suite.json"
            suite.write_text(json.dumps({"documents": [{"id": "a1", "file": "memo.md"}]}))
            expected = {"suite_sha256": hashlib.sha256(suite.read_bytes()).hexdigest(),
                        "document_sha256": {"a1": hashlib.sha256(source.read_bytes()).hexdigest()}}
            check_suite(suite, expected)
            source.write_text("Changed memo")
            with self.assertRaises(ValueError):
                check_suite(suite, expected)
            suite.write_text("Changed suite")
            with self.assertRaises(ValueError):
                check_suite(suite, expected)


if __name__ == "__main__":
    unittest.main()
