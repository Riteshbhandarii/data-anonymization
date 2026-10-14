# Anonymization product options

Survey for #27, checked 2026-10-13. This is an inventory, not a purchase
recommendation. It covers **nine options: four free local libraries/tools,
three metered cloud APIs and two proprietary platforms**. Free trials and
community access do not make a proprietary service an open-source local tool.
No paid service was called or subscribed to during this survey.

| Category / option | Cost model | Where data is processed | Data handled | Finnish | Setup | Source / project evidence |
|---|---|---|---|---|---|---|
| Local: Presidio | Free, open source | Local Python / containers | Extracted text; image redaction extension | Our configured spaCy/recognizer pipeline is measured in English and Finnish; language-specific setup required | Python, models, extraction/OCR adapters | [Project documentation](https://microsoft.github.io/presidio/), [language configuration](https://github.com/data-privacy-stack/presidio/blob/main/docs/analyzer/languages.md), [#53](https://github.com/Riteshbhandarii/data-anonymization/pull/53) |
| Local: ARX | Free, open source | Local Java GUI/library | Structured tables; generalization, suppression and statistical privacy models | Language-independent table values; requires chosen identifiers, hierarchies and privacy model; no Finnish text NER claim | Java plus manual column/risk configuration | [Official framework](https://arx.deidentifier.org/development/framework/), [source](https://github.com/ARX-deidentifier/arx), [#51](https://github.com/Riteshbhandarii/data-anonymization/pull/51) |
| Local: scrubadub | Free, open source | Local Python | Free text; optional name/address detectors | Finnish regex-style values tested in #51; Finnish name/company support is not established by that configuration | Python; optional detectors need additional models/packages | [Official documentation](https://scrubadub.readthedocs.io/en/stable/), [#51](https://github.com/Riteshbhandarii/data-anonymization/pull/51) |
| Local: DataFog Core | Free, open source | Local Rust/Python/JS/WASM bindings | Pattern detection in text and structured JSON; names from configured JSON fields | Patterns can match Finnish data, but free-text Finnish NER is not documented; tested configuration in #51 | Install binding; document extraction remains separate | [Official source](https://github.com/DataFog/datafog-core), [#51](https://github.com/Riteshbhandarii/data-anonymization/pull/51) |
| Cloud API: Google Sensitive Data Protection | Metered service; free allowances depend on operation | **Google cloud: source data leaves the local machine** | Text, structured records, storage inspection and image inspection/redaction | Finland national-ID detector documented; Finnish person/company quality requires measured evidence | Google project, credentials, API configuration and extraction where needed | [Capabilities](https://docs.cloud.google.com/sensitive-data-protection/docs), [detectors](https://docs.cloud.google.com/sensitive-data-protection/docs/infotypes-reference), [pricing](https://cloud.google.com/sensitive-data-protection/pricing), [#46](https://github.com/Riteshbhandarii/data-anonymization/pull/46) |
| Cloud API: Amazon Comprehend PII | Metered service; advertised free tier subject to terms | **AWS cloud: source data leaves the local machine** | Text PII detection; asynchronous text redaction | PII guide documents English/Spanish; **Finnish PII not supported by this workflow** | AWS credentials; text extraction; S3 for batch redaction | [PII documentation](https://docs.aws.amazon.com/comprehend/latest/dg/pii.html), [pricing](https://aws.amazon.com/comprehend/pricing/) |
| Cloud API: Azure AI Language PII | Metered service; free/student access subject to terms | **Azure cloud: source data leaves the local machine** | Text PII; document redaction tested on DOCX/PDF; our tested endpoint rejected PPTX/XLSX/CSV | Finnish appears in official text/document language tables; four-file representative test in #46, not a general benchmark | Azure Language, storage/SAS for document jobs, polling and output validation | [Language support](https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/language-support), [pricing](https://azure.microsoft.com/en-us/pricing/details/language/), [#46](https://github.com/Riteshbhandarii/data-anonymization/pull/46) |
| Proprietary: Limina | Free trial/community access; commercial terms quoted by vendor | Hosted community API was tested; vendor also offers containers in customer VPC/on-premises | Text and file processing; PDF/XLSX/PPTX/CSV worked in the team's sample, DOCX returned HTTP 500 | Finnish synthetic results in #46; vendor's multilingual claim is not our measured guarantee | API key for hosted trial; vendor deployment for local infrastructure | [Official platform](https://www.getlimina.ai/en), [pricing](https://www.getlimina.ai/en/pricing), [#46](https://github.com/Riteshbhandarii/data-anonymization/pull/46) |
| Proprietary: Tonic Textual | Paid usage / enterprise contract | Tonic Cloud or paid self-hosted deployment | Unstructured text and document/image formats listed by vendor, including DOCX/PDF/PPTX/CSV | Vendor advertises 50+ languages; **Finnish has not been verified or tested here** | Account/API/pipeline setup; own infrastructure for self-hosting | [Official capabilities](https://www.tonic.ai/products/textual), [pricing/deployment](https://www.tonic.ai/pricing) |

The hosted rows require sending source data to a third party. They are research
comparators; this table does not authorize uploading private documents. A
self-hosted commercial deployment is a different route from the hosted trial
and needs its own deployment and data-flow verification.

## Read the evidence correctly

The existing results have different denominators. The full detector matrix in
[#53](https://github.com/Riteshbhandarii/data-anonymization/pull/53) and
[#54](https://github.com/Riteshbhandarii/data-anonymization/pull/54) scores
whole labelled values. The free-tool reports in
[#51](https://github.com/Riteshbhandarii/data-anonymization/pull/51) record
changed text needing review, which is not equivalent to verified removal.
Commercial tests in [#46](https://github.com/Riteshbhandarii/data-anonymization/pull/46)
use much smaller synthetic samples and distinguish any-type coverage from
type-aware detection. ARX's tabular risk/utility measures do not share a
text-span recall denominator. These numbers must not be ranked in one accuracy
column.

Local model alternatives belong to [#29](https://github.com/Riteshbhandarii/data-anonymization/issues/29).
Screenshot/snipping alternatives belong to
[#30](https://github.com/Riteshbhandarii/data-anonymization/issues/30) and
[#52](https://github.com/Riteshbhandarii/data-anonymization/pull/52).
The work plan is in [work-plan.md](work-plan.md).
