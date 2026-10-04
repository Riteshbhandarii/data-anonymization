"""Tests for the scoring logic in eval/bench.py.

Every number the project reports comes from found() and the counting loop in
main(), so each rule that review once had to catch by hand is pinned here.
Nothing loads a spaCy model: detections are tiny fake result objects.
"""

import csv
import hashlib
import importlib.util
import json
import pathlib
from types import SimpleNamespace

import pytest

BENCH = pathlib.Path(__file__).resolve().parent.parent.parent / "eval" / "bench.py"
spec = importlib.util.spec_from_file_location("bench", BENCH)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def span(start, end, entity_type="X"):
    return SimpleNamespace(start=start, end=end, entity_type=entity_type)


def whole(text, value, n=0):
    """A span holding exactly the n-th occurrence of value in text."""
    start = -1
    for _ in range(n + 1):
        start = text.find(value, start + 1)
    return span(start, start + len(value))


# found() -------------------------------------------------------------------

def test_found_nothing_detected():
    assert bench.found("Call 0401234567 now", "0401234567", []) == ""


def test_found_whole_span_is_covered():
    text = "Call 0401234567 now"
    assert bench.found(text, "0401234567", [whole(text, "0401234567")]) == "covered"


def test_found_span_larger_than_value_is_covered():
    text = "Call 0401234567 now"
    assert bench.found(text, "0401234567", [span(0, len(text))]) == "covered"


def test_found_span_inside_value_is_partial():
    # Presidio returns the city out of a street address.
    text = "Address: 12 Main Street, Springfield"
    value = "12 Main Street, Springfield"
    city = whole(text, "Springfield")
    assert bench.found(text, value, [city]) == "partial"


def test_found_span_overlapping_one_edge_is_partial():
    text = "Mail anna.virtanen@example.com today"
    value = "anna.virtanen@example.com"
    start = text.find(value)
    assert bench.found(text, value, [span(start, start + 5)]) == "partial"
    assert bench.found(text, value, [span(start - 4, start + 6)]) == "partial"


def test_found_span_elsewhere_is_nothing():
    text = "Anna Virtanen wrote to Acme Oy"
    assert bench.found(text, "Acme Oy", [span(0, 5)]) == ""


def test_found_adjacent_span_is_not_overlap():
    text = "abcdef"
    assert bench.found(text, "def", [span(0, 3)]) == ""


def test_found_value_missing_from_text_is_nothing():
    assert bench.found("nothing here", "Acme Oy", [span(0, 12)]) == ""


def test_found_second_occurrence_only_is_not_covered():
    text = "Acme Oy in row one. Acme Oy in row two."
    second = whole(text, "Acme Oy", 1)
    # The first copy still reads in full, so the label is not covered.
    assert bench.found(text, "Acme Oy", [second]) == "partial"


def test_found_first_occurrence_only_is_not_covered():
    text = "Acme Oy in row one. Acme Oy in row two."
    assert bench.found(text, "Acme Oy", [whole(text, "Acme Oy", 0)]) == "partial"


def test_found_both_occurrences_is_covered():
    text = "Acme Oy in row one. Acme Oy in row two."
    results = [whole(text, "Acme Oy", 0), whole(text, "Acme Oy", 1)]
    assert bench.found(text, "Acme Oy", results) == "covered"


def test_found_one_whole_one_partial_is_partial():
    text = "Acme Oy in row one. Acme Oy in row two."
    second = whole(text, "Acme Oy", 1)
    results = [whole(text, "Acme Oy", 0), span(second.start, second.start + 4)]
    assert bench.found(text, "Acme Oy", results) == "partial"


def test_found_overlapping_occurrences_are_all_checked():
    # "aa" occurs at 0 and 1 in "aaa"; covering only the first leaves the second.
    assert bench.found("aaa", "aa", [span(0, 2)]) == "partial"
    assert bench.found("aaa", "aa", [span(0, 3)]) == "covered"


# verdict() -----------------------------------------------------------------

