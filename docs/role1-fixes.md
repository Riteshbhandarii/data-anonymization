# Role 1: detector corrections and metadata policy

This follow-up to #70 and #68 changes `combined` context filtering and release
metadata handling. The original research matrix is unchanged and was not rerun.

## Behavior changes

- Remove fully contained numeric/date candidates in ISO/IEC/EN/SFS and ASTM
  citations. Calendar-shaped references need a directly attached technical marker;
  intervening prose is insufficient. Mixed candidates crossing a citation stay masked.
  Names and business/personal IDs are never exempted merely by citation overlap.
- Remove explicit operational time quantities while guarding ages, personal history,
  subjects that may refer to people and possessives. An inanimate subject can bind a duration
  even when an unrelated reporting person's name occurs elsewhere; that name stays masked.
- Correct PERSON candidates made entirely of recognized job titles, and a narrow
  class of unnamed facilities in impersonal logistics clauses. Named sites,
  addresses, owners, site codes and uncertain continuations stay masked.
- Detect Finnish Business ID and VAT number shapes as `FI_BUSINESS_ID` and
  `FI_VAT_NUMBER`; checksum failure does not exempt a possible company reference.
  An optional `organization_terms` glossary supplies explicit deployment knowledge.
  The suffix-free Finnish company miss in #70 remains a default-NER limitation.
- Keep model weights, labels and thresholds unchanged. Filtering does not repair
  identifiers missed by the models.

Metadata omission is the release default in `run_pipeline`, the UI and manual
public-AI packs. Complete `Document metadata` sections are removed before
anonymization, and before truncation of sanitized pack exports. Property-value
line breaks are folded to prevent injected body headings. Repeated/nested
sections, CRLF, genuine code fences and inline code are covered by regressions.
Low-level extraction and audits retain properties; explicit retention is available
for a reviewed need. Notes, comments, headers/footers, hidden sheets and body text
still require normal processing. See [clean-text cookbook](clean-text-cookbook.md).

## Final policy replay

On 2026-10-23, cached actual CPU predictions captured on 2026-10-20 were replayed
against frozen policy SHA256
`60cdbcf72bc4c87e6c3a79c4228425ddd245bf23c70526da158e36f0bec9e6f5`.
The comparison is privacy-repaired baseline `8051239`; each pair shares identical
raw Presidio/GLiNER predictions. These published fixtures are development/regression
sets, not fresh blind evaluation. No inference or corpus generation was rerun.

| Actual-model scope | Before (`8051239`) | Final policy |
|---|---:|---:|
| Old development set: ordinary targets with unwanted masking | 35/56 | 33/56 |
| Old set: sensitive targets with any overlap / full coverage | 59/64 / 49/64 | 59/64 / 49/64 |
| Broad set: ordinary targets with unwanted masking | 46/70 | 46/70 |
| Broad set: sensitive targets with any overlap / full coverage | 88/90 / 69/90 | 88/90 / 69/90 |
| Targeted citation set: ordinary targets with unwanted masking | 3/20 | 0/20 |
| Newly lost actual sensitive characters in targeted adjudication | — | 0 |

Character retention gates lose no any-type or correctly typed protection against raw
routing or `8051239`. Targeted adjudication retains all 262 masked sensitive
characters (238 correctly typed). The native audit covers 146 body labels and
152 literal occurrences: all 2,409 masked characters (2,328 correctly typed) remain
protected. Typed body recall stays 136/146; retained utility hours stay 6/6 per
language. These are text-retention counts, not Qwen/Gemma answer accuracy.
Any overlap is not full anonymization. The broad set shows no utility gain;
existing misses and partial coverage remain.

A 60-case **focused development/regression probe** compares the pre-fix commit
`f3b93d1` (policy `62ae5ce…d072`) with the final policy. It informed a further
possessive-context refinement before replay; it is not fresh blind evaluation.

| Actual-model focused probe | Before (`f3b93d1`) | Final policy |
|---|---:|---:|
| Sensitive characters masked, any type / correctly typed | 311/397 / 299/397 | 369/397 / 357/397 |
| Sensitive targets fully covered | 35/46 | 42/46 |
| Ordinary targets with unwanted masking | 1/20 | 2/20 |

The final policy retains all raw/`8051239`/pre-fix sensitive character protection.
All four work-hour and four plain business-contract controls remain clear.
The added ordinary mask is a conservative calendar-shaped standard reference with
an intervening word before the citation; an older Finnish software-duration mask
also remains. Reviewer cases now yield `Date of admission ([DATE_TIME]).` and
`[PERSON] employment contract lasted [DATE_TIME].` The cases are tracked as
`review_context_regressions.json`; conversion preserves original text and labels.
Original probe SHA256: `35eb833e7c109dea2f0c854e3504255120475de3e169217e4f01e9f674560e62`.

Generated reports added by this PR are excluded from the diff; byte-verified local
copies remain under ignored `outputs/pr77-report-archive/eval/baselines/`.
Fixtures, tests and reproduction scripts remain tracked. Raw document text,
prediction caches and detailed local results stay under ignored `outputs/`.

## Capture versions and fixture hashes

