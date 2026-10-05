"""Pure helpers for the testbench UI. No Streamlit and no model loading here."""

import html
import re
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import pairwise

from eval.bench import TYPE_MAP, found

PALETTE = ["#fde68a", "#bfdbfe", "#fbcfe8", "#bbf7d0", "#ddd6fe", "#fed7aa",
           "#a5f3fc", "#fecaca", "#e9d5ff", "#d9f99d", "#fcd5ce", "#c7d2fe"]
STATUS_COLOURS = {"covered": "#86efac", "partial": "#fde047", "missed": "#fca5a5"}

# Headings the extractor writes for content a reader never sees on the page.
_HIDDEN = re.compile(
    r"^(#{2,3}) (Document metadata|Tracked changes|Review comments|Speaker notes"
    r"|(First page |Even page )?(header|footer)\b.*)$", re.IGNORECASE)
_HEADING = re.compile(r"^(#{2,3}) (.*)$")


def split_sections(markdown):
    """Return (title, body, hidden) for each heading-delimited section.

    Text before the first heading gets the title "(start)". A section is hidden
    when the extractor's heading says it holds metadata, notes, comments,
    tracked changes or headers/footers. Hidden worksheets carry no marker in
    the Markdown, so they appear as ordinary sheets.
    """
    sections, title, body, hidden = [], "(start)", [], False
    for line in markdown.split("\n"):
        if _HEADING.match(line):
            if "".join(body).strip() or title != "(start)":
                sections.append((title, "\n".join(body).strip(), hidden))
            title, body, hidden = line.lstrip("# ").strip(), [], bool(_HIDDEN.match(line))
        else:
            body.append(line)
    sections.append((title, "\n".join(body).strip(), hidden))
    return sections


def type_colours(types):
    return {t: PALETTE[i % len(PALETTE)] for i, t in enumerate(sorted(set(types)))}


def merge_intervals(items):
    """Union of overlapping (start, end, label, score) items; label of the top score."""
    merged = []
    for s, e, label, score in sorted(items, key=lambda i: (i[0], -i[1])):
        if merged and s < merged[-1][1]:
            last = merged[-1]
            top = label if score > last[3] else last[2]
            merged[-1] = (last[0], max(last[1], e), top, max(score, last[3]))
        else:
            merged.append((s, e, label, score))
    return merged