@pytest.mark.parametrize("entity_type, planted, covered, partial, expected", [
    ("PERSON", 0, 0, 0, "not in corpus"),
    ("PERSON", 10, 0, 4, "partial only"),
    ("PLATE", 10, 0, 0, "no recognizer"),
    ("PERSONAL_ID", 10, 0, 0, "recognizer rejects all"),
    ("PERSON", 100, 95, 0, "good"),
    ("PERSON", 100, 100, 0, "good"),
    ("PERSON", 100, 94, 3, "weak"),
    ("PERSON", 100, 1, 0, "weak"),
])
def test_verdict(entity_type, planted, covered, partial, expected):
    assert bench.verdict(entity_type, planted, covered, partial) == expected


def test_verdict_partial_only_wins_over_missing_recognizer():
    # Something was detected, so the type is not unconfigured.
    assert bench.verdict("PLATE", 10, 0, 2) == "partial only"


# manifest() and fingerprint() ----------------------------------------------

def make_corpus(root, docs, n=None):
    """Write docs = {stem: (entities, text)} the way corpus/generate.py does."""
    for sub in ("labels", "text"):
        (root / sub).mkdir(exist_ok=True)
    rows = []
    digest = hashlib.sha256()
    for stem, (entities, text) in docs.items():
        lang, fmt = stem.split("_")[:2]
        label = {"file": f"{fmt}/{stem}.{fmt}", "language": lang, "format": fmt,
                 "entities": entities}
        (root / "labels" / f"{stem}.json").write_text(json.dumps(label), encoding="utf-8")
        (root / "text" / f"{stem}.txt").write_text(text, encoding="utf-8")
        rows.append({"file": label["file"], "language": lang, "format": fmt,
                     "entities": len(entities), "hidden": 0})
        digest.update((root / "labels" / f"{stem}.json").read_bytes())
        digest.update((root / "text" / f"{stem}.txt").read_bytes())
    with open(root / "index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "language", "format", "entities", "hidden"])
        w.writeheader()
        w.writerows(rows)
    (root / "corpus.json").write_text(json.dumps(
        {"seed": 1, "n": n or len(docs), "documents": len(docs),
         "identifiers": 0, "faker": "x", "corpus_sha256": digest.hexdigest()}),
        encoding="utf-8")


def label(type_, value, location="body"):
    return {"type": type_, "value": value, "location": location}


def test_manifest_follows_index_order(tmp_path):
    make_corpus(tmp_path, {"en_csv_01": ([], "b"), "en_csv_00": ([], "a")})
    assert bench.manifest(str(tmp_path)) == ["en_csv_01", "en_csv_00"]


def test_fingerprint_changes_when_text_or_labels_change(tmp_path):
    make_corpus(tmp_path, {"en_csv_00": ([label("PERSON", "Anna")], "Anna")})
    before = bench.fingerprint(str(tmp_path), ["en_csv_00"])
    (tmp_path / "text" / "en_csv_00.txt").write_text("Anna!", encoding="utf-8")
    after_text = bench.fingerprint(str(tmp_path), ["en_csv_00"])
    assert after_text != before
    (tmp_path / "labels" / "en_csv_00.json").write_text("{}", encoding="utf-8")
    assert bench.fingerprint(str(tmp_path), ["en_csv_00"]) != after_text


def test_fingerprint_matches_generator_recipe(tmp_path):
    # The digest in corpus.json is labels then text per stem, in manifest order.
    make_corpus(tmp_path, {"en_csv_00": ([label("PERSON", "Anna")], "Anna"),
                           "fi_csv_00": ([], "Maija")})
    stems = bench.manifest(str(tmp_path))
    expected = json.loads((tmp_path / "corpus.json").read_text())["corpus_sha256"]
    assert bench.fingerprint(str(tmp_path), stems) == expected


# main() with a stub analyzer -------------------------------------------------

class StubAnalyzer:
    """Detects every listed (value, bench entity name) wherever it appears whole."""

    def __init__(self, detect=()):
        self.detect = detect

    def analyze(self, text, language, score_threshold):
        out = []
        for value, entity in self.detect:
            start = text.find(value)
            if start >= 0:
                out.append(span(start, start + len(value), entity))
        return out


@pytest.fixture
def run(monkeypatch):
    """Run main() and return (counts, misses) instead of writing a report."""
    def go(root, detect=()):
        got = {}
        monkeypatch.setattr(bench, "build_analyzer", lambda: StubAnalyzer(detect))
        monkeypatch.setattr(bench, "report",
                            lambda counts, misses, corpus, baseline:
                            got.update(counts=dict(counts), misses=misses))
        bench.main(str(root))
        return got
    return go


def test_metadata_label_is_not_counted_even_if_value_is_in_body(tmp_path, run):
    text = "Memo by Anna Virtanen."
    make_corpus(tmp_path, {"en_docx_00": (
        [label("PERSON", "Anna Virtanen", "metadata")], text)})
    got = run(tmp_path, detect=[("Anna Virtanen", "PERSON")])
    assert got["counts"] == {}
    assert got["misses"] == []


def test_only_body_labels_are_counted_when_mixed(tmp_path, run):
    text = "Memo by Anna Virtanen, mail anna@example.com."
    make_corpus(tmp_path, {"en_docx_00": (
        [label("PERSON", "Anna Virtanen", "metadata"),
         label("EMAIL", "anna@example.com")], text)})
    got = run(tmp_path, detect=[("anna@example.com", "EMAIL_ADDRESS")])
    assert got["counts"] == {("en", "docx", "EMAIL"): [1, 1, 0]}


def test_counting_loop_covered_partial_and_miss(tmp_path, run):
    text = "Anna Virtanen, 12 Main Street, Springfield, Acme Oy and Acme Oy"
    make_corpus(tmp_path, {"en_csv_00": ([
        label("PERSON", "Anna Virtanen"),
        label("ADDRESS", "12 Main Street, Springfield"),
        label("COMPANY", "Acme Oy"),
        label("PLATE", "ABC-123")], text)})
    got = run(tmp_path, detect=[("Anna Virtanen", "PERSON"),
                                ("Springfield", "LOCATION")])
    c = got["counts"]
    assert c[("en", "csv", "PERSON")] == [1, 1, 0]
    assert c[("en", "csv", "ADDRESS")] == [1, 0, 1]
    assert c[("en", "csv", "COMPANY")] == [1, 0, 0]
    assert {m["type"]: m["detected"] for m in got["misses"]} == {
        "ADDRESS": "partial", "COMPANY": "nothing", "PLATE": "nothing"}


def test_detection_of_the_wrong_type_does_not_count(tmp_path, run):
    text = "Contact Anna Virtanen"
    make_corpus(tmp_path, {"en_csv_00": ([label("PERSON", "Anna Virtanen")], text)})
    got = run(tmp_path, detect=[("Anna Virtanen", "ORGANIZATION")])
    assert got["counts"][("en", "csv", "PERSON")] == [1, 0, 0]


def test_leftover_documents_from_a_larger_run_are_not_scored(tmp_path, run):
    docs = {f"en_csv_{i:02d}": ([label("PERSON", f"Person{i}")], f"Person{i}")
            for i in range(3)}
    make_corpus(tmp_path, docs)
    # Regenerate smaller into the same directory: the old files stay on disk.
    make_corpus(tmp_path, {"en_csv_00": docs["en_csv_00"]})
    assert (tmp_path / "labels" / "en_csv_02.json").exists()
    got = run(tmp_path, detect=[(f"Person{i}", "PERSON") for i in range(3)])
    assert got["counts"] == {("en", "csv", "PERSON"): [1, 1, 0]}


def test_edited_corpus_file_stops_the_run(tmp_path, run):
    make_corpus(tmp_path, {"en_csv_00": ([label("PERSON", "Anna")], "Anna")})
    (tmp_path / "text" / "en_csv_00.txt").write_text("Anna, edited", encoding="utf-8")
    with pytest.raises(SystemExit, match="does not match"):
        run(tmp_path)


def test_report_is_not_reached_when_digest_mismatches(tmp_path, monkeypatch):
    make_corpus(tmp_path, {"en_csv_00": ([label("PERSON", "Anna")], "Anna")})
    (tmp_path / "labels" / "en_csv_00.json").write_text(
        json.dumps({"file": "csv/en_csv_00.csv", "language": "en", "format": "csv",
                    "entities": []}), encoding="utf-8")
    called = []
    monkeypatch.setattr(bench, "build_analyzer", lambda: StubAnalyzer())
    monkeypatch.setattr(bench, "report", lambda *a: called.append(a))
    with pytest.raises(SystemExit):
        bench.main(str(tmp_path))
    assert called == []
