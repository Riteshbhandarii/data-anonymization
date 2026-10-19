"""Frozen base spans must reject changed provenance before LLM inference."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from detect.local_llm import FinalPassDetector
from eval.local_base_cache import CachedDetector, source_digest, text_key


class BaseCacheTests(unittest.TestCase):
    def test_replay_preserves_masking_and_rejects_changed_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "labels").mkdir()
            (root / "text").mkdir()
            (root / "index.csv").write_text("file\na.md\n")
            label = '{"language": "fi", "entities": []}'
            text = "Aino\njob Tampere"
            (root / "labels/a.json").write_text(label)
            (root / "text/a.txt").write_text(text)
            digest = hashlib.sha256(label.encode() + text.encode()).hexdigest()
            cache = {"method": "combined", "corpus_sha256": digest,
                     "detector_source_sha256": source_digest(), "spans": {
                         text_key(text, "fi"): [{"start": 0, "end": 4,
                                                "entity_type": "PERSON", "score": 0.9}]}}
            path = root / "cache.json"
            path.write_text(json.dumps(cache))
            base = CachedDetector(path, root, "combined")
            seen = []
            final = SimpleNamespace(detect=lambda value, lang: seen.append((value, lang)) or [])
            spans = FinalPassDetector(base, final).detect(text, "fi")
            self.assertEqual([("████\njob Tampere", "fi")], seen)
            self.assertEqual((0, 4, "PERSON"), (spans[0].start, spans[0].end, spans[0].entity_type))
            with self.assertRaises(ValueError):
                CachedDetector(path, root, "rules")
            with patch("eval.local_base_cache.source_digest", return_value="changed"), self.assertRaises(ValueError):
                CachedDetector(path, root, "combined")
            (root / "text/a.txt").write_text("changed")
            with self.assertRaises(ValueError):
                CachedDetector(path, root, "combined")
            with self.assertRaises(KeyError):
                base.detect(text, "en")


if __name__ == "__main__":
    unittest.main()