def highlight_html(text, intervals, colours, title_fn=None):
    """Render pipeline Markdown with highlights at original character offsets.

    Headings, tables, lists, quotes and common inline formatting are rendered
    as HTML. Text keeps its spacing and inherits the page's font. Raw HTML is
    escaped, and Markdown links and images show their labels without loading
    resources. An interval crossing formatting or table cells becomes several
    marks, all with the same colour and tooltip.
    """
    valid = [(max(0, i[0]), min(len(text), i[1]), i[2], i[3] if len(i) > 3 else 0)
             for i in intervals if i[0] < len(text) and i[1] > 0 and i[1] > i[0]]
    merged = merge_intervals(valid)

    def highlighted(start, end):
        if end <= start:
            return ""
        out, pos = [], start
        for left, right, label, _ in merged:
            if right <= start:
                continue
            if left >= end:
                break
            left, right = max(start, left), min(end, right)
            out.append(html.escape(text[pos:left]))
            colour = colours.get(label, "#ddd")
            if not re.fullmatch(r"#(?:[\da-fA-F]{3}|[\da-fA-F]{4}|[\da-fA-F]{6}|[\da-fA-F]{8})",
                                str(colour)):
                colour = "#ddd"
            tip = html.escape(str(title_fn(label) if title_fn else label), quote=True)
            out.append(f'<mark style="background:{colour};color:#111;'
                       f'padding:0 2px;border-radius:3px" title="{tip}">'
                       f'{html.escape(text[left:right])}</mark>')
            pos = right
        out.append(html.escape(text[pos:end]))
        return "".join(out)

    def inline(start, end, table_cell=False):
        out, pos = [], start
        for match in _INLINE.finditer(text, start, end):
            out.append(highlighted(pos, match.start()))
            kind = match.lastgroup
            if kind == "escaped":
                out.append(highlighted(match.start() + 1, match.end()))
            elif kind == "cell_break":
                out.append("<br>" if table_cell else highlighted(match.start(), match.end()))
            elif kind in {"link", "image"}:
                label_start = match.start() + (2 if kind == "image" else 1)
                label_end = text.index("]", label_start, match.end())
                out.append(inline(label_start, label_end, table_cell))
            elif kind == "code":
                out.append("<code>" + highlighted(match.start() + 1,
                                                 match.end() - 1) + "</code>")
            else:
                width = 2 if kind in {"strong", "strong_alt", "strike"} else 1
                tag = "strong" if width == 2 else "em"
                if kind == "strike":
                    tag = "s"
                out.append(f"<{tag}>" + inline(match.start() + width,
                                               match.end() - width, table_cell) + f"</{tag}>")
            pos = match.end()
        out.append(highlighted(pos, end))
        return "".join(out)

    lines, offset = [], 0
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        lines.append((line, offset, offset + len(line)))
        offset += len(raw)

    out, paragraph, index = [], [], 0

    def flush_paragraph():
        if paragraph:
            out.append('<p style="margin:0 0 0.85rem">' +
                       inline(paragraph[0][1], paragraph[-1][2]) + "</p>")
            paragraph.clear()

    while index < len(lines):
        line, start, end = lines[index]
        heading = _DISPLAY_HEADING.match(line)
        fence = _FENCE.match(line)
        cells = _table_cells(line, start)
        separator = (_table_cells(lines[index + 1][0], lines[index + 1][1])
                     if cells and index + 1 < len(lines) else None)
        table = separator and all(_TABLE_SEPARATOR.fullmatch(text[a:b])
                                  for a, b in separator)
        list_item = _LIST_ITEM.match(line)
        quote = _QUOTE.match(line)
        if not line.strip():
            flush_paragraph()
        elif heading:
            flush_paragraph()
            level = len(heading.group(1))
            size = "1.25rem" if level <= 2 else "1.05rem"
            out.append(f'<h{level} style="font-family:inherit;font-size:{size};'
                       'line-height:1.4;margin:0.9rem 0 0.5rem">' +
                       inline(start + heading.start(2), start + heading.end(2)) +
                       f"</h{level}>")
        elif fence:
            flush_paragraph()
            marker = fence.group(1)
            code_start = index + 1
            index = code_start
            while index < len(lines) and not re.fullmatch(
                    r" {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*",
                    lines[index][0]):
                index += 1
            code = (highlighted(lines[code_start][1], lines[index - 1][2])
                    if index > code_start else "")
            out.append('<pre style="white-space:pre-wrap;overflow-wrap:anywhere;'
                       'margin:0 0 0.85rem"><code>' + code + "</code></pre>")
        elif table:
            flush_paragraph()
            out.append('<div style="overflow-x:auto"><table style="border-collapse:collapse;'
                       'width:100%;min-width:40rem;margin:0 0 0.85rem"><thead><tr>')
            for left, right in cells:
                out.append('<th style="text-align:left;white-space:nowrap;border-bottom:1px solid #d1d5db;'
                           'padding:0.45rem 0.65rem">' + inline(left, right, True) + "</th>")
            out.append("</tr></thead><tbody>")
            index += 2
            while index < len(lines):
                row = _table_cells(lines[index][0], lines[index][1])
                if row is None:
                    break
                out.append("<tr>")
                for left, right in row:
                    out.append('<td style="border-bottom:1px solid #e5e7eb;'
                               'padding:0.45rem 0.65rem">' + inline(left, right, True) + "</td>")
                out.append("</tr>")
                index += 1
            out.append("</tbody></table></div>")
            continue
        elif list_item:
            flush_paragraph()
            ordered = list_item.group(1)[0].isdigit()
            tag = "ol" if ordered else "ul"
            number = list_item.group(1).rstrip(".)")
            attr = f' start="{int(number)}"' if ordered else ""
            out.append(f'<{tag}{attr} style="margin:0 0 0.85rem;padding-left:1.5rem">')
            while index < len(lines):
                item = _LIST_ITEM.match(lines[index][0])
                if not item or item.group(1)[0].isdigit() != ordered:
                    break
                item_start = lines[index][1] + item.start(2)
                out.append("<li>" + inline(item_start, lines[index][2]) + "</li>")
                index += 1
            out.append(f"</{tag}>")
            continue
        elif quote:
            flush_paragraph()
            out.append('<blockquote style="border-left:3px solid #d1d5db;'
                       'padding-left:0.8rem;margin:0 0 0.85rem">' +
                       inline(start + quote.start(1), end) + "</blockquote>")
        elif _RULE.fullmatch(line):
            flush_paragraph()
            out.append("<hr>")
        else:
            paragraph.append(lines[index])
        index += 1
    flush_paragraph()
    return ('<div class="document-preview" style="white-space:pre-wrap;'
            'font-family:inherit;font-size:inherit;line-height:1.65;'
            'overflow-wrap:anywhere">' + "".join(out) + "</div>")


