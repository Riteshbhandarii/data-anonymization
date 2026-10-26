# Options map

[Docs index](README.md) › RQ1 · RQ4

Which options exist for anonymizing each document format before it goes to a public AI model, and which fits when? This is the decision guide for small and medium businesses. It draws on the project's measurements at evidence snapshot `e148240` and the dated 2026-10-19 local reruns linked below. No tool here has been shown to make arbitrary documents safe to send. Choose the smallest necessary input, process locally, then review the actual output.

## Key result

- Best local detector: `combined` finds 1,849/1,919 values on 140 synthetic files, 4,269/5,112 on TAB and 80/100 on Turku.
- A local LLM run on the original text and merged with `combined` hides 146/146 values, against 139/146 for `combined` alone, and 58 vs 26 of 71 contextual items such as licence numbers and code names ([contextual-llm](contextual-llm.md)). Run on already masked text it adds about one.
- Commercial samples are small: Azure 35/48 any-type, Google 55/98, Limina 69/74 on 8 of 10 submitted files.
- For screenshots, GLiNER hides 422/467 readable values and rules 408/467. Pixelation and blur are not redaction.
- Email, logs/code, CAD, audio/video and scanned PDFs are NOT TESTED; those rows are desk research.

## How to read the evidence

| Evidence family | Denominator and meaning | Source |
|---|---|---|
| Current seven-method matrix | 885 documents per method; 11,070 labelled values per method. Whole-value accepted-type coverage; partial spans fail. Datasets retain separate denominators. | [Report](dataset-audit-runs.md), [aggregate JSON](../eval/baselines/dataset-audit-matrix.json) |
| Current local LLM comparison | 14 short synthetic documents, 146 body labels; typed-overlap precision is a different metric from matrix precision. | [Comparison](local-llm-comparison.md) |
| Extraction acceptance | 70 generated documents, 960 labels; 946 returned, 14 OCR misses. This measures extraction before detection. | [Audit](archive/pre-review-audit.md), [diagnosis](residual-misses.md) |
| Earlier screenshot study | 40 PNGs, 480 planted values, 467 readable before redaction. Hidden/readable and hidden/planted are distinct. This study predates the audit and excludes combined. | [Screenshot report](screenshot-redaction.md) |
| Earlier OCR study | 20 PNGs, 240 planted values, paired clean/half-resolution variants; Windows CPU. OCR accuracy is not redaction accuracy. | [OCR report](ocr-survey.md) |
| Commercial samples | Azure: 4 documents/48 labels. Google: 10/98. Limina: 8 successful/74 body labels, out of 10 submitted. Earlier team tests, not rerun here. | [Azure](commercial/azure_document_pii_redaction.md), [Google](commercial/google_cloud_dlp.md), [Limina](commercial/limina_anonymization.md) |
| Free-tool samples | Each report totals 6,500 labels: 100 not extracted and 6,400 extractable. Counts mean changed text needing review, not verified removal. | [scrubadub CSV](../eval/free_tools/scrubadub/results/format_language_summary_v2.csv), [DataFog CSV](../eval/free_tools/datafog/results/format_language_summary_v2.csv) |

These are separate studies. The measured-result cells below identify their
study; their numbers are not a common ranking. Matrix lower-bound precision
counts overlap with any annotation. Incomplete annotations mean an unlabelled
detection is not automatically a false positive. Archived pre-audit detector
results are not substituted for the current matrix.

## Part A: choose by format

All pipeline results below concern extracted Markdown, unless a row explicitly
says image redaction or a vendor-returned file. The original Office/PDF source
is not sanitized by exporting Markdown.

