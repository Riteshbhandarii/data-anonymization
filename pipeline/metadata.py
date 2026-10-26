"""Remove extracted document properties without removing body/notes/comments."""

import re

_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def remove_document_metadata(markdown: str) -> str:
    """Drop complete 'Document metadata' sections, including nested subsections.

    The next heading of the same or a higher level resumes ordinary content.
    Fenced code is not interpreted as a heading. Backtick fence info strings
    cannot contain backticks; complete inline code spans do not start a block.
    Remaining text and line endings are preserved, so repeated calls are safe.
    This changes exported text only; it never edits or sanitizes the source
    Office/PDF container.
    """
    output, dropping, fence = [], None, None
    for line in markdown.splitlines(keepends=True):
        marker = _FENCE.fullmatch(line.rstrip("\r\n"))
        if fence:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence))
                            + r",}[ \t]*", line.rstrip("\r\n")):
                fence = None
        elif marker and (marker.group(1)[0] == "~" or "`" not in marker.group(2)):
            fence = marker.group(1)
        else:
            heading = _HEADING.match(line.rstrip("\r\n"))
            if heading:
                level, title = len(heading.group(1)), heading.group(2).strip()
                if dropping is not None and level <= dropping:
                    dropping = None
                if title.casefold() == "document metadata":
                    dropping = level if dropping is None else min(dropping, level)
        if dropping is None:
            output.append(line)
    return "".join(output)
