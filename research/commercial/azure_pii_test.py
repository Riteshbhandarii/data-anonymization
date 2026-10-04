import os
import time
import json
import requests

# Read secrets from environment variables
ENDPOINT = os.environ["AZURE_LANGUAGE_ENDPOINT"]
KEY = os.environ["AZURE_LANGUAGE_KEY"]
SOURCE_SAS_URL = os.environ["AZURE_SOURCE_SAS_URL"]
OUTPUT_SAS_URL = os.environ["AZURE_OUTPUT_SAS_URL"]

# Azure Document PII API endpoint
submit_url = (
    f"{ENDPOINT.rstrip('/')}"
    "/language/analyze-documents/jobs"
    "?api-version=2024-11-15-preview"
)

# Request body
payload = {
    "displayName": "Azure Document PII test - en_csv_00",
    "analysisInput": {
        "documents": [
            {
                "language": "en-US",
                "id": "en_csv_00",
                "source": {
                    "location": SOURCE_SAS_URL
                },
                "target": {
                    "location": OUTPUT_SAS_URL
                }
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
                "excludeExtractionData": False
            }
        }
    ]
}

# Headers
headers = {
    "Ocp-Apim-Subscription-Key": KEY,
    "Content-Type": "application/json"
}

print("Submitting job...")

response = requests.post(
    submit_url,
    headers=headers,
    json=payload
)

print("Submit status:", response.status_code)

# Stop and show error if submission failed
if response.status_code not in (200, 201, 202):
    print("\nSubmission failed:")
    print(response.text)
    raise SystemExit

# Azure returns the job URL in operation-location
operation_location = response.headers.get("operation-location")

if not operation_location:
    print("\nNo operation-location header returned.")
    print(response.headers)
    raise SystemExit

print("Job submitted successfully.")
print("Polling status...")

# Poll until the async job finishes
while True:
    status_response = requests.get(
        operation_location,
        headers={
            "Ocp-Apim-Subscription-Key": KEY
        }
    )

    if status_response.status_code != 200:
        print("\nPolling failed:")
        print("Status code:", status_response.status_code)
        print(status_response.text)
        raise SystemExit

    result = status_response.json()
    status = result.get("status", "unknown")

    print("Status:", status)

    if status.lower() in ("succeeded", "failed", "cancelled"):
        break

    time.sleep(3)

print("\nFinal response:")
print(json.dumps(result, indent=2, ensure_ascii=False))

# Save the returned JSON locally
output_json = "azure_pii_result.json"

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        indent=2,
        ensure_ascii=False
    )

print(f"\nSaved API result to {output_json}")