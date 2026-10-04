# Anonymization techniques

Grouped by what they actually do, with the failure mode for each.

## Removing or replacing identifiers

| Technique | What it does | Where it breaks |
|---|---|---|
| Suppression / redaction | Delete the value outright | Destroys context, model output quality drops |
| Masking | Partial hide, `****1234` | Fine for display, weak as a data control |
| Pseudonymization | Replace with a token, keep a key | Reversible by design, so still personal data under GDPR. Not anonymization |
| Hashing / tokenization | One-way hash of the identifier | A plain hash of a phone number or a national ID is brute-forceable. Needs salt, and even then remains pseudonymization |
| Surrogate substitution | Swap a real name for a fake but plausible one | Best fit for LLM input. The document stays readable and the model still works |
| Generalization | 34 becomes 30-39, Turku becomes Finland | Loses precision and is rarely sufficient alone |
| Date shifting | Shift all dates in a record by a random offset, preserving intervals | Standard in health data. Breaks cross-record linking |
| Top and bottom coding | Cap outliers, salary above 200k becomes 200k+ | Outliers carry most of the re-identification risk |

## Statistical guarantees, tabular data

- **k-anonymity**, every record is indistinguishable from at least k-1 others on the quasi-identifiers. Tooling: ARX, Amnesia.
- **l-diversity**, fixes the homogeneity attack where all k records share the same sensitive value.
- **t-closeness**, tightens that further against distribution attacks.
- **Differential privacy**, calibrated noise with a formal guarantee and a budget. The only technique with a proof. Costly in accuracy and awkward to apply to documents.
- **Perturbation**, noise without the formal guarantee.
- **Swapping**, shuffle values between records.
- **Aggregation**, release counts rather than rows.
- **Synthetic data**, generate records with matching statistics. Not automatically safe, since generators can memorize and leak.

## Format specific

- Metadata stripping: author, company, license serial, file paths containing usernames, timestamps, GPS
- Flattening: tracked changes, comments, hidden sheets, speaker notes, PDF layers
- True PDF redaction rather than drawing a black rectangle. A black box leaves the text underneath, and this is the most common real-world failure
- OCR, then redact, then re-render, for scanned documents
- Face and plate blurring, EXIF removal, for images
- Voice conversion for audio. A transcript removes the words but the file still carries the voice, which is biometric

## The one that fits sending data to a public model

**Round-trip pseudonymization.** Replace entities with placeholders before the request, send it, then map the placeholders back in the response locally. A real name leaves as `PERSON_1` and the user still gets a usable answer. Implemented in Presidio and LLM Guard.

## Caveats worth stating in any report

- Direct identifiers are the easy part. Re-identification happens through quasi-identifiers. Postcode plus birth date plus gender identifies most individuals. AOL and Netflix were both broken this way.
- Free text is the hardest format and no detector reaches perfect recall. Plan for a residual error rate and state what it is.
- Anonymization is not binary. It is a risk level relative to what an attacker can link against.

## Toolkit map

Which of the techniques above this repository already has, and where each one fits. Status is as of early October 2026; it changes as the open pull requests land.

### Finding identifiers

| Technique | Fits | Cannot do | Status here |
|---|---|---|---|
| Pattern recognizers (regex) | Identifiers with a fixed shape: email, IBAN, phone, plate, invoice reference, identity code | Anything without a fixed shape, such as names. Every country and company has its own formats, so the set is never finished | Presidio's built-in patterns in `main` (#4). Plate, invoice and identity code in progress (#5) |
| Checksum validation | Identifiers with a check character: IBAN, Finnish identity code | Catch a mistyped real value, which a strict checksum rejects | Presidio built-in. Whether to validate is open, see `open-questions.md` |
| Statistical NER (spaCy, Stanza) | Names, organisations and places in running text | Values with no sentence around them, such as table cells and signature blocks. Finnish quality is lower than English and depends on model size | spaCy small models via Presidio in `main` (#4). Large models in progress (#6). Stanza not started (#7) |
| Zero-shot NER (GLiNER) | Entity types described in plain words, including domain-specific ones | Run fast; untested on Finnish here | Not started (#8) |
| Local language model as detector | Identifiers that need context, and quasi-identifiers | Run quickly or deterministically; needs a GPU | Not started (#9) |
| Deny lists | A company's own known names: customers, products, projects | Find anything not on the list | Not built |

### Transforming what was found

| Technique | Fits | Cannot do | Status here |
|---|---|---|---|
| Suppression / replacement with a type label | Any data; the safe default | Keep the document useful when too much is removed | In review (#3, `redact/`) |
| Consistent pseudonyms | Model input where relationships between people matter | Stop linkage: a consistent token across documents lets two documents be tied to the same person | In review (#3, alias map with explicit document or corpus scope) |
| Surrogate values (fake names, numbers) | Model input that must stay readable | Guarantee a fake value never matches a real one | Not built. Faker is used only to generate the test corpus |
| Masking | Display | Act as a data control | Not built |
| Generalization, date shifting, top and bottom coding | Tabular data | Help free text | Not built |
| k-anonymity, l-diversity, t-closeness | Tabular exports with quasi-identifier columns | Apply to documents | Not built; ARX and Amnesia are external options |
| Differential privacy | Aggregate statistics | Apply to individual documents | Not planned |

### Format handling

| Technique | Fits | Status here |
|---|---|---|
| Reading hidden content: document properties, speaker notes, hidden sheets, headers, footers, comments, tracked changes | Office files | In review (#3) |
| OCR for scans and embedded images | Scanned PDF, images inside documents | In review (#3), options compared under #31 |
| Rebuilding a redacted file in its original format | Users who need to keep editing the document | Not built; the pipeline outputs Markdown text. See the output format question in `open-questions.md` |
