"""Check the testbench helpers without loading any spaCy model."""

import unittest
from html.parser import HTMLParser
from time import perf_counter
from types import SimpleNamespace

from app.logic import (
    changed_intervals,
    highlight_html,
    label_intervals,
    recall_table,
    score_labels,
    split_sections,
    summarize,
)


class RenderedDocument(HTMLParser):
    """Read visible text and highlighted runs independently of HTML layout."""

    def __init__(self, content):
        super().__init__()
        self.tags, self.text, self.marks = [], [], []
        self.active = None
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "mark":
            self.active = []

    def handle_endtag(self, tag):
        if tag == "mark":
            self.marks.append("".join(self.active))
            self.active = None

    def handle_data(self, data):
        self.text.append(data)
        if self.active is not None:
            self.active.append(data)


def span(start, end, entity_type):
    return SimpleNamespace(start=start, end=end, entity_type=entity_type, score=0.8)


class AppLogicTests(unittest.TestCase):
    text = "Mail Anna <a@b.fi> or call +358 40 1234567 about Ox."

    def entities(self):
        return [{"type": "PERSON", "value": "Anna", "location": "body"},
                {"type": "EMAIL", "value": "a@b.fi", "location": "body"},
                {"type": "PHONE", "value": "+358 40 1234567", "location": "body"},
                {"type": "COMPANY", "value": "Secret Oy", "location": "metadata"}]

    def test_found_partial_missed_absent(self):
        t = self.text
        results = [span(5, 9, "PERSON"),
                   span(t.index("a@b"), t.index("a@b") + 3, "EMAIL_ADDRESS"),
                   span(0, 4, "PHONE_NUMBER")]  # wrong place
        status = {s["type"]: s["status"] for s in score_labels(t, self.entities(), results)}
        self.assertEqual(status, {"PERSON": "covered", "EMAIL": "partial",
                                  "PHONE": "missed", "COMPANY": "absent"})

    def test_wrong_type_does_not_count(self):
        scored = score_labels(self.text, self.entities()[:1], [span(5, 9, "LOCATION")])
        self.assertEqual(scored[0]["status"], "missed")

    def test_summary_counts_and_misses(self):
        scored = score_labels(self.text, self.entities(), [span(5, 9, "PERSON")])
        got, total, misses = summarize(scored)
        self.assertEqual((got, total), (1, 3))
        self.assertEqual(sorted(misses), ["EMAIL", "PHONE"])

    def test_highlight_escapes_and_marks(self):
        out = highlight_html("<b>Anna</b> & co", [(3, 7, "PERSON", 0.9)], {"PERSON": "#fff"})
        self.assertIn("&lt;b&gt;", out)
        self.assertIn(">Anna</mark>", out)
        self.assertNotIn("<b>", out)

    def test_overlaps_are_merged(self):
        out = highlight_html("abcdef", [(0, 3, "A", 0.5), (2, 5, "B", 0.9)], {})
        self.assertEqual(out.count("<mark"), 1)
        self.assertIn(">abcde</mark>", out)

    def test_heading_and_table_are_rendered_with_original_offsets(self):
        markdown = "## Anna\n\n| Name | Email |\n| --- | --- |\n| **Anna** | anna@example.org |"
        second = markdown.index("Anna", markdown.index("| **"))
        email = markdown.index("anna@example.org")
        out = highlight_html(markdown, [(second, second + 4, "PERSON"),
                                        (email, email + 16, "EMAIL")],
                             {"PERSON": "#bfdbfe", "EMAIL": "#fde68a"})
        doc = RenderedDocument(out)
        tags = [tag for tag, _ in doc.tags]
        self.assertIn("h2", tags)
        self.assertIn("table", tags)
        self.assertIn("strong", tags)
        self.assertEqual(doc.marks, ["Anna", "anna@example.org"])
        visible = "".join(doc.text)
        self.assertNotIn("##", visible)
        self.assertNotIn("|", visible)
        self.assertNotIn("---", visible)
        self.assertNotIn("**", visible)
        self.assertIn("font-family:inherit", out)
        self.assertNotIn("font-family:monospace", out)

    def test_span_crossing_formatting_and_table_cells_keeps_each_visible_piece(self):
        markdown = "| Person | City |\n| --- | --- |\n| **Märta** | Turku |"
        start = markdown.index("Märta")
        end = markdown.index("Turku") + len("Turku")
        doc = RenderedDocument(highlight_html(markdown, [(start, end, "MATCH")],
                                              {"MATCH": "#abc"},
                                              lambda _: "Sensitive match"))
        self.assertEqual(doc.marks, ["Märta", "Turku"])
        for tag, attrs in doc.tags:
            if tag == "mark":
                self.assertEqual(attrs["title"], "Sensitive match")
                self.assertIn("background:#abc", attrs["style"])

    def test_escaped_pipe_stays_inside_one_table_cell_and_keeps_highlight_offset(self):
        markdown = "| Value | Person |\n| --- | --- |\n| a\\|b | Eva |"
        start = markdown.index("a\\|b")
        doc = RenderedDocument(highlight_html(markdown, [(start, start + 4, "VALUE")], {}))
        self.assertEqual(sum(tag == "td" for tag, _ in doc.tags), 2)
        self.assertEqual("".join(doc.marks), "a|b")
        self.assertIn("a|b", "".join(doc.text))

    def test_untrusted_html_colours_and_tooltips_cannot_create_active_content(self):
        markdown = '<script>alert("x")</script> Anna'
        start = markdown.index("Anna")
        out = highlight_html(markdown, [(start, start + 4, "PERSON")],
                             {"PERSON": 'red;background:url(https://example.org/x)'},
                             lambda _: '\" onmouseover=\"alert(1)')
        doc = RenderedDocument(out)
        self.assertEqual("".join(doc.text), markdown)
        self.assertNotIn("script", [tag for tag, _ in doc.tags])
        mark = next(attrs for tag, attrs in doc.tags if tag == "mark")
        self.assertNotIn("onmouseover", mark)
        self.assertIn("background:#ddd", mark["style"])
        self.assertNotIn("url(", out)

    def test_links_and_images_show_labels_without_loading_resources(self):
        markdown = "[Contact Anna](https://example.org) ![Portrait](https://example.org/photo.png)"
        start = markdown.index("Anna")
        doc = RenderedDocument(highlight_html(markdown, [(start, start + 4, "PERSON")], {}))
        self.assertEqual("".join(doc.text), "Contact Anna Portrait")
        self.assertEqual(doc.marks, ["Anna"])
        self.assertFalse(any(tag in {"a", "img"} for tag, _ in doc.tags))
        self.assertFalse(any("src" in attrs or "href" in attrs for _, attrs in doc.tags))

    def test_code_fences_lists_quotes_and_plain_pdf_paragraphs(self):
        markdown = ("A PDF line\ncontinues here.\n\n- Anna\n- Eva\n\n"
                    "> Review this\n\n```text\nAnna <script>\n```\n")
        start = markdown.rindex("Anna")
        doc = RenderedDocument(highlight_html(markdown, [(start, start + 4, "PERSON")], {}))
        tags = [tag for tag, _ in doc.tags]
        self.assertIn("ul", tags)
        self.assertIn("blockquote", tags)
        self.assertIn("pre", tags)
        self.assertIn("code", tags)
        self.assertNotIn("script", tags)
        self.assertEqual(doc.marks, ["Anna"])
        visible = "".join(doc.text)
        self.assertIn("A PDF line\ncontinues here.", visible)
        self.assertNotIn("```", visible)
        self.assertNotIn("> Review", visible)

    def test_multiline_unicode_and_adjacent_spans_keep_source_coordinates(self):
        markdown = "## People\r\n\r\nMärta 😀\r\nWei"
        first = markdown.index("Märta")
        emoji = markdown.index("😀")
        doc = RenderedDocument(highlight_html(markdown,
                                              [(first, emoji, "PERSON"),
                                               (emoji, emoji + 1, "OTHER"),
                                               (emoji + 1, len(markdown), "MULTILINE")], {}))
        self.assertEqual(doc.marks, ["Märta ", "😀", "\r\nWei"])

    def test_out_of_bounds_intervals_are_clipped_or_ignored(self):
        doc = RenderedDocument(highlight_html("Anna", [(-2, 2, "A"), (2, 99, "B"),
                                                     (7, 9, "C"), (2, 2, "D")], {}))
        self.assertEqual(doc.marks, ["An", "na"])

    def test_changed_intervals_use_both_versions_and_do_not_require_placeholders(self):
        original = "Märta 😀\nmail: x@y.fi"
        clean = "Anonymous\nmail: hidden"
        before, after = changed_intervals(original, clean)
        self.assertTrue(before)
        self.assertTrue(after)
        self.assertTrue(all(original[start:end] for start, end, _, _ in before))
        self.assertTrue(all(clean[start:end] for start, end, _, _ in after))
        original_doc = RenderedDocument(highlight_html(original, before, {}))
        clean_doc = RenderedDocument(highlight_html(clean, after, {}))
        self.assertEqual("".join(original_doc.text), original)
        self.assertEqual("".join(clean_doc.text), clean)
        self.assertTrue(original_doc.marks)
        self.assertTrue(clean_doc.marks)

    def test_changed_intervals_preserve_repeated_matching_text(self):
        original = "Eva met Eva."
        clean = "Eva met [PERSON]."
        before, after = changed_intervals(original, clean)
        self.assertEqual(before, [(8, 11, "REPLACED", 1.0)])
        self.assertEqual(after, [(8, 16, "REPLACED", 1.0)])

    def test_changed_intervals_handle_insertions_deletions_and_no_change(self):
        self.assertEqual(changed_intervals("ab", "ab X"),
                         ([], [(2, 4, "REPLACED", 1.0)]))
        self.assertEqual(changed_intervals("ab X", "ab"),
                         ([(2, 4, "REPLACED", 1.0)], []))
        self.assertEqual(changed_intervals("😀", "😀"), ([], []))

    def test_adjacent_replacements_cover_both_complete_versions(self):
        original, clean = "AnnaEva", "[PERSON_1][PERSON_2]"
        self.assertEqual(changed_intervals(original, clean),
                         ([(0, len(original), "REPLACED", 1.0)],
                          [(0, len(clean), "REPLACED", 1.0)]))

    def test_code_span_pipe_does_not_split_a_table_cell(self):
        markdown = "| Value |\n| --- |\n| `a|b` |"
        start = markdown.index("a|b")
        doc = RenderedDocument(highlight_html(markdown, [(start, start + 3, "VALUE")], {}))
        self.assertEqual(sum(tag == "td" for tag, _ in doc.tags), 1)
        self.assertEqual(doc.marks, ["a|b"])

    def test_extracted_table_cell_breaks_render_without_allowing_arbitrary_html(self):
        markdown = '| Person |\n| --- |\n| Anna<br>Eva \\| <img src="https://example.org/x"> |'
        start = markdown.index("Anna")
        end = markdown.index("Eva") + len("Eva")
        doc = RenderedDocument(highlight_html(markdown, [(start, end, "PERSON")], {}))
        tags = [tag for tag, _ in doc.tags]
        self.assertEqual(tags.count("br"), 1)
        self.assertNotIn("img", tags)
        self.assertEqual(doc.marks, ["Anna", "Eva"])
        self.assertIn('| <img src="https://example.org/x">', "".join(doc.text))
        self.assertNotIn("<br>", "".join(doc.text))
        plain = RenderedDocument(highlight_html("Literal <br> text", [], {}))
        self.assertEqual("".join(plain.text), "Literal <br> text")

    def test_large_repeated_documents_keep_precise_changes_without_slow_global_matching(self):
        row = ("| Anna Example | anna@example.org | A repeated quarterly note. " +
               "The figures remain unchanged. " * 4 + "|\n")
        original = "| Person | Contact | Notes |\n| --- | --- | --- |\n" + row * 786
        clean = original.replace("Anna Example", "[PERSON]")
        started = perf_counter()
        before, after = changed_intervals(original, clean)
        self.assertLess(perf_counter() - started, 5.0)
        self.assertEqual(len(before), 786)
        self.assertEqual(len(after), 786)
        self.assertTrue(all(original[start:end] == "Anna Example" for start, end, _, _ in before))
        self.assertTrue(all(clean[start:end] == "[PERSON]" for start, end, _, _ in after))

    def test_label_intervals_cover_every_occurrence(self):
        scored = [{"type": "PERSON", "value": "Eva", "location": "body", "status": "partial"}]
        self.assertEqual(len(label_intervals("Eva met Eva", scored)), 2)

    def test_hidden_sections(self):
        md = ("## Document metadata\nAuthor: X\n\n## Document content\nbody\n\n"
              "## Footer (section 1)\nfoot\n\n## Slide 1\ns\n\n### Speaker notes\nn")
        hidden = {t: h for t, _, h in split_sections(md)}
        self.assertEqual(hidden, {"Document metadata": True, "Document content": False,
                                  "Footer (section 1)": True, "Slide 1": False,
                                  "Speaker notes": True})

    def test_recall_table(self):
        rows = [{"dataset": "d", "method": "m", "covered": "3", "planted": "4"},
                {"dataset": "d", "method": "m", "covered": "1", "planted": "4"}]
        self.assertEqual(recall_table(rows), {("d", "m"): 0.5})


if __name__ == "__main__":
    unittest.main()
