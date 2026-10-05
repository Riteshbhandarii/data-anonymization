# Evaluation of Free and Open-Source Anonymization Tools

## 1. Introduction

As part of the commercial research into existing anonymization solutions, two free/open-source tools were evaluated:

- scrubadub
- ARX Data Anonymization Tool

The purpose of the evaluation was to investigate how suitable these tools are for anonymizing data that may occur in typical SME files.

The test data included English and Finnish synthetic data. Five file formats were considered in the wider evaluation:

- CSV
- DOCX
- PDF
- PPTX
- XLSX

The two tools use fundamentally different approaches. scrubadub focuses on detecting and removing sensitive information from textual data, whereas ARX focuses on privacy-preserving transformation of structured datasets. Therefore, the results should not be interpreted as a direct accuracy competition between the tools.

---

## 2. scrubadub

### 2.1 Tool Overview

scrubadub is an open-source Python library intended to detect and remove personally identifiable information from text. It can be integrated into Python-based data-processing pipelines.

Unlike a complete document-redaction application, scrubadub operates primarily on textual content. Consequently, document formats such as DOCX, PDF, PPTX and XLSX require appropriate extraction logic before their textual content can be processed.

### 2.2 Test Methodology

scrubadub was evaluated using **500 synthetic files** covering five formats.

| Format | English | Finnish | Total |
|---|---:|---:|---:|
| CSV | 50 | 50 | 100 |
| DOCX | 50 | 50 | 100 |
| PDF | 50 | 50 | 100 |
| PPTX | 50 | 50 | 100 |
| XLSX | 50 | 50 | 100 |
| **Total** | **250** | **250** | **500** |

The files contained labelled sensitive entities, allowing the processed output to be compared against ground truth.

In total, the evaluation contained **6,500 labelled sensitive-entity occurrences**.

The evaluation checked whether each labelled sensitive value was still present after the scrubadub workflow. Therefore, the primary metric is described as the **labelled-entity removal rate**, rather than overall anonymization accuracy.

### 2.3 Results

Of the **6,500** labelled entity occurrences:

- **1,149** were removed
- **5,351** remained
- Overall labelled-entity removal rate: **17.68%**

Performance varied considerably between entity categories.

| Entity Category | English Removal | Finnish Removal |
|---|---:|---:|
| Email | 100% | 100% |
| Phone | 52.33% | 59.33% |
| Person | 5.88% | 5.88% |
| Personal ID | 4.00% | 1.60% |
| Address | 0% | 0% |
| Company | 0% | 0% |
| IBAN | 0% | 0% |
| Date | 0% | 0% |
| Invoice | 0% | 0% |
| Vehicle plate | 0% | 0% |

Email addresses were the strongest category, with all labelled email occurrences removed in both English and Finnish data.

Phone-number removal was moderate, at **52.33% for English** and **59.33% for Finnish**.

Default performance was substantially weaker for the other tested categories. In particular, addresses, company names, IBANs, dates, invoice numbers and vehicle registration numbers had a **0% removal rate** in this baseline evaluation.

The experiment also highlighted the importance of document-specific locations. Sensitive information may occur outside the main visible text, for example in:

- PowerPoint speaker notes
- Spreadsheet hidden sheets
- Document metadata

### 2.4 Limitations

The **17.68%** result should not be described as overall scrubadub "accuracy."

The experiment primarily measured whether known labelled sensitive values disappeared from the processed text.

It does not by itself provide a complete assessment of:

- False positives
- Partial redactions
- Semantic correctness
- Overall document anonymization quality

Successful processing of complex document formats also depends on the quality and coverage of the extraction pipeline.

The test used the default/baseline scrubadub workflow. Additional detectors and custom rules could potentially improve performance for entity types that were poorly handled in the baseline.

### 2.5 scrubadub Conclusion

The baseline results suggest that scrubadub should not be relied upon by itself as a complete anonymization solution for heterogeneous SME documents.

It performed particularly well for email addresses and provided moderate coverage for telephone numbers. However, the low overall labelled-entity removal rate and weak performance on many other sensitive categories indicate that additional detectors, custom rules and document-processing logic would be necessary.

scrubadub may therefore be useful as one component within a larger anonymization pipeline rather than as a complete standalone solution.

---

## 3. ARX Data Anonymization Tool

### 3.1 Tool Overview

ARX takes a substantially different approach to anonymization.

Rather than automatically searching unstructured text for names, email addresses or other PII, ARX is designed primarily for **structured/tabular datasets**.

The user defines how attributes should be treated, including:

- Identifying attributes
- Quasi-identifying attributes
- Insensitive attributes

Privacy models such as **k-anonymity** can then be applied.

For this reason, ARX was not evaluated as an automatic PII-detection system.

### 3.2 CSV Methodology

The original CSV files were combined into larger structured datasets to provide a more meaningful k-anonymity experiment.

Two datasets were created:

- English CSV-derived dataset: **100 records**
- Finnish CSV-derived dataset: **100 records**

The attributes were configured as follows:

| Attribute | ARX Classification |
|---|---|
| Name | Identifying |
| Email | Identifying |
| Phone | Identifying |
| Address | Identifying |
| IBAN | Identifying |
| Personal ID | Identifying |
| Vehicle plate | Identifying |
| Company | Quasi-identifying |
| Source file | Insensitive |

The following privacy configuration was used:

| Setting | Configuration |
|---|---|
| Privacy model | 5-anonymity |
| Suppression limit | 0% |
| Search strategy | Optimal |
| Transformation model | Global transformation |

