"""Orchestrate extraction, anonymization, and Markdown output."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .anonymization import Anonymizer, baseline_anonymize, run_anonymization_passes
from .extractors import extract_to_markdown
from .normalization import normalize_markdown

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
    anonymizer: Anonymizer = baseline_anonymize,
    anonymization_passes: int = 2,
    ocr_language: str = "eng",
    progress: ProgressCallback | None = None,
) -> PipelineResult:
    """Convert a local file to anonymized Markdown and save the result.

    The anonymizer contract is deliberately small: it accepts Markdown text and
    returns Markdown text. Team members can pass their implementation through
    the ``anonymizer`` argument without changing the extraction pipeline.
    """
    source = Path(input_path)
    destination_dir = Path(output_dir)
    if anonymization_passes < 1:
        raise ValueError("anonymization_passes must be at least 1")

    _report(progress, "Detecting the file type and extracting text")
    markdown = extract_to_markdown(source, ocr_language=ocr_language)

    _report(progress, "Normalizing extracted content as Markdown")
    markdown = normalize_markdown(markdown)

    for pass_number in range(1, anonymization_passes + 1):
        _report(progress, f"Running anonymization pass {pass_number}")
        markdown = run_anonymization_passes(markdown, anonymizer, passes=1)

    _report(progress, "Saving anonymized Markdown")
    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = destination_dir / f"{source.stem}_anonymized.md"
    output_path.write_text(markdown, encoding="utf-8")

    return PipelineResult(
        input_path=source,
        output_path=output_path,
        markdown=markdown,
    )


def _report(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)
