# Role 1: detector corrections and metadata policy

Follow-up to #70 and #68, measured on 2026-10-20 against baseline routing at
`61eb73f`. Historical research tables and charts retain their original results.

## Detector changes

`combined` removes DATE_TIME candidates wholly inside technical standards or
explicitly bound English/Finnish work-hour/duration expressions, and PERSON
candidates consisting entirely of a recognized job title. A quantity alone is
insufficient: unrelated words such as "contract" elsewhere in a sentence cannot
exempt an age. Ambiguous temporal contexts, personal history, calendar dates and
mixed name/date spans remain masked. These rules do not change model weights or
raise detection thresholds.

A narrow LOCATION correction covers lowercase unnamed facilities in impersonal
logistics clauses. Named sites, countries, addresses, owners, site codes and
uncertain continuations remain masked. This is a grammatical class, not a list
of places copied from the study corpus.

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

Safe measured evidence: the preserved
[initial comparison](../eval/baselines/role1-corrections-2026-10-20.json) and the
[guarded follow-up](../eval/baselines/role1-guarded-corrections-2026-10-20.json).

GLiNER checkpoint: `urchade/gliner_multi_pii-v1`, cached revision
`1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d`, CPU. English/Finnish small spaCy
models are both 3.8.0. Package versions and unchanged backbone-file hashes are
in the aggregate. Model thresholds were not raised.

| Regression scope | Denominator | Original routing | Initial correction (`c07a2e8`) | Guarded follow-up |
|---|---:|---:|---:|---:|
| Seed-42 n=1, typed body labels | 146 labels / 14 documents | 136 | 136 | 136 |
| Previously covered body labels newly lost | Every previously covered body label | — | 0 | 0 |
| Contextual test split: standard identifiers covered | 44 | 44 | 44 | 44 |
| Contextual test split: business identifiers fully covered | 9 | 5 | 7 | 7 |
| Contextual test split: contextual identifiers fully covered | 71 | 26 | 28 | 28 |
| Contextual test split: decoys incorrectly masked | 46 | 21 | 5 | 7 |
| English utility memo hour quantities retained | 6 quantities / 3 memos | 0 | 6 | 6 |
| Finnish utility memo hour quantities retained | 6 quantities / 3 memos | 0 | 6 | 6 |

The contextual corpus hash is the existing experiment's
`59196e9978155e2f12609cf668022b3e23d0f9f42a008c6f2d236a56cd5149ee`.
These known test cases are reused as regressions, not claimed as newly blind
evaluation. The body corpus was regenerated on Windows with the same seed/size;
its byte fingerprint differs from the historical host. Paired before/after
inputs are identical. This is not a rerun of the full 885-document matrix, whose
public datasets are not cached on this machine.

Hours retention is available numeric evidence, **not** a rerun of historical
Qwen/Gemma question-answering accuracy. The follow-up checks each contextual
label as well as each body label: no previously fully covered label becomes
uncovered. Remaining contextual misses and the suffix-free company are not
claimed solved. Default results do not use a company glossary.

### Privacy regression and independent validation

The initial correction was too broad: Finnish ages could be treated as ordinary
durations. A development probe uses actual, frozen CPU model predictions for
31 age sentences and 12 operational controls. Original routing detects 30/31
ages; the initial correction retains only 13/31; the guarded filter retains all
30 detected ages. The three exact reviewer examples are again masked. The one
remaining birthday-age miss precedes filtering. All 11 raw operational DATE_TIME
candidates are removed in both corrected policies. This probe informed
development and is **not** an independent accuracy estimate.
Its [aggregate](../eval/baselines/age-guard-probe-2026-10-20.json) records the
frozen raw/source hashes and model versions without document text or spans.

Before opening the independent fixture or measuring it, the policy was frozen
at SHA256 `b15ef89cce764877ec53902484aafcbd29adecc2447b41e0e10a6ad85c2c23b9`.
A separate author, without reading the implementation or existing cases,
prepared 120 fictional candidate checks (60 English, 60 Finnish). The fixture
hash is `96964af553983fdb00cd3f1c78ca140ded9f9cfd99e5faae70257770fe14801c`.
Its semantic `AGE` label is uniformly adapted to production `DATE_TIME` for all
34 such candidates before both policies, regardless of the expected result.
No rule or fixture was adjusted after measuring this holdout.

