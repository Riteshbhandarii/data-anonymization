# Role 1: detector corrections and metadata policy

Follow-up to #70 and #68, measured on 2026-10-20 against baseline routing at
`61eb73f`. Historical research tables and charts retain their original results.

## Detector changes

`combined` removes DATE_TIME candidates wholly inside explicit English/Finnish
quantities or technical standards, and PERSON candidates consisting entirely of
a recognized job title. Mixed spans containing a name/date remain; birth/age
contexts retain date candidates. These context rules do not change model weights.

Finnish Business ID (`1234567-8`) and Finnish VAT (`FI12345678`) shapes now produce
`FI_BUSINESS_ID` and `FI_VAT_NUMBER` spans. These flag potential company references,
not verified VAT registration. A mistyped identifier can still disclose its owner,
so checksum failure does not exempt a matching shape. Formats follow
[YTJ](https://www.ytj.fi/en/index/businessid.html) and the
[Tax Administration](https://www.vero.fi/en/businesses-and-corporations/taxes-and-charges/vat/international-commerce/vat-number/).

An optional `organization_terms` sequence supports a maintained local company
glossary. No corpus company names are embedded in the code. Construct a
`CombinedDetector(base.presidio, base.model, organization_terms=customer_names)`
from `base = get_detector("combined")` when deployment knowledge is available.
This is explicit supplementary knowledge, evaluated separately from default NER.
The short, suffix-free Finnish company miss in #70 remains a default-NER
limitation requiring independent validation or a team acceptance decision.

## Paired results

The policies share **the same actual raw Presidio/GLiNER predictions**, captured
on this Windows CPU host. Before uses old routing; after applies the corrections.
No answering LLM, paid API or cloud OCR was called. Only aggregate evidence is
published; raw cached spans and document text remain in ignored `outputs/`.
Cached lookup time is omitted because it is not model inference time.

Safe measured evidence: [role1-corrections-2026-10-20.json](../eval/baselines/role1-corrections-2026-10-20.json).

GLiNER checkpoint: `urchade/gliner_multi_pii-v1`, cached revision
`1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d`, CPU. English/Finnish small spaCy
models are both 3.8.0. Package versions and unchanged backbone-file hashes are
in the aggregate. Model thresholds were not raised.

| Regression scope | Denominator | Before | After |
|---|---:|---:|---:|
| Seed-42 n=1, typed body labels | 146 labels / 14 documents | 136 | 136 |
| Previously covered body labels newly lost | Every previously covered body label | — | 0 |
| Contextual test split: standard identifiers covered | 44 | 44 | 44 |
| Contextual test split: business identifiers fully covered | 9 | 5 | 7 |
| Contextual test split: contextual identifiers fully covered | 71 | 26 | 28 |
| Contextual test split: decoys incorrectly masked | 46 | 21 | 5 |
| English utility memo hour quantities retained | 6 quantities / 3 memos | 0 | 6 |
| Finnish utility memo hour quantities retained | 6 quantities / 3 memos | 0 | 6 |

The contextual corpus hash is the existing experiment's
`59196e9978155e2f12609cf668022b3e23d0f9f42a008c6f2d236a56cd5149ee`.
These known test cases are reused as regressions, not claimed as newly blind
evaluation. The body corpus was regenerated on Windows with the same seed/size;
its byte fingerprint differs from the historical host. Paired before/after
inputs are identical. This is not a rerun of the full 885-document matrix, whose
public datasets are not cached on this machine.

Hours retention is available numeric evidence, **not** a rerun of historical
Qwen/Gemma question-answering accuracy. Remaining contextual misses, the five
decoys and the suffix-free company are not claimed solved. Default results do
not use a company glossary. The linked aggregate includes hashes and versions.

## Metadata decision

Metadata omission is the release default in `run_pipeline`, the UI and manual
public-AI pack builder. Tasks usually need body content, not shared template
titles and internal keyword codes. Explicit retention remains available for a
reviewed need. Low-level extraction and extraction/detection audits retain the
properties so missing extraction cannot be hidden by the release policy.

Complete `Document metadata` sections are removed before detection in the
pipeline/UI, and before truncation of sanitized manual-pack exports. Repeated
sections, nested headings, CRLF and fenced code are handled. Notes, comments,
headers/footers, hidden sheets and body text remain subject to normal processing.
The UI excludes intentionally omitted metadata labels from its denominator;
changing the option invalidates the previous result. Original files are unchanged.
See the [clean-text cookbook](clean-text-cookbook.md).

## Outstanding acceptance

- **R01/R02 ChatGPT linkage re-test: NOT RUN.** Their previous exported bodies
  and sources are not in this checkout. The public report cannot reconstruct
  those inputs. Local removal tests do not establish that all linkage is gone.
- Once the previous `runs` directory is available, create a fresh pack with
  `python -m eval.make_pack --runs PREVIOUS_RUNS --pack outputs/metadata-off-pack --method combined`.
  Inspect `paste/link-R01-R02.txt` and the unrelated-pair controls. Repeat the
  actual ChatGPT conditions in independent chats and record model/version,
  date, search state, verbatim responses and scores. Preserve the old answers.
- `--include-metadata` creates a retained-property comparison condition. Raw
  fictional ceiling controls remain raw in both packs.
- Matching answering-model usefulness results, acceptance of the company
  limitation and any requirement for sanitized original formats remain pending.
  These issues are not automatically closed by this code change.

## Reproduce

Install combined's dependencies and small English/Finnish spaCy models first.
Use a new output directory to preserve reports and caches.

```bash
python corpus/generate.py --out outputs/role1-repro/corpus --n 1 --seed 42
python -m eval.contextual_corpus --out outputs/role1-repro/contextual --seed 42
python -m eval.create_study outputs/role1-repro/utility
python -m eval.role1_regression outputs/role1-repro \
  --components outputs/role1-repro/frozen-components.json \
  --out outputs/role1-repro/comparison.json
```

The last command captures each model family's actual predictions if the cache
does not exist, then scores both policies on that cache. Existing caches are
replayed. Only the safe aggregate report may be published.
