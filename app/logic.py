"""Pure helpers for the testbench UI. No Streamlit and no model loading here."""

import html
import re
from collections import defaultdict

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
    """Escape text and wrap each (start, end, label, ...) interval in a <mark>."""
    out, pos = [], 0
    for s, e, label, *rest in merge_intervals([(*i[:3], i[3] if len(i) > 3 else 0) for i in intervals]):
        out.append(html.escape(text[pos:s]))
        tip = html.escape(title_fn(label) if title_fn else label)
        out.append(f'<mark style="background:{colours.get(label, "#ddd")};color:#111;'
                   f'padding:0 2px;border-radius:3px" title="{tip}">'
                   f'{html.escape(text[s:e])}</mark>')
        pos = e
    out.append(html.escape(text[pos:]))
    return ('<div style="white-space:pre-wrap;font-family:monospace;font-size:0.85rem;'
            'line-height:1.5">' + "".join(out) + "</div>")


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
