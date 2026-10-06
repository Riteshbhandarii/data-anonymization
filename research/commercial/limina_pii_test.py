import argparse
import base64
import json
import os
import time
from pathlib import Path

import requests


DEFAULT_API_URL = "https://api.getlimina.ai/community/v4"

TEST_FILES = [
    {
        "path": "bench_final/docx/en_docx_00.docx",
        "language": "en",
        "format": "docx",
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    {
        "path": "bench_final/docx/fi_docx_00.docx",
        "language": "fi",
        "format": "docx",
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    {
        "path": "bench_final_detection/pdf/en_pdf_00.pdf",
        "language": "en",
        "format": "pdf",
        "content_type": "application/pdf",
    },
    {
        "path": "bench_final_detection/pdf/fi_pdf_00.pdf",
        "language": "fi",
        "format": "pdf",
        "content_type": "application/pdf",
    },
    {
        "path": "bench_final_detection/xlsx/en_xlsx_00.xlsx",
        "language": "en",
        "format": "xlsx",
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    {
        "path": "bench_final_detection/xlsx/fi_xlsx_00.xlsx",
        "language": "fi",
        "format": "xlsx",
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    {
        "path": "bench_final_detection/pptx/en_pptx_00.pptx",
        "language": "en",
        "format": "pptx",
        "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    },
    {
        "path": "bench_final_detection/pptx/fi_pptx_00.pptx",
        "language": "fi",
        "format": "pptx",
        "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    },
    {
        "path": "bench_final/csv/en_csv_00.csv",
        "language": "en",
        "format": "csv",
        "content_type": "text/csv",
    },
    {
        "path": "bench_final/csv/fi_csv_00.csv",
        "language": "fi",
        "format": "csv",
        "content_type": "text/csv",
    },
]


def process_file(api_url, api_key, item, output_root):
    source = Path(item["path"])

    if not source.exists():
        return {
            "file": str(source),
            "language": item["language"],
            "format": item["format"],
            "status": "missing",
        }

    print(f"\nProcessing: {source}")

    encoded = base64.b64encode(source.read_bytes()).decode("ascii")

    payload = {
        "file": {
            "data": encoded,
            "content_type": item["content_type"],
        },
        "entity_detection": {
            "return_entity": True,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    url = f"{api_url.rstrip('/')}/process/files/base64"

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=180,
        )
    except requests.RequestException as exc:
        print(f"Request failed: {exc}")
        return {
            "file": str(source),
            "language": item["language"],
            "format": item["format"],
            "status": "request_error",
            "error": str(exc),
        }

    print(f"HTTP {response.status_code}")

    if response.status_code != 200:
        try:
            error_body = response.json()
        except ValueError:
            error_body = response.text

        print(error_body)

        return {
            "file": str(source),
            "language": item["language"],
            "format": item["format"],
            "status": "api_error",
            "http_status": response.status_code,
            "error": error_body,
        }

    result = response.json()

    raw_dir = output_root / "raw"
    redacted_dir = output_root / "redacted"

    raw_dir.mkdir(parents=True, exist_ok=True)
    redacted_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / f"{source.stem}.json"

    with raw_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    processed_file = result.get("processed_file")

    redacted_path = None

    if processed_file:
        redacted_path = (
            redacted_dir
            / f"{source.stem}.redacted{source.suffix}"
        )

        try:
            redacted_bytes = base64.b64decode(
                processed_file,
                validate=True,
            )
            redacted_path.write_bytes(redacted_bytes)
        except Exception as exc:
            print(f"Could not decode redacted file: {exc}")
            redacted_path = None

    entities = result.get("entities", [])
    languages = result.get("languages_detected", {})

    print(f"Entities returned: {len(entities)}")
    print(f"Languages detected: {languages}")

    if redacted_path:
        print(f"Redacted file: {redacted_path}")

    print(f"Raw JSON: {raw_path}")

    return {
        "file": str(source),
        "language": item["language"],
        "format": item["format"],
        "status": "success",
        "http_status": response.status_code,
        "entity_count": len(entities),
        "entities_present": result.get("entities_present"),
        "languages_detected": languages,
        "page_count": result.get("page_count"),
        "raw_json": str(raw_path),
        "redacted_file": str(redacted_path) if redacted_path else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run representative Limina file anonymization tests."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N files.",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=7.0,
        help="Delay in seconds between API calls.",
    )

    parser.add_argument(
        "--output",
        default="commercial_limina_results",
        help="Directory for local test outputs.",
    )

    args = parser.parse_args()

    api_key = os.environ.get("LIMINA_API_KEY")

    if not api_key:
        raise SystemExit(
            "LIMINA_API_KEY is not set."
        )

    api_url = os.environ.get(
        "LIMINA_API_URL",
        DEFAULT_API_URL,
    )

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    files = TEST_FILES

    if args.limit is not None:
        files = files[: args.limit]

    summaries = []

    for index, item in enumerate(files):
        summary = process_file(
            api_url,
            api_key,
            item,
            output_root,
        )
        summaries.append(summary)

        if index < len(files) - 1:
            time.sleep(args.delay)

    summary_path = output_root / "summary.json"

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            summaries,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n==============================")
    print("Finished")
    print("==============================")

    for result in summaries:
        print(
            f"{result['format'].upper():5} "
            f"{result['language'].upper():2} "
            f"{result['status']}"
        )

    print(f"\nSummary: {summary_path}")


if __name__ == "__main__":
    main()