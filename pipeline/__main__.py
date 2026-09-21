"""Command-line entry point for the local anonymization pipeline."""

import argparse

from .core import DEFAULT_OUTPUT_DIR, run_pipeline
from .errors import PipelineError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a supported local file to anonymized Markdown."
    )
    parser.add_argument("input_file", help="Path to the source file")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for the generated Markdown file",
    )
    parser.add_argument(
        "--ocr-language",
        default="eng",
        help="Tesseract language code used for scanned pages and images",
    )
    args = parser.parse_args()

    try:
        result = run_pipeline(
            args.input_file,
            output_dir=args.output_dir,
            ocr_language=args.ocr_language,
            progress=print,
        )
    except PipelineError as exc:
        parser.exit(1, f"Error: {exc}\n")

    print(f"Created: {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
