"""Small Markdown cleanup helpers used before anonymization."""

import re


def normalize_markdown(markdown: str) -> str:
    """Normalize newlines and excessive blank space without rewriting content."""
    normalized = markdown.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    return f"{normalized}\n" if normalized else ""