# The extractor emits a small Markdown vocabulary. Keeping source slices intact
# makes detection offsets reliable even inside formatting and escaped cells.
_INLINE = re.compile(
    r"(?P<escaped>\\[\\`*{}\[\]()#+.!_|>~-])"
    r"|(?P<cell_break><br ?/?>)"
    r"|(?P<image>!\[[^\]\n]*\]\([^\)\n]*\))"
    r"|(?P<link>\[[^\]\n]+\]\([^\)\n]*\))"
    r"|(?P<code>`[^`]+`)"
    r"|(?P<strong>\*\*[^\n]+?\*\*)"
    r"|(?P<strong_alt>__[^\n]+?__)"
    r"|(?P<strike>~~[^\n]+?~~)"
    r"|(?P<em>\*[^*\n]+?\*)"
    r"|(?P<em_alt>(?<!\w)_[^_\n]+?_(?!\w))")
_DISPLAY_HEADING = re.compile(r" {0,3}(#{1,6})\s+(.*?)(?:\s+#+\s*)?$")
_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})[^`]*$")
_TABLE_SEPARATOR = re.compile(r"\s*:?-{3,}:?\s*")
_LIST_ITEM = re.compile(r" {0,3}([-+*]|\d+[.)])\s+(.*)$")
_QUOTE = re.compile(r" {0,3}>\s?(.*)$")
_RULE = re.compile(r" {0,3}([-*_])(?:\s*\1){2,}\s*$")


def _table_cells(line, start):
    """Return source ranges for cells, keeping escaped or code-span pipes."""
    separators, escaped, code = [], False, False
    for pos, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "`":
            code = not code
        elif char == "|" and not code:
            separators.append(pos)
    if not separators:
        return None
    bounds = [-1, *separators, len(line)]
    cells = [(left + 1, right) for left, right in pairwise(bounds)]
    if not line[:separators[0]].strip():
        cells = cells[1:]
    if not line[separators[-1] + 1:].strip():
        cells = cells[:-1]
    result = []
    for left, right in cells:
        while left < right and line[left].isspace():
            left += 1
        while right > left and line[right - 1].isspace():
            right -= 1
        result.append((start + left, start + right))
    return result or None


def changed_intervals(original, clean, label="REPLACED"):
    """Return changed character intervals in each version for paired previews.

    Offsets refer independently to the original and cleaned strings. Insertions
    have an interval only on the cleaned side; deletions only on the original
    side. Changed lines or sentences are compared as word, whitespace and
    punctuation tokens. This avoids matching incidental letters between a
    person's name and a replacement, and bounds work on repeated documents.
    Unchanged tokens, including repeated text and Unicode, are left untouched.
    The comparison does not assume a particular anonymizer's placeholder style.
    """
    before, after = [], []

    def compare_words(old_start, old_end, new_start, new_end):
        old_tokens = list(re.finditer(r"\w+|\s+|[^\w\s]", original[old_start:old_end]))
        new_tokens = list(re.finditer(r"\w+|\s+|[^\w\s]", clean[new_start:new_end]))
        # A single unusually long changed line still gets a bounded comparison.
        # Ordinary lines retain whitespace and repeated words as useful matches.
        matcher = SequenceMatcher(None, [t.group() for t in old_tokens],
                                  [t.group() for t in new_tokens],
                                  autojunk=len(old_tokens) + len(new_tokens) > 4096)
        for operation, left, right, new_left, new_right in matcher.get_opcodes():
            if operation == "equal":
                continue
            if left < right:
                before.append((old_start + old_tokens[left].start(),
                               old_start + old_tokens[right - 1].end(), label, 1.0))
            if new_left < new_right:
                after.append((new_start + new_tokens[new_left].start(),
                              new_start + new_tokens[new_right - 1].end(), label, 1.0))

    def chunks(value):
        ranges, start = [], 0
        for boundary in re.finditer(r"\r\n|\r|\n|(?<=[.!?])[ \t]+", value):
            ranges.append((start, boundary.end()))
            start = boundary.end()
        if start < len(value):
            ranges.append((start, len(value)))
        return ranges

    old_chunks, new_chunks = chunks(original), chunks(clean)
    matcher = SequenceMatcher(None, [original[a:b] for a, b in old_chunks],
                              [clean[a:b] for a, b in new_chunks])
    for operation, left, right, new_left, new_right in matcher.get_opcodes():
        if operation == "equal":
            continue
        if right - left == new_right - new_left:
            for old_chunk, new_chunk in zip(old_chunks[left:right], new_chunks[new_left:new_right]):
                compare_words(*old_chunk, *new_chunk)
        else:
            old_start = old_chunks[left][0] if left < len(old_chunks) else len(original)
            old_end = old_chunks[right - 1][1] if left < right else old_start
            new_start = new_chunks[new_left][0] if new_left < len(new_chunks) else len(clean)
            new_end = new_chunks[new_right - 1][1] if new_left < new_right else new_start
            compare_words(old_start, old_end, new_start, new_end)
    return before, after


def score_labels(text, entities, results):
    """Score each labelled value with eval.bench.found through TYPE_MAP.

    Returns dicts with type, value, location and status in
    covered / partial / missed / absent (value not in the extracted text).
    """
    by_type = defaultdict(list)
    for r in results:
        by_type[TYPE_MAP.get(r.entity_type)].append(r)
    scored = []
    for e in entities:
        if e["value"] not in text:
            status = "absent"
        else:
            status = found(text, e["value"], by_type[e["type"]]) or "missed"
        scored.append({**e, "status": status})
    return scored


def label_intervals(text, scored):
    """Every occurrence of every present labelled value, tagged by its status."""
    items = []
    for e in scored:
        if e["status"] == "absent":
            continue
        start = text.find(e["value"])
        while start >= 0:
            items.append((start, start + len(e["value"]), e["status"], 1))
            start = text.find(e["value"], start + 1)
    return items


def summarize(scored):
    """(found, total, {type: [missed values]}); found counts covered values only."""
    present = [s for s in scored if s["status"] != "absent"]
    misses = defaultdict(list)
    for s in present:
        if s["status"] != "covered":
            misses[s["type"]].append(f'{s["value"]} ({s["status"]})')
    return sum(s["status"] == "covered" for s in present), len(present), dict(misses)


def recall_table(rows):
    """Aggregate results.csv rows (dicts) into {(dataset, method): recall}."""
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        key = (r["dataset"], r["method"])
        agg[key][0] += int(r["covered"])
        agg[key][1] += int(r["planted"])
    return {k: (c / p if p else float("nan")) for k, (c, p) in agg.items()}
