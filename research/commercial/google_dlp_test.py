import argparse
import json
import logging
import time
from pathlib import Path

from google.cloud import dlp_v2
from google.protobuf.json_format import MessageToDict

PROJECT_ID = "data-anonymization-research"
logger = logging.getLogger(__name__)

TEST_FILES = [
    ("bench_final/docx/en_docx_00.docx", "en", "docx"),
    ("bench_final/docx/fi_docx_00.docx", "fi", "docx"),

    ("bench_final_detection/pdf/en_pdf_00.pdf", "en", "pdf"),
    ("bench_final_detection/pdf/fi_pdf_00.pdf", "fi", "pdf"),

    ("bench_final_detection/xlsx/en_xlsx_00.xlsx", "en", "xlsx"),
    ("bench_final_detection/xlsx/fi_xlsx_00.xlsx", "fi", "xlsx"),

    ("bench_final_detection/pptx/en_pptx_00.pptx", "en", "pptx"),
    ("bench_final_detection/pptx/fi_pptx_00.pptx", "fi", "pptx"),

    ("bench_final/csv/en_csv_00.csv", "en", "csv"),
    ("bench_final/csv/fi_csv_00.csv", "fi", "csv"),
]


FILE_TYPES = {
    "docx": dlp_v2.ByteContentItem.BytesType.WORD_DOCUMENT,
    "pdf": dlp_v2.ByteContentItem.BytesType.PDF,
    "xlsx": dlp_v2.ByteContentItem.BytesType.EXCEL_DOCUMENT,
    "pptx": dlp_v2.ByteContentItem.BytesType.POWERPOINT_DOCUMENT,
    "csv": dlp_v2.ByteContentItem.BytesType.CSV,
}


def inspect_file(client, path, language, fmt, output_dir):
    print(f"\nProcessing: {path}")

    summary = {
        "file": str(path),
        "language": language,
        "format": fmt,
    }

    if not path.exists():
        print("File missing")
        summary["status"] = "missing"
        return summary

    try:
        response = client.inspect_content(
            request={
                "parent": f"projects/{PROJECT_ID}/locations/global",
                "item": {
                    "byte_item": {
                        "type_": FILE_TYPES[fmt],
                        "data": path.read_bytes(),
                    }
                },
                "inspect_config": {
                    "min_likelihood": "POSSIBLE",
                    "include_quote": True,
                    "limits": {
                        "max_findings_per_request": 1000,
                    },
                },
            },
            timeout=120,
        )

        result = MessageToDict(
            response._pb,
            preserving_proto_field_name=True,
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{path.stem}.json"

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(
                result,
                f,
                indent=2,
                ensure_ascii=False,
            )

        findings = response.result.findings

        print(f"SUCCESS: {len(findings)} findings")

        for finding in findings:
            print(
                finding.info_type.name,
                "|",
                repr(finding.quote),
            )

        summary.update({
            "status": "success",
            "findings": len(findings),
            "raw_json": str(output_path),
        })

    except Exception as error:
        logger.exception("Google DLP inspection failed for %s", path)
        print(f"ERROR: {error}")

        summary.update({
            "status": "error",
            "error": str(error),
        })

    return summary


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
    )

    args = parser.parse_args()

    client = dlp_v2.DlpServiceClient()

    output_root = Path("commercial_google_results")
    raw_dir = output_root / "raw"

    tests = TEST_FILES

    if args.limit is not None:
        tests = tests[:args.limit]

    summaries = []

    for index, (file_path, language, fmt) in enumerate(tests):
        result = inspect_file(
            client,
            Path(file_path),
            language,
            fmt,
            raw_dir,
        )

        summaries.append(result)

        if index < len(tests) - 1:
            time.sleep(args.delay)

    output_root.mkdir(parents=True, exist_ok=True)

    summary_path = output_root / "summary.json"

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            summaries,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n==============================")
    print("GOOGLE DLP TEST SUMMARY")
    print("==============================")

    for result in summaries:
        print(
            f"{result['format'].upper():5} "
            f"{result['language'].upper():2} "
            f"{result['status']}"
        )

    print(f"\nSaved: {summary_path}")

    if any(result["status"] != "success" for result in summaries):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
