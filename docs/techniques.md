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
