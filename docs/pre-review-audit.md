# Pre-review audit

Audit of the implemented pipeline, pending PRs and their combined behavior on
2026-10-13. No PR was merged, no auto-merge was enabled, and no paid/public-model
document request was made. This audit found defects beyond the initially failing
CI checks and added reproductions before fixing them.

| Area | Confirmed defect and resulting behavior | Fix location |
|---|---|---|
| Image sanitization | Dropping alpha exposed invisible email pixels that OCR had not inspected. OCR and output now composite onto the same white background and discard source metadata. A real Tesseract reproduction confirms the old exposure and repaired output. | #52, `redact/image.py` |
| DOCX extraction | Nested tables, content controls, pictures and referenced footnotes/endnotes were omitted. These now enter the appropriate body/image/notes regions. Referenced missing note content fails extraction rather than producing a silently incomplete output. | This PR, `pipeline/extractors.py` |
| XLSX extraction | Comments, sensitive formula expressions and cells beyond incorrect reported dimensions were lost. Comments and expressions are preserved alongside cached values; source dimensions drive cached reads. | This PR, `pipeline/extractors.py` |
| PDF and TIFF | PDF reviewer annotation fields and later TIFF frames were omitted. Both are extracted. | This PR, `pipeline/extractors.py` |
| Extraction accounting | Path aliases could count one physical document twice. Resolved duplicate inputs are now rejected. Nested table pipes are escaped once, preserving original labelled values. | This PR, validation/extraction regressions |
| UI | Metadata-only values could count as covered body labels; changed inputs/settings showed old output, reruns overwrote outputs, and download filenames could carry source names. Coverage is location-aware, old results are hidden, saves are exclusive, and downloads use `anonymized.md`. Save failures remain visible without crashing the preview; the server binds loopback by default. | #50, UI helpers and workflow |
| Detector windows | GLiNER/Privacy Filter and outer document chunks split identifiers without overlap. Dense word tokens could exceed GLiNER's internal limit even below the character limit. Corrected windows overlap and deduplicate spans, and GLiNER respects its word-limit cap. | #53/#54 |
| Dataset scoring | Labelled negative documents dropped false positives from precision; empty datasets/missing language rows and failed declared documents could look complete. Negative and unlabelled inputs are distinct, incomplete selections fail, and corpus hashes are checked before model loading. | #53/#54 |
| Local model boundary | Malformed response envelopes escaped error accounting; invalid spans could inflate benchmark recall. Responses and spans are validated, and failures retain their denominators. | #56 |
| Manual experiments | Rebuilding packs overwrote recorded answers; an unrelated document's own identity was treated as the target's guess rate. Packs require a new directory and controls score against the original target. Unsent requests are `not-run`, distinct from model refusals. Incomplete method comparisons cannot win by testing only an easier dataset. | This PR, `eval/make_pack.py` |
| Study reports | Models, search conditions, alias scopes and languages were combined into one result; unrelated inputs inherited the target's source format. Conditions and actual input format are now recorded separately, and duplicate utility question IDs fail preparation. | This PR, `eval/study.py` |
| Utility accounting | Unrun prompts were labelled attempted, and mixed models could escape rejection through invalid answers. Planned/attempted counts are separate and malformed rows retain model consistency checks. | #55 |
| Installation/checks | App installs did not pin the corpus Faker version, and the full local model set lacked a single dependency manifest. The generator version and tested model packages are pinned; CI also lints commercial research when present. | This PR / #54 |

## Verification

Regression fixtures use actual DOCX/XLSX/PDF/TIFF files, malformed model/HTTP
responses and labelled negative documents. Real Streamlit tests run fictional
text through extraction/redaction with a stub detector: changing selection hides
old results, reruns preserve prior output, downloads have neutral filenames and
save failures remain visible. No model weights or API credentials are needed
for these tests. Existing extraction acceptance thresholds are unchanged.

Historical model tables and aggregate artifacts remain archived. Corrected
windowing and precision can change both accuracy and runtime: rerun the matrix
before presenting old figures as current-code measurements. A green software
check does not replace the manual public-AI study (#44) or real-document labels
(#45).

## Review order and remaining limits

This PR is stacked on #50. Review #50, this core audit, #52, #53, #54 and #56 in
that order. #55 and the research/product PRs are independent. #49 remains a
duplicate superseded by #51. The combined local trial keeps #54's detector
registry and GLiNER pattern helper when resolving overlapping changes; all
regressions from both branches are retained.

The supported-reader audit does not establish coverage for DOCX charts/OLE or
external pictures, XLSX drawings/charts/threaded comments, PPTX master content
or charts, or PDF attachments/XMP/link targets/vector-only lettering. XLSX
comment extraction now needs a nonstreaming workbook view, increasing memory
use for large files. OCR still misses unreadable pixels and depends on language
and orientation. Quasi-identifier privacy benefit and the public model's ability
to re-identify documents remain unmeasured. Keep these as explicit limits in
the final comparison rather than calling the tool universally safe.
