"""Check the contextual corpus generator: determinism, exact offsets, coverage."""

import json
import re
import tempfile
import unittest
from collections import Counter
from itertools import pairwise
from pathlib import Path

from eval import contextual_corpus as cc


class ContextualCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = cc.generate(42)

    def test_same_seed_gives_identical_corpus(self):
        self.assertEqual(self.docs, cc.generate(42))

    def test_other_seed_changes_values(self):
        other = cc.generate(7)
        self.assertNotEqual([d["text"] for d in self.docs], [d["text"] for d in other])

    def test_offsets_are_exact_and_verify_passes(self):
        for doc in self.docs:
            cc.verify(doc)
            for item in doc["labels"] + doc["decoys"]:
                self.assertEqual(doc["text"][item["start"] : item["end"]], item["value"], doc["id"])

    def test_verify_rejects_a_shifted_offset(self):
        doc = json.loads(json.dumps(self.docs[0]))
        doc["labels"][0]["start"] += 1
        doc["labels"][0]["end"] += 1
        with self.assertRaises(ValueError):
            cc.verify(doc)

    def test_verify_rejects_overlap(self):
        doc = json.loads(json.dumps(self.docs[0]))
        first = doc["labels"][0]
        doc["decoys"].append(
            {"value": first["value"], "kind": "role", "start": first["start"], "end": first["end"]}
        )
        with self.assertRaises(ValueError):
            cc.verify(doc)

    def test_labels_and_decoys_never_overlap(self):
        for doc in self.docs:
            spans = sorted((i["start"], i["end"]) for i in doc["labels"] + doc["decoys"])
            for (_, end), (start, _) in pairwise(spans):
                self.assertLessEqual(end, start, doc["id"])

    def test_languages_and_split_sizes(self):
        self.assertEqual(len(self.docs), 24)
        self.assertEqual(len({d["id"] for d in self.docs}), 24)
        counts = Counter((d["language"], d["split"]) for d in self.docs)
        self.assertEqual(
            counts, {("en", "dev"): 3, ("en", "test"): 9, ("fi", "dev"): 3, ("fi", "test"): 9}
        )

    def test_all_categories_present_in_both_languages(self):
        for lang in cc.LANGUAGES:
            found = Counter(
                label["category"]
                for doc in self.docs
                if doc["language"] == lang
                for label in doc["labels"]
            )
            for category in cc.CATEGORIES:
                self.assertGreaterEqual(found[category], 4, f"{lang} {category}")

    def test_per_document_item_counts(self):
        for doc in self.docs:
            by_category = Counter(label["category"] for label in doc["labels"])
            standard = by_category["STANDARD"]
            contextual = sum(v for k, v in by_category.items() if k != "STANDARD")
            self.assertTrue(2 <= standard <= 3, f"{doc['id']} standard={standard}")
            self.assertTrue(3 <= contextual <= 5, f"{doc['id']} contextual={contextual}")
            self.assertTrue(2 <= len(doc["decoys"]) <= 3, f"{doc['id']} decoys")
            self.assertTrue(120 <= len(doc["text"].split()) <= 300, f"{doc['id']} words")

    def test_hidden_items_sit_in_a_notes_or_comment_section(self):
        markers = ("Speaker notes", "Puhujan muistiinpanot", "Comment", "Kommentti", "Note:", "Huomio:")
        for doc in self.docs:
            for label in doc["labels"]:
                if label["category"] == "HIDDEN":
                    before = doc["text"][: label["start"]]
                    self.assertTrue(any(m in before for m in markers), doc["id"])

    def test_no_banned_names(self):
        for doc in self.docs:
            for name in cc.BANNED:
                found = re.search(rf"\b{re.escape(name)}\b", doc["text"], re.IGNORECASE)
                self.assertIsNone(found, f"{doc['id']} contains {name}")

    def test_write_corpus_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "corpus"
            cc.write_corpus(self.docs, out)
            index = json.loads((out / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(len(index), 24)
            for entry in index:
                text = (out / f"{entry['id']}.md").read_text(encoding="utf-8")
                record = json.loads((out / f"{entry['id']}.json").read_text(encoding="utf-8"))
                for item in record["labels"] + record["decoys"]:
                    self.assertEqual(text[item["start"] : item["end"]], item["value"])
            with self.assertRaises(FileExistsError):
                cc.write_corpus(self.docs, out)
            self.assertEqual(cc.main(["--out", str(out)]), 1)


if __name__ == "__main__":
    unittest.main()