The same configuration was used for English and Finnish data to maintain consistency.

### 3.3 CSV Results

ARX successfully produced an anonymous transformation for both datasets.

Direct identifying attributes were replaced with suppressed values represented by `*`.

Under the tested configuration, company information was also fully generalized/suppressed.

The `source_file` attribute remained available because it had been explicitly classified as insensitive.

The English and Finnish datasets showed the same general behaviour.

This represents strong protection of the selected attributes, but it also demonstrates a significant **privacy-utility trade-off**. Almost all of the useful identifying and quasi-identifying information was lost under this particular configuration.

Importantly, these results should **not** be described as "100% PII detection."

ARX did not automatically identify the sensitive information. The sensitive columns were manually classified before anonymization.

---

## 4. XLSX-Derived ARX Evaluation

### 4.1 Methodology

ARX was also evaluated using structured data extracted from the XLSX test files.

Because ARX is a structured-data anonymization tool rather than a complete Excel workbook-redaction system, worksheet data was first combined and converted into tabular CSV datasets suitable for ARX.

The resulting datasets contained:

- English XLSX-derived dataset: **100 records**
- Finnish XLSX-derived dataset: **100 records**

The relevant attributes were configured as follows:

| Attribute | Classification |
|---|---|
| Name | Identifying |
| Email | Identifying |
| Phone | Identifying |
| IBAN | Identifying |
| Company | Quasi-identifying |
| Date | Quasi-identifying |
| Source file | Insensitive |

The same configuration was used:

- **5-anonymity**
- **0% suppression limit**
- **Optimal search**
- **Global transformation**

### 4.2 XLSX-Derived Results

Both English and Finnish datasets successfully produced anonymous transformations.

In both experiments:

- Name was suppressed
- Email was suppressed
- Phone was suppressed
- IBAN was suppressed
- Company was fully generalized/suppressed
- Date was fully generalized/suppressed
- `source_file` remained available

As with the CSV experiment, the results demonstrate that ARX can provide strong privacy protection when the structure and meaning of the dataset are known in advance.

However, the resulting information loss was substantial.

The XLSX experiment also has an important limitation: ARX was tested on **extracted tabular worksheet data**, not directly on complete XLSX workbooks.

Workbook-specific features such as hidden worksheets and metadata require separate preprocessing and should not be considered covered by this ARX experiment.

---

## 5. DOCX, PDF and PPTX Support in ARX

DOCX, PDF and PPTX were not directly tested with ARX because they do not match the structured tabular workflow used in this evaluation.

This should not be interpreted as a failed ARX test. Instead, it represents a difference in tool scope.

For organizations dealing with heterogeneous office documents, preprocessing or another anonymization system would therefore be necessary before structured data could be processed using ARX.

This contrasts with the scrubadub experiment, where text was extracted from multiple document formats and subsequently processed.

---

## 6. Comparison

| Feature | scrubadub | ARX |
|---|---|---|
| Free/open-source | Yes | Yes |
| Primary approach | PII removal from text | Structured data anonymization |
| Automatic PII detection | Yes, for supported patterns/entities | No |
| CSV | Tested | Tested |
| XLSX | Tested through extraction | Tested using extracted tabular data |
| DOCX | Tested through extraction | Not directly suitable |
| PDF | Tested through extraction | Not directly suitable |
| PPTX | Tested through extraction | Not directly suitable |
| English | Tested | Tested |
| Finnish | Tested | Tested |
| Privacy models such as k-anonymity | No | Yes |
| Requires manual attribute classification | Generally no | Yes |
| Main strength observed | Email and some phone detection | Structured privacy transformation |
| Main weakness observed | Low baseline coverage for many entity types | High information loss and preprocessing/manual configuration |

The comparison demonstrates that the tools solve different problems.

scrubadub is more relevant when the objective is to automatically locate sensitive information within extracted textual content. However, the baseline experiment showed limited coverage beyond email addresses and some telephone numbers.

ARX is better suited to datasets with a known structure and clearly defined columns. It provides formal privacy mechanisms such as k-anonymity, but requires manual data classification and configuration.

In the tested configuration, strong privacy protection came at the expense of substantial data utility.

---

## 7. Overall Conclusion and Recommendation

The evaluation indicates that neither scrubadub nor ARX should be considered a universal anonymization solution for all SME document types.

scrubadub provides a lightweight open-source option for text-based PII removal and can be integrated into Python processing pipelines. However, the baseline evaluation achieved an overall labelled-entity removal rate of only **17.68%**, with strong performance concentrated mainly in email addresses and, to a lesser extent, telephone numbers.

Additional custom detectors and processing logic would be required for broader coverage.

ARX demonstrated a stronger approach for structured tabular datasets. Using **5-anonymity**, the tested English and Finnish CSV- and XLSX-derived datasets could be transformed so that identifying information was suppressed.

However, the tested configuration also removed/generalized the quasi-identifying information, producing substantial information loss. ARX additionally requires users to classify attributes and configure privacy requirements before anonymization.

For heterogeneous SME environments containing CSV, XLSX, DOCX, PDF and PPTX files, a **combined pipeline approach** is therefore more appropriate than relying on either tool alone.

Text-oriented detection/redaction tools can handle extracted document content, while structured privacy tools such as ARX can be applied where tabular data and formal privacy guarantees are required.

The testing also highlights an important requirement for any production anonymization workflow: processing must consider not only visible content but also potentially sensitive information stored in locations such as:

- Metadata
- Hidden spreadsheet sheets
- Presentation speaker notes
