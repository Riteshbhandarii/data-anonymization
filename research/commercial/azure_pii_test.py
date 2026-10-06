import argparse
import json
import os
import time

import requests


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Azure Document PII redaction on one document."
    )

    parser.add_argument(
        "--file-id",
        required=True,
        help="Document id used in the Azure job, e.g. en_docx_00",
    )

    parser.add_argument(
        "--language",
        required=True,
        help="Document language, e.g. en-US or fi",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum polling time in seconds. Default: 300",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    endpoint = os.environ["AZURE_LANGUAGE_ENDPOINT"]
    key = os.environ["AZURE_LANGUAGE_KEY"]
    source_sas_url = os.environ["AZURE_SOURCE_SAS_URL"]
    output_sas_url = os.environ["AZURE_OUTPUT_SAS_URL"]

    submit_url = (
        f"{endpoint.rstrip('/')}"
        "/language/analyze-documents/jobs"
        "?api-version=2024-11-15-preview"
    )

    payload = {
        "displayName": f"Azure Document PII test - {args.file_id}",
        "analysisInput": {
            "documents": [
                {
                    "language": args.language,
                    "id": args.file_id,
                    "source": {
                        "location": source_sas_url
                    },
                    "target": {
                        "location": output_sas_url
                    },
                }
            ]
        },
        "tasks": [
            {
                "kind": "PiiEntityRecognition",
                "taskName": "PII Redaction",
                "parameters": {
                    "redactionPolicy": {
                        "policyKind": "entityMask"
                    },
                    "excludeExtractionData": False,
                },
            }
        ],
    }

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json",
    }

    print("Submitting job...")

    response = requests.post(
        submit_url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    print("Submit status:", response.status_code)

    if response.status_code not in (200, 201, 202):
        print("\nSubmission failed:")
        print(response.text)
        raise SystemExit(1)

    operation_location = response.headers.get("operation-location")

    if not operation_location:
        print("\nNo operation-location header returned.")
        raise SystemExit(1)

    print("Job submitted successfully.")
    print("Polling status...")

    start_time = time.monotonic()

    while True:
        elapsed = time.monotonic() - start_time

        if elapsed > args.timeout:
            print(
                f"\nPolling timed out after {args.timeout} seconds."
            )
            raise SystemExit(1)

        status_response = requests.get(
            operation_location,
            headers={
                "Ocp-Apim-Subscription-Key": key
            },
            timeout=30,
        )

        if status_response.status_code != 200:
            print("\nPolling failed:")
            print("Status code:", status_response.status_code)
            print(status_response.text)
            raise SystemExit(1)

        result = status_response.json()
        status = result.get("status", "unknown")

        print("Status:", status)

        if status.lower() in ("succeeded", "failed", "cancelled"):
            break

        time.sleep(3)

    print("\nFinal response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    output_json = f"{args.file_id}_azure_pii_result.json"

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\nSaved API result to {output_json}")


if __name__ == "__main__":
    main()