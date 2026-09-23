"""Small Markdown cleanup helpers used before anonymization."""

import re


def normalize_markdown(markdown: str) -> str:
    """Normalize line endings and blank lines while preserving Markdown spacing."""
    normalized = markdown.replace("\r\n", "\n").replace("\r", "\n")
    # Keep content-line whitespace: trailing spaces can mark a hard break,
    # and leading spaces can define indentation or code blocks.
    normalized = "\n".join(line if line.strip() else "" for line in normalized.split("\n"))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip("\n")
    return f"{normalized}\n" if normalized else ""
