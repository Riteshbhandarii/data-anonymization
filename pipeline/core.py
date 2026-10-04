"""Orchestrate extraction, anonymization, and Markdown output."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .errors import AnonymizationError, ExtractionError, PipelineError
from .extractors import extract_to_markdown
from .normalization import normalize_markdown

Anonymizer = Callable[[str], str]
Extractor = Callable[[Path], str]
ProgressCallback = Callable[[str], None]
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


@dataclass(frozen=True)
class PipelineResult:
    """The saved file and text produced by one pipeline run."""

    input_path: Path
    output_path: Path
    markdown: str


def run_pipeline(
    input_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    anonymizer: Anonymizer,
    extractor: Extractor | None = None,
    ocr_language: str = "eng",
    progress: ProgressCallback | None = None,
) -> PipelineResult:
    """Extract Markdown, call the anonymization module, and save its output.

    ``anonymizer`` is required and receives the complete normalized Markdown
    string. Its returned string is saved unchanged as UTF-8 Markdown.
    ``extractor`` optionally replaces the built-in format routing and OCR; it
    receives a Path and returns Markdown text. ``ocr_language`` applies only to
    the built-in extractor. ``progress`` receives a message at each stage.
    Output names retain the input extension and gain a numbered suffix when a
    file with the same output name already exists.
    """
    source = Path(input_path)
    destination_dir = Path(output_dir)
    if not source.is_file():
        raise ExtractionError(f"Input file does not exist: {source}")
    if not callable(anonymizer):
        raise TypeError("anonymizer must be a callable accepting and returning str")

    _report(progress, "Detecting the file type and extracting text")
    # A custom extractor can replace the existing reader without changing the flow.
    try:
        if extractor is None:
            markdown = extract_to_markdown(source, ocr_language=ocr_language)
        else:
            markdown = extractor(source)
    except PipelineError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Text extraction failed: {exc}") from exc

    if not isinstance(markdown, str):
        raise ExtractionError("The extractor must return a Markdown string.")

    _report(progress, "Normalizing extracted content as Markdown")
    markdown = normalize_markdown(markdown)

    # Hand the complete Markdown to the anonymization module and receive its output.
    _report(progress, "Anonymizing Markdown")
    try:
        markdown = anonymizer(markdown)
    except Exception as exc:
        raise AnonymizationError(f"Anonymization failed: {exc}") from exc
    if not isinstance(markdown, str):
        raise AnonymizationError("The anonymizer must return a Markdown string.")

    _report(progress, "Saving anonymized Markdown")
    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = _save_markdown(destination_dir, source.name, markdown)

    return PipelineResult(
        input_path=source,
        output_path=output_path,
        markdown=markdown,
    )


def _save_markdown(destination_dir: Path, source_name: str, markdown: str) -> Path:
    """Save UTF-8 output without overwriting a previous or concurrent run."""
    base_name = f"{source_name}_anonymized"
    sequence = 1
    while True:
        suffix = "" if sequence == 1 else f"_{sequence}"
        output_path = destination_dir / f"{base_name}{suffix}.md"
        try:
            # Exclusive creation also protects against simultaneous pipeline runs.
            with output_path.open("x", encoding="utf-8", newline="\n") as output:
                output.write(markdown)
            return output_path
        except FileExistsError:
            sequence += 1


def _report(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)