Baseline source SHA256 (`8051239`):
`b15ef89cce764877ec53902484aafcbd29adecc2447b41e0e10a6ad85c2c23b9`.
Pre-fix policy SHA256: `62ae5ce1786af03c8a48fa696bc111f417a954ed87bc04b0149d630a9d29d072`.
Capture: CPU/offline, four torch threads; GLiNER threshold 0.4, Presidio 0.0.
GLiNER `urchade/gliner_multi_pii-v1`, revision
`1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d`. Packages: torch 2.14.1,
gliner 0.2.29, spaCy 3.8.16, Presidio analyzer/anonymizer 2.2.364,
transformers 5.16.1, huggingface-hub 1.9.0; English/Finnish small spaCy models 3.8.0.
Capture Python: 3.12.6 for broad/citation; unknown for old development. Versions describe inference.

| Tracked fixture | SHA256 |
|---|---|
| `tests/fixtures/context_holdout.json` | `96964af553983fdb00cd3f1c78ca140ded9f9cfd99e5faae70257770fe14801c` |
| `tests/fixtures/context_holdout_v2.json` | `c14a231b9d9b25ae7a6a8702f3d617c0f56043507c1d7c2e54122cf9695d031b` |
| `tests/fixtures/technical_citation_holdout.json` | `c5371a6758ada6d23e3155daa8224b27c183f25cd291a24adbfa5e78efde1a31` |
| `tests/fixtures/technical_citation_privacy_targets.json` | `0b13e70c8a46ca62f4e11807e545900df054a64f979b4b5bb6e59d224e482384` |
| `tests/fixtures/review_context_regressions.json` | `e00105713fa2a8e32795e8de7f294710513250acc84b2101d20f7acdd3539254` |

The citation privacy targets were independently annotated after raw capture,
not frozen detector ground truth. Contextual corpus SHA256:
`59196e9978155e2f12609cf668022b3e23d0f9f42a008c6f2d236a56cd5149ee`;
Windows seed-42 n=1 body corpus SHA256:
`bd6def49a3fac7c2f8c9427fe514cc369fdae6e5b8af75c62a80b2b05ff57274`.

## Reproduce

Use the project virtual environment, both spaCy models and cached GLiNER weights.
Preserve Git history containing `8051239`. Fresh captures below use new ignored
outputs; the original run's replay uses byte-identical raw cache/provenance files
in each output directory and omits `--capture`. These are `development-replay` checks.

```powershell
$policySha = "60cdbcf72bc4c87e6c3a79c4228425ddd245bf23c70526da158e36f0bec9e6f5"
python -m eval.context_guard_validation --fixture tests/fixtures/context_holdout_v2.json --fixture-sha c14a231b9d9b25ae7a6a8702f3d617c0f56043507c1d7c2e54122cf9695d031b --baseline-ref 8051239 --out outputs/role1-repro/broad-candidates.json
python -m eval.context_model_validation --capture --expected-policy-sha $policySha --fixture tests/fixtures/context_holdout_v2.json --fixture-sha c14a231b9d9b25ae7a6a8702f3d617c0f56043507c1d7c2e54122cf9695d031b --baseline-ref 8051239 --evaluation-stage development-replay --out outputs/role1-repro/broad-model
python -m eval.context_model_validation --capture --expected-policy-sha $policySha --fixture tests/fixtures/technical_citation_holdout.json --fixture-sha c5371a6758ada6d23e3155daa8224b27c183f25cd291a24adbfa5e78efde1a31 --privacy-targets tests/fixtures/technical_citation_privacy_targets.json --privacy-targets-sha 0b13e70c8a46ca62f4e11807e545900df054a64f979b4b5bb6e59d224e482384 --baseline-ref 8051239 --evaluation-stage development-replay --out outputs/role1-repro/citation-model
python -m eval.context_model_validation --capture --expected-policy-sha $policySha --fixture tests/fixtures/review_context_regressions.json --fixture-sha e00105713fa2a8e32795e8de7f294710513250acc84b2101d20f7acdd3539254 --baseline-ref f3b93d1 --evaluation-stage development-replay --out outputs/role1-repro/review-model
python corpus/generate.py --out outputs/role1-repro/corpus --n 1 --seed 42
python -m eval.contextual_corpus --out outputs/role1-repro/contextual --seed 42
python -m eval.create_study outputs/role1-repro/utility
python -m eval.role1_regression outputs/role1-repro --components outputs/role1-repro/frozen-components.json --out outputs/role1-repro/body-contextual.json
```

Capture is CPU/offline and refuses to overwrite raw model caches. Replay verifies
fixture bytes, metadata and provenance hashes. The body command captures only
when its cache is absent. No answering LLM, paid API or cloud OCR is used.

## Remaining acceptance work

- **R01/R02 actual ChatGPT linkage retest: not run.** Previous exported bodies
  and sources are absent. Local removal tests cannot establish that linkage is gone.
  With prior runs available, create a new pack using
  `python -m eval.make_pack --runs PREVIOUS_RUNS --pack outputs/metadata-off-pack --method combined`.
  Compare `paste/link-R01-R02.txt` and unrelated-pair controls in independent chats,
  recording model/version, date, search state, verbatim responses and scores.
  Use `--include-metadata` for retained properties; preserve old answers.
- Answering-model usefulness, acceptance of the company limitation and any need
  for sanitized original formats remain pending. Finite synthetic regressions
  cannot establish real-document safety or absence of overfitting.