| Format | Options that handle it | What measurements show | Main risk | Recommendation |
|---|---|---|---|---|
| DOCX | Local extractor + rules/GLiNER/combined/Privacy Filter/GLiNER2 or local LLM; Azure native document PII; Google inspection; Tonic vendor route | Current combined: 380/400 values on 20 synthetic DOCX. Azure: 17/24 any-type full coverage on 2 DOCX. Limina's 2 corpus DOCX and minimal smoke DOCX failed HTTP 500. Sources: [matrix](dataset-audit-runs.md), commercial reports above. | Comments, revisions, headers, properties, embedded pictures; charts/OLE/external pictures unsupported locally. | For a text question, extract locally, run combined, inspect source against output. Do not upload the original DOCX. For same-format output, evaluate a separate redaction tool and hidden-content coverage. |
| XLSX | Local extractor + text detector; ARX on a selected table/export; Limina; Google inspection; Tonic vendor route | Combined: 252/260 values on 20 synthetic workbooks. Limina: 16/16 body labels on 2 workbooks; hidden-content observations are outside that denominator. Azure tested native endpoint rejected XLSX. | Hidden sheets, comments, formula expressions, cell dimensions, external references, charts/drawings; row linkage. | Export only necessary columns/rows; use ARX when quasi-identifiers need generalization. Review formulas and hidden sheets before selecting text. |
| PPTX | Local extractor + detector; Limina; Google inspection; Tonic vendor route | Combined: 292/300 values on 20 synthetic presentations. Limina: 15/16 any-type body coverage on 2 presentations. Azure native endpoint rejected PPTX. | Speaker notes, metadata, images/logos, master content and charts. | Use reviewed text from relevant slides. Inspect slide pixels and notes; never treat clean extracted text as a sanitized deck. |
| PDF text | Local PyMuPDF extraction + detector; applied PyMuPDF/Acrobat redaction for a PDF deliverable; Azure/Limina; Google inspection | Combined PDF aggregate: 295/299 values on 20 synthetic PDFs, including OCR image regions; no separate pure-text PDF score. Azure: 18/24 any-type coverage on 2 PDFs; Limina 22/24 on 2. | Annotations, text under rectangles, images, attachments/XMP/link targets/vector lettering. | Prefer reviewed text. For PDF delivery apply content-removing redactions, save a new file, check copy/paste and rendered pages. |
| Scanned PDF | Tesseract/PaddleOCR/EasyOCR + detector + pixel redaction/rebuild; cloud OCR with authorized processing; Acrobat OCR | NOT TESTED as a dedicated full-page scanned-PDF corpus. Embedded-image PDF/OCR evidence is narrower; see [OCR report](ocr-survey.md). | OCR substitutions, orientation, signatures, stamps, page regions never extracted. | Compare OCR with every page. Use opaque pixel removal and rebuild; unreadable or unchecked regions block sending. |
| Images/screenshots | Local image module; Presidio Image Redactor; manual solid-fill tools; PyMuPDF after PDF conversion; authorized cloud image services | Earlier 40-PNG study: GLiNER hides 422/467 readable values, rules 408/467. Combined was NOT RUN in that study. Current small diagnosis is separately scoped in [residual misses](residual-misses.md). | Logos, faces, signatures, QR codes, window titles, pixels OCR misreads; blur/pixelation. | Crop to necessary content, use solid fills, export a fresh flattened raster, inspect visually. Pixelation and blur are not redaction. |
| CSV/database export | ARX; local text detector for fields; DataFog patterns; scrubadub; Google structured records; Limina CSV | Combined: 171/180 values on 20 synthetic CSVs. Free-tool changed-text measures are separate. Database connectors and relational export workflows NOT TESTED. | Quasi-identifier combinations, stable keys, joins, rare rows; names absent from regex detections. | Remove unnecessary fields first. Model linkage risk and use generalization/suppression for tables; keep any pseudonym map local. |
| Email | Local Python MIME parser/Apache Tika + reviewed text detector; recurse into attachments | NOT TESTED. [Python email parser](https://docs.python.org/3/library/email.parser.html) documents MIME parsing; [Apache Tika](https://tika.apache.org/docs/4.1.x/formats.html) lists email formats. Neither is an anonymizer. | From/To/CC, Message-ID, Received/IP headers, HTML, signatures, quoted threads, attachment metadata. | Export the minimum relevant text, remove headers/history, inspect every attachment separately. No native email support is established for our pipeline. |
| Logs/code | Local secret scanner such as Gitleaks plus rules/Privacy Filter/NER; manual domain review | NOT TESTED. [Gitleaks repository](https://github.com/gitleaks/gitleaks) documents secret detection in Git/files/stdin, not complete anonymization. | Tokens, paths/usernames, hostnames, customer/project names, IPs, proprietary source or architecture. | Run secret scanning and identifier review locally; use a minimal synthetic reproducer. Keep confidential code/design local even after identifier removal. |
| CAD | Local CAD inspection, property/title-block/BOM review, approved image/text export | NOT TESTED. [FreeCAD official export documentation](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Import_Export_Preferences.md) describes CAD export and author/company fields; it is not an anonymization workflow. | Geometry itself, dimensions, part numbers, assemblies, supplier BOM, title blocks and metadata. | Do not send confidential designs. A reviewed generic sketch or synthetic dimensions may answer the question without disclosing the design. |
| Audio/video | Local Whisper transcript + text detector; local FFmpeg stream/metadata control; manual visual review | NOT TESTED. [Whisper](https://github.com/openai/whisper) and [FFmpeg](https://ffmpeg.org/ffmpeg.html) document transcription and stream handling, not anonymization; Tonic also advertises an untested commercial audio route. Finnish quality NOT TESTED here. | Voice/speaker identity, spoken context, faces, slides, subtitles, embedded streams and metadata. | Prefer a reviewed minimal transcript. Removing words does not sanitize the voice or video; do not send original recordings without a separate approved workflow. |

Format counts in the current matrix are 20 source files per listed format;
PNG includes paired resolution variants (40 files). For unsupported reader
content, use the [complete table](residual-misses.md), not just a visible-page
check. The untested rows are desk research, not project capabilities.

## Part B: choose by option

“Local” means content remains on the machine in the described configuration.
Downloads for initial installation are separate from document processing.
“NOT RUN” means there is no project measurement; vendor support does not fill
that gap. Hosted variants explicitly send data off the machine.

### Products and free tools

| Option | Free/paid | Local/cloud: does data leave? | Formats | Finnish support | Measured result, sample and source | GOOD | BAD | WHEN TO USE | WHEN NOT TO |
|---|---|---|---|---|---|---|---|---|---|
| Presidio | Free/open source | Local analyzer; remote recognizers require separate review | Text; image extension separately below | Our configured EN/FI spaCy models and recognizers measured | See basic/rules rows below; [inventory](#appendix-product-inventory-and-sources), [official docs](https://microsoft.github.io/presidio/) | Configurable recognizers and operators | Not an Office/PDF reader; default models miss entities | Local detector component with format extraction | As a complete document safety guarantee |
| ARX | Free/open source | Local Java | Structured tables; prepared CSV/XLSX inputs | Language-independent values; no Finnish NER claim | Screenshots only; no comparable labelled recall result. [Artifacts](../eval/free_tools/arx/screenshots/), [official framework](https://arx.deidentifier.org/development/framework/) | Generalization, suppression and privacy models | Manual schema/hierarchy/risk choices; weak fit for prose | Tabular quasi-identifiers and explicit release models | Free-text documents or automatic safe-to-paste decisions |
| scrubadub | Free/open source | Local | Extracted text | Tested pattern values; Finnish people/companies unestablished | 1,049/6,400 extractable values changed, 100/6,500 not extracted; changed, unverified. [CSV](../eval/free_tools/scrubadub/results/format_language_summary_v2.csv) | Simple pattern scrubbing | Tested config changes no names/companies; change is not verified removal | Narrow known-format fields plus manual checks | General Finnish document anonymization |
| DataFog Core | Free/open source | Local bindings | Text/JSON; Office extraction external | Patterns tested; Finnish free-text NER unestablished | 2,769/6,400 extractable values changed; 100/6,500 not extracted. Addresses: postal-code replacement only, changed, unverified. [CSV](../eval/free_tools/datafog/results/format_language_summary_v2.csv), [manual address review](../eval/free_tools/datafog/results/datafog_address_manual_validation.csv) | Local pattern processing | No people/companies changed in tested config; address remains identifiable | Pattern layer with explicit field policies | Treating changed addresses as removed addresses |
| Google Sensitive Data Protection | Metered cloud | Cloud: data leaves the machine | Text, records, storage inspection, image redaction | Finland ID documented; sampled EN/FI quality only | 55/98 full any-type detection, 53/98 type-aware; 10 documents. [Team report](commercial/google_cloud_dlp.md), [official capabilities](https://docs.cloud.google.com/sensitive-data-protection/docs) | Configurable infoTypes; structured APIs | Sample default config missed all tested IBANs/IDs/plates/invoices; file reconstruction not measured | Existing authorized cloud workflow with configured detectors | Local-only processing or assuming default coverage |
| Amazon Comprehend PII | Metered cloud | AWS cloud: data leaves the machine; S3 for batch | Text; extracted documents | PII workflow English/Spanish, not Finnish | NOT RUN. [Official PII guide](https://docs.aws.amazon.com/comprehend/latest/dg/pii.html) | Managed detection/redaction workflow | Requires extraction; no Finnish PII support in documented workflow | Authorized English/Spanish text processing | Finnish or local-only source data |
| Azure AI Language PII | Metered cloud | Azure cloud: data leaves the machine; storage for document jobs | Text; tested native DOCX/PDF, endpoint also TXT | Finnish listed and sampled | 35/48 any-type full coverage; 33/48 type-aware, 4 documents; 1 partial. [Team report](commercial/azure_document_pii_redaction.md), [official language table](https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/language-support) | Returned DOCX/PDF and entity JSON | Native tested endpoint rejects XLSX/PPTX/CSV; Finnish IDs inconsistent | Authorized DOCX/PDF workflow needing preserved format | Local-only data or complete Office coverage |
| Limina | Proprietary; trial/community, commercial terms | Tested hosted API: data leaves the machine. Vendor offers customer VPC/on-prem deployment; not tested | Sample PDF/XLSX/PPTX/CSV; DOCX failed | FI sample measured; not general support validation | 69/74 any-type full coverage, 62/74 type-aware across 8 successful files; 2/10 corpus files failed. [Team report](commercial/limina_anonymization.md), [vendor](https://www.getlimina.ai/en) | Returns processed files; hidden-content detections observed | DOCX HTTP 500; partial phones; hosted disclosure | Evaluate authorized same-format workflows and local deployment terms | Reliable DOCX processing without revalidation; local-only via hosted API |
| Tonic Textual | Paid/proprietary | Tonic Cloud: data leaves the machine; paid self-hosting offered, untested | Vendor lists text/documents/images/audio | Finnish unverified | NOT RUN. [Vendor capabilities](https://www.tonic.ai/products/textual), [deployment/pricing](https://www.tonic.ai/pricing) | Broad vendor format route | No project accuracy or Finnish evidence; contract/setup | Procurement evaluation with data-flow and format tests | Assuming a vendor language count proves Finnish quality |

### Our detector configurations and local LLMs

Matrix cells below show **only synthetic all-location coverage** for a compact
common reference; public-text dataset rows remain separate in the linked matrix.
This does not rank commercial/free-tool studies against that corpus.

| Option | Free/paid | Local/cloud: does data leave? | Formats | Finnish support | Measured result, sample and source | GOOD | BAD | WHEN TO USE | WHEN NOT TO |
|---|---|---|---|---|---|---|---|---|---|
| basic | Free | Local | Extracted text via all supported readers | spaCy small FI | 1,178/1,919 values, 140 files; [current matrix](dataset-audit-runs.md) | Cheap baseline | No project invoice/plate/identity patterns | Benchmark reference or narrow common identifiers | Default safe-to-send policy |
| rules | Free | Local | Extracted text | Configured FI spaCy and patterns | 1,536/1,919, 140 files; [matrix](dataset-audit-runs.md) | Fast; structured identifiers complement NER | Whole addresses/names missed; hours mistaken for dates | Local structured-value layer with review | Unreviewed prose or utility-sensitive numeric tasks |
| rules-lg | Free | Local | Extracted text | Finnish large spaCy model | 1,615/1,919, 140 files; [matrix](dataset-audit-runs.md) | Better Finnish names than small spaCy in these selections | More weights; incomplete addresses/companies | CPU alternative to small-model rules | Assuming larger NER closes all gaps |
| GLiNER + patterns | Free cached weights | Local | Extracted text | Measured FI despite no separate FI model-card claim | 1,725/1,919, 140 files; Turku 80/100 in 18 texts; [matrix](dataset-audit-runs.md) | Names/addresses complement patterns | More compute; IBAN weakness without rules; unlabelled detections | Semantic detector alongside patterns | As OCR or visual logo detection |
| combined | Free | Local | Extracted text; image module can use it | FI measured | 1,849/1,919, 140 files; separate TAB 4,269/5,112, Turku 80/100; [matrix](dataset-audit-runs.md) | Complementary detections; current local starting point | Still misses company names and OCR errors; over-redacts; no privacy proof | Reviewed local text preparation | Automatic approval to disclose a whole document |
| privacy-filter + patterns | Free open weights | Local | Extracted text | FI ai4privacy measured; Turku mismatch | 1,582/1,919, 140 files; separate Turku 0/100 in 18 texts; [matrix](dataset-audit-runs.md) | Personal-data taxonomy; high lower-bound precision on selected text | No organization category; taxonomy/domain mismatch | Evaluate personal PII under an explicit label policy | Company confidentiality or assuming benchmark marketing transfers to FI NER |
| GLiNER2 + patterns | Free cached weights | Local | Extracted text | FI absent from listed training languages; measured here | 1,809/1,919, 140 files; ai4privacy FI 1,636/1,953 in 300 rows; [matrix](dataset-audit-runs.md) | Alternative multilingual PII detector | Boundary/honorific mismatch; not uniformly strongest | Domain-specific comparison against combined | Swapping in without per-type checks |
| Qwen 3.5 9B alone | Free cached local weights | Local LM Studio loopback | Text windows | FI measured on short synthetic text | 14 documents: 144/146 hidden by any detection (typed 94/146); contextual prompt 57/71 contextual items, 2/46 decoys. [Contextual test](contextual-llm.md) | Finds companies and context-dependent values rules miss | Mislabels types; skips names when told they are masked; about 5.6 s per short document | Alongside `combined`, merged | Replacing `combined`: misses some names and emails alone |
| Gemma 4 E4B alone | Free cached local weights | Local LM Studio loopback | Text windows | FI weaker than EN here | 14 documents: 133/146 by any detection (typed 111/146); 12 Finnish names and companies missed. [Contextual test](contextual-llm.md) | Smaller and faster than Qwen | Weak on Finnish names | Comparison only | Finnish documents without review |
| combined → Qwen (LLM on masked text) | Free cached weights | Local; base process exits before LLM load | Base spans masked before inference | FI measured | 14 documents: 140/146 by any detection; contextual 47/71 with 22/46 decoys. [Contextual test](contextual-llm.md) | Keeps base spans | Masking removes the context the LLM needs; Qwen sometimes loops to its token limit | Not recommended; use merged | — |
| **combined + Qwen, merged** | Free cached weights | Local; run one after the other, union of spans | Same original text for both | FI measured | 14 documents: **146/146**; contextual corpus **58/71** contextual items and 44/44 standard identifiers. [Contextual test](contextual-llm.md) | Covers what each misses: formats from rules, context from the LLM | Inherits `combined`'s over-masking (22/46 decoys); slower on long documents | Documents with reference numbers, code names or company context | Fast bulk processing of long exports on a laptop |

Local processing still has a runtime cost. The current combined/MPS pack
preparation needed 1,178.2 detection seconds for 17 long real-public exports
(2,040,231 characters), with 32.4 extraction seconds; no real-text recall is
available for those files. See [the separate timing record](public-ai-pack.md).
This workload is not ranked against short-template LLM or earlier OCR timings.

The current nine-question-per-language utility rerun found no added benefit
from Gemma final pass: the two methods produced identical corresponding prompts
and answers. Combined raw/redacted/pseudonymized exact-answer counts were EN
7/9, 5/9, 4/9 and FI 9/9, 1/9, 6/9. Counting only answers the sanitized text
can support, redaction drops to 0/9 and pseudonyms to 3/9 in both languages:
masked hours let guesses score. See [utility-impact.md](utility-impact.md#evidence-supported-answers)
and the [paired comparison](../eval/baselines/final-evidence-utility-comparison.json).

### OCR options: extraction, not anonymization

| Option | Free/paid | Local/cloud: does data leave? | Formats | Finnish support | Measured result, sample and source | GOOD | BAD | WHEN TO USE | WHEN NOT TO |
|---|---|---|---|---|---|---|---|---|---|
| Tesseract | Free/open source | Local | Raster images; rendered PDF/image regions | `fin`, measured with `eng+fin` | Earlier 20 PNGs: 229/240 exact labels; [OCR report](ocr-survey.md) | Fast baseline; simple local install | Single-character errors leak identifiers | Default OCR plus page-by-page review | As a redactor or unreadable-pixel guarantee |
| PaddleOCR mobile | Free/open source | Local cached models | Raster images | Finnish-capable Latin recognizer | Earlier same 20 PNGs: 228/240; FI 115/120; [OCR report](ocr-survey.md) | Alternative for Finnish printed text | Slower on measured CPU; initialization/runtime configuration matters | Second OCR opinion on difficult regions | Assuming language support implies perfect output |
| EasyOCR `sv,en` | Free/open source | Local cached models | Raster images | No `fi`; tested Latin approximation | Earlier same 20 PNGs: 215/240; [OCR report](ocr-survey.md) | Local alternate reader | Not an actual Finnish-language configuration | Optional comparison where installed | Claiming verified native Finnish support |
| Google Cloud Vision | Metered cloud | Cloud: images leave the machine | Images/PDF OCR workflows | Finnish listed | NOT RUN. [Official language table](https://docs.cloud.google.com/vision/docs/languages), [survey](ocr-survey.md) | Managed Finnish OCR | Hosted disclosure; no project accuracy | Only approved cloud inputs | Local-only data or redaction by OCR alone |
| Azure Vision Read | Metered cloud | Cloud: images leave the machine | Images/document OCR | Finnish printed text; Finnish handwriting not listed | NOT RUN. [Official table](https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/language-support), [survey](ocr-survey.md) | Printed Finnish support | No project measurement; cloud | Approved OCR backend | Finnish handwriting guarantee or local-only data |
| Amazon Textract | Metered cloud | Cloud: files leave the machine | Images/PDF/document extraction | Finnish not in documented languages | NOT RUN. [Official limits](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html) | Managed document extraction | No Finnish evidence/support in cited language list | Approved supported-language workflow | Finnish/local-only workflow |

### Screenshot and PDF redaction tools

Earlier image figures below share 40 PNGs and 467 OCR-readable labels. They
are archived study results, not a post-audit rerun or a combined detector test.

| Option | Free/paid | Local/cloud: does data leave? | Formats | Finnish support | Measured result, sample and source | GOOD | BAD | WHEN TO USE | WHEN NOT TO |
|---|---|---|---|---|---|---|---|---|---|
| Our `redact/image.py` | Free/MIT | Local | Images, fresh PNG output | `eng+fin` plus configured FI detector | Earlier rules: 408/467 hidden, 408/480 planted; GLiNER: 422/467, 422/480. [Report](screenshot-redaction.md) | Solid fills; fresh pixels; alpha handling audited | No logo/face/signature/QR recognition; OCR bottleneck | Reviewed screenshots with manual additional boxes | Automatic clearance of visual business content |
| Presidio Image Redactor | Free/MIT | Local with Tesseract; optional Azure OCR sends images off machine | Images | Custom FI analyzer + OCR required | Earlier basic 359/467 hidden; rules 407/467; [report](screenshot-redaction.md) | Existing OCR-to-box pipeline | Rules non-label words blacked 9.3%; no logos | Configured local image pipeline | Unchecked English defaults on Finnish images |
| Windows Snipping Tool Text Actions | Bundled/free | OCR locality unverified in cited source | Screenshots | Unverified | NOT RUN. [Microsoft guide](https://support.microsoft.com/en-au/windows/apps/use-snipping-tool-to-capture-screenshots) | Quick email/phone selection | Not broad PII detection; saved-pixel behavior needs validation | Manual assisted editing with output inspection | Assuming Quick Redact catches names/logos or proves local processing |
| macOS Screenshot/Markup | Bundled/free | Local manual workflow | Screenshots/images | Manual, language-independent | NOT RUN. [Apple PDF redaction guide](https://support.apple.com/en-ie/guide/preview/prvw11580/11.0/mac/27) covers Preview; screenshot fill/export remains manual | Easy manual filled shapes; Preview also offers applied PDF redaction | Operator can choose translucent shapes; original layers/save path need checking | Solid fill and new flattened export | Drawing an outline or shipping editable markup |
| ShareX | Free/GPL | Local editing; optional upload actions send data off machine | Screenshots/images | Manual; OCR separate | NOT RUN. [Official repo](https://github.com/ShareX/ShareX) | Manual filled rectangles | Blur/pixelate options are unsafe substitutes; upload tasks need disabling | Manual opaque rectangles, local save | Blur/pixelation or automatic upload workflow |
| Greenshot | Free/open source Windows; platform terms vary | Local editor; plugins/exports require review | Screenshots | Manual; OCR feature status unverified | NOT RUN. [Repo](https://github.com/greenshot/greenshot) | Manual annotation | Obfuscation/pixelation is not removal | Only verified opaque fill/export workflow | Treating OCR pixelation as redaction |
| Flameshot | Free/GPL | Local editor; upload actions can disclose | Screenshots | Manual | NOT RUN. [Official privacy guide](https://flameshot.org/docs/advanced/protecting-your-privacy/) | Cross-platform manual rectangles | Pixelation is not redaction; export choice matters | Solid fill saved locally | Pixelate tool or hosted upload |
| Adobe Acrobat Pro / Premium / Studio | Paid | Local desktop redaction; cloud features require separate data-flow review | PDF; image conversion and OCR route | FI OCR/detection unverified here | NOT RUN. [Adobe apply/sanitize tutorial](https://experienceleague.adobe.com/en/docs/document-cloud-learn/acrobat-learning/advanced-tasks/protect/redact) | Applied content removal and hidden-information review | Licence; OCR/manual selection can miss content | Same-format PDF deliverable with apply/save/recheck | Black overlay without Apply Redactions |
| PyMuPDF | AGPL or paid commercial licence | Local library | PDF; rendered image regions | Depends on external OCR/detector | Redaction product NOT RUN; extractor used in matrix. [Official redaction API](https://pymupdf.readthedocs.io/en/latest/page.html#Page.apply_redactions) | Removes content when applied | Programmer supplies correct areas/settings; licence constraints | Programmatic verified PDF removal | Assuming adding annotations alone removes content |
| Google image redaction | Metered cloud | Cloud: image data leaves the machine | Images | Image OCR FI unverified here | NOT RUN. [Official guide](https://docs.cloud.google.com/sensitive-data-protection/docs/concepts-image-redaction) | Opaque rectangles from infoTypes | Cloud disclosure and OCR/type misses | Authorized cloud image workflow | Local-only images or visual-context guarantee |
| Private AI image route | Commercial | Vendor container/customer environment; deployment/telemetry verify | Vendor text/image/face route | Image Finnish unverified | NOT RUN; vendor behavior unverified in [survey](screenshot-redaction.md), [vendor](https://private-ai.com/) | Potential container route | Blur claim does not establish redaction; no measured evidence | Procurement evaluation after pixel-removal validation | Assuming face blur removes identity or sending unreviewed source |

Azure Language and Amazon Comprehend return text spans/masked text, rather than
drawing screenshot boxes. Their OCR composites appear in the product/OCR rows;
using Azure Read or Textract still sends the image off the machine. No cloud
option was called during this 2026-10-19 work.

## Part C: decision flow before pasting

**Paste the cleaned text, never upload the original file.** The pipeline, UI
and manual public-AI pack now omit `Document metadata` sections by default.
For a justified comparison, explicitly enable `include_metadata=True`, the UI's
**Keep document metadata**, or the pack's `--include-metadata` flag. This exports
reviewed text; it does not sanitize the original Office/PDF container. Follow
the [clean-text cookbook](clean-text-cookbook.md) for the exact workflow.

1. **Decide whether disclosure is allowed.** Identify the owner and purpose.
   Personal data and confidential business information are separate gates.
   A design, source file, price list or strategy can remain confidential after
   names disappear. If disclosure is prohibited or unclear, keep it local and
   use a fictional example instead.
2. **Reduce the input.** Copy only the paragraph, fields or synthetic example
   needed for the question. Remove attachments, unrelated history, identifiers
   and secrets that the task does not need.
3. **Check the actual format.** Inspect hidden sheets, comments, revisions,
   notes, metadata and embedded objects. Use Part A. An unsupported object or
   unreadable page means the input has not passed review.
4. **Choose a local method.** For supported prose start with extraction plus
   combined; for structured quasi-identifiers consider ARX and field reduction.
   For scans use local OCR; for screenshots use solid pixel removal and manual
   boxes. For documents with reference numbers, code names or company context,
   also run a local LLM on the same text and merge its detections.
5. **Inspect the saved output against the source.** Check whole names,
   addresses, account digits, logos, signatures, faces, QR codes and indirect
   clues. Verify PDF copy/paste and fresh flattened image pixels. Blur and
   pixelation fail this gate. Do not send an unchecked original file.
6. **Check usefulness and linkage.** Verify the numbers and relationships
   required for the task remain correct. Keep alias keys local; consistent
   aliases and rare combinations can link records. If the remaining context
   identifies a person/company, reduce it further or stop.
7. **Make the release decision.** Send only the reviewed minimal output through
   the organization's approved AI route. A cloud anonymizer also receives the
   source, so it needs its own authorization. If confidentiality, personal-data
   risk, extraction completeness or output review is unresolved, do not send.
   Record the tool/configuration and review decision; the measurements here
   are evidence for that decision, not automatic permission.

## Appendix: product inventory and sources

Survey checked 2026-10-13. This is an inventory, not a purchase
recommendation. It covers **nine options: four free local libraries/tools,
three metered cloud APIs and two proprietary platforms**. Free trials and
community access do not make a proprietary service an open-source local tool.
No paid service was called or subscribed to during this survey.

| Category / option | Cost model | Where data is processed | Data handled | Finnish | Setup | Source / project evidence |
|---|---|---|---|---|---|---|
| Local: Presidio | Free, open source | Local Python / containers | Extracted text; image redaction extension | Our configured spaCy/recognizer pipeline is measured in English and Finnish; language-specific setup required | Python, models, extraction/OCR adapters | [Project documentation](https://microsoft.github.io/presidio/), [language configuration](https://github.com/data-privacy-stack/presidio/blob/main/docs/analyzer/languages.md), [matrix](dataset-audit-runs.md) |
| Local: ARX | Free, open source | Local Java GUI/library | Structured tables; generalization, suppression and statistical privacy models | Language-independent table values; requires chosen identifiers, hierarchies and privacy model; no Finnish text NER claim | Java plus manual column/risk configuration | [Official framework](https://arx.deidentifier.org/development/framework/), [source](https://github.com/ARX-deidentifier/arx), [free-tool results](../eval/free_tools/) |
| Local: scrubadub | Free, open source | Local Python | Free text; optional name/address detectors | Finnish regex-style values tested in the free-tool runs; Finnish name/company support is not established by that configuration | Python; optional detectors need additional models/packages | [Official documentation](https://scrubadub.readthedocs.io/en/stable/), [free-tool results](../eval/free_tools/) |
| Local: DataFog Core | Free, open source | Local Rust/Python/JS/WASM bindings | Pattern detection in text and structured JSON; names from configured JSON fields | Patterns can match Finnish data, but free-text Finnish NER is not documented; tested configuration in the free-tool runs | Install binding; document extraction remains separate | [Official source](https://github.com/DataFog/datafog-core), [free-tool results](../eval/free_tools/) |
| Cloud API: Google Sensitive Data Protection | Metered service; free allowances depend on operation | **Google cloud: source data leaves the local machine** | Text, structured records, storage inspection and image inspection/redaction | Finland national-ID detector documented; Finnish person/company quality requires measured evidence | Google project, credentials, API configuration and extraction where needed | [Capabilities](https://docs.cloud.google.com/sensitive-data-protection/docs), [detectors](https://docs.cloud.google.com/sensitive-data-protection/docs/infotypes-reference), [pricing](https://cloud.google.com/sensitive-data-protection/pricing), [commercial reports](#products-and-free-tools) |
| Cloud API: Amazon Comprehend PII | Metered service; advertised free tier subject to terms | **AWS cloud: source data leaves the local machine** | Text PII detection; asynchronous text redaction | PII guide documents English/Spanish; **Finnish PII not supported by this workflow** | AWS credentials; text extraction; S3 for batch redaction | [PII documentation](https://docs.aws.amazon.com/comprehend/latest/dg/pii.html), [pricing](https://aws.amazon.com/comprehend/pricing/) |
| Cloud API: Azure AI Language PII | Metered service; free/student access subject to terms | **Azure cloud: source data leaves the local machine** | Text PII; document redaction tested on DOCX/PDF; our tested endpoint rejected PPTX/XLSX/CSV | Finnish appears in official text/document language tables; four-file representative test, not a general benchmark | Azure Language, storage/SAS for document jobs, polling and output validation | [Language support](https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/language-support), [pricing](https://azure.microsoft.com/en-us/pricing/details/language/), [commercial reports](#products-and-free-tools) |
| Proprietary: Limina | Free trial/community access; commercial terms quoted by vendor | Hosted community API was tested; vendor also offers containers in customer VPC/on-premises | Text and file processing; PDF/XLSX/PPTX/CSV worked in the team's sample, DOCX returned HTTP 500 | Finnish synthetic results in the commercial report; vendor's multilingual claim is not our measured guarantee | API key for hosted trial; vendor deployment for local infrastructure | [Official platform](https://www.getlimina.ai/en), [pricing](https://www.getlimina.ai/en/pricing), [commercial reports](#products-and-free-tools) |
| Proprietary: Tonic Textual | Paid usage / enterprise contract | Tonic Cloud or paid self-hosted deployment | Unstructured text and document/image formats listed by vendor, including DOCX/PDF/PPTX/CSV | Vendor advertises 50+ languages; **Finnish has not been verified or tested here** | Account/API/pipeline setup; own infrastructure for self-hosting | [Official capabilities](https://www.tonic.ai/products/textual), [pricing/deployment](https://www.tonic.ai/pricing) |

The hosted rows require sending source data to a third party. They are research
comparators; this table does not authorize uploading private documents. A
self-hosted commercial deployment is a different route from the hosted trial
and needs its own deployment and data-flow verification.

### Reading the inventory

The existing results have different denominators. The [detector matrix](dataset-audit-runs.md)
scores whole labelled values. The [free-tool results](../eval/free_tools/) record
changed text needing review, which is not equivalent to verified removal.
Commercial tests use much smaller synthetic samples and distinguish any-type
coverage from type-aware detection. ARX's tabular risk/utility measures do not
share a text-span recall denominator. These numbers must not be ranked in one
accuracy column.

## Related

- [dataset-audit-runs.md](dataset-audit-runs.md): the seven-method detector matrix
- [contextual-llm.md](contextual-llm.md): local LLMs merged with `combined`, and contextual identifiers
- [ocr-survey.md](ocr-survey.md): OCR engines
- [screenshot-redaction.md](screenshot-redaction.md): screenshot redaction tools and results
- [limitations.md](limitations.md): what the evidence does not show