| Independent supplied-candidate check | Initial correction | Guarded follow-up |
|---|---:|---:|
| Sensitive candidates retained | 63/64 | 64/64 |
| Non-identifying candidates correctly discarded | 7/56 | 4/56 |
| Newly dropped sensitive candidates | — | 0 |

This is a check of the postfilter contract, **not detector recall**. See the
[aggregate](../eval/baselines/context-guard-holdout-2026-10-20.json) and
`eval/context_guard_validation.py`. The held-out utility result did not improve;
the follow-up therefore makes no claim of a general reduction in over-masking.
The known-corpus false masks rise from 5 to 7 while removing the unsafe age
exemption, despite recovering three unnamed-facility decoys. Uncertain durations
remain masked rather than weakening the privacy gate to obtain a better score.
Future changes need fresh independent cases; this published fixture is now a
regression set, not a reusable blind test. None of these samples guarantees
real-document safety or absence of overfitting.

The same frozen fixture was also processed by the actual offline CPU models.
Those predictions were captured once and shared by both filters; supplied
candidates were not injected into detection. This separates postfilter behavior
from what the models can find in the first place.

| Independent actual-model check | Raw routing | Initial correction | Guarded follow-up |
|---|---:|---:|---:|
| Sensitive targets with any masking overlap | 59/64 | 57/64 | 59/64 |
| Sensitive targets fully covered by the span union | 49/64 | 48/64 | 49/64 |
| Previously protected targets losing all overlap | — | 2 | 0 |
| Non-identifying targets with unwanted masking overlap | 35/56 | 33/56 | 35/56 |

Any overlap is **not full anonymization**. The five targets missed entirely
by raw routing (four ages and one named facility), and incomplete coverage of
other targets, remain detector limitations. The filter does not repair these
pre-existing misses. The actual-model holdout confirms the privacy repair but
does not demonstrate a general utility improvement. Its text-free aggregate is
[context-model-holdout-2026-10-20.json](../eval/baselines/context-model-holdout-2026-10-20.json).

## Metadata decision

Metadata omission is the release default in `run_pipeline`, the UI and manual
public-AI pack builder. Tasks usually need body content, not shared template
titles and internal keyword codes. Explicit retention remains available for a
reviewed need. Low-level extraction and extraction/detection audits retain the
properties so missing extraction cannot be hidden by the release policy.

Complete `Document metadata` sections are removed before detection in the
pipeline/UI, and before truncation of sanitized manual-pack exports. Repeated
sections, nested headings, CRLF and fenced code are handled. Property-value line
breaks are folded into spaces so a property cannot inject a body heading and
escape removal. The property text remains available to audits. Notes, comments,
headers/footers, hidden sheets and body text remain subject to normal processing.
The UI excludes intentionally omitted metadata labels from its denominator;
changing the option invalidates the previous result. Original files are unchanged.
See the [clean-text cookbook](clean-text-cookbook.md).

The follow-up also validates complete fence opener lines. Backtick info strings
cannot contain backticks, as specified by
[CommonMark](https://spec.commonmark.org/0.31.2/#fenced-code-blocks), so a complete
inline code span cannot suppress removal of a later metadata heading. Genuine
backtick/tilde fences and their examples remain intact. Regression tests cover
MD, TXT and custom-extractor paths before anonymization and output saving.

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

To replay the supplied-candidate comparison, retain Git history containing
`c07a2e8` and run `python -m eval.context_guard_validation --out NEW_REPORT.json`.
CI runs the current-policy privacy gate without requiring that history, model
weights or network access. The fixture bytes and offsets are checked before
scoring. Utility counts are reported, not asserted to be perfect.

For actual-model reproduction, cache the documented models first, then run:

```bash
python -m eval.context_model_validation --capture \
  --expected-policy-sha b15ef89cce764877ec53902484aafcbd29adecc2447b41e0e10a6ad85c2c23b9 \
  --out outputs/context-model-repro
```

The expected hash pins the policy before loading the fixture. Capture is CPU
only, offline, and refuses to overwrite a raw cache. Omit `--capture` to replay
the identical cached predictions. Raw text/spans stay under ignored `outputs/`;
only its `safe_aggregate.json` contains publishable counts and provenance.
The comparison requires Git history containing `c07a2e8`. Future policy versions
need their own recorded source hash and fresh independent validation data.
