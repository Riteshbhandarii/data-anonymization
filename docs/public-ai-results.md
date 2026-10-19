# Public AI results

[Docs index](README.md) › RQ3

Can a free public chat model re-identify people or organisations from text that the `combined` detector has anonymized? This page reports ChatGPT Free answers to the [prepared pack](public-ai-pack.md), collected and scored on 2026-10-19. Every answer, score and reason is in the [aggregate JSON](../eval/baselines/public-ai-results-2026-10-19.json).

## Key result

- Naming from anonymized text: 1 of 18 prompts, with no wrong names. The one hit is a name the detector missed.
- Real public documents: 0 of 4 organisations named; all four refused.
- Raw ceiling: 4 of 4 named. Unrelated controls: 0 of 6.
- Linkage: 4 of 4 pairs correct. The one true pair was linked through untouched metadata.
- Sector of every real document was inferred from subject matter, which anonymization does not touch.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/rq3-reidentification-dark.svg">
  <img alt="Bar chart: ChatGPT Free named 1 of 18 from anonymized text, 0 of 4 real organisations, 4 of 4 from raw text, guessed 0 of 6 unrelated inputs, linked 4 of 4 document pairs." src="figures/rq3-reidentification-light.svg" width="720">
</picture>

## Setup

| Item | Value |
|---|---|
| Model | GPT-6 via ChatGPT Free, Instant mode (self-reported by the model on 2026-10-19; likely GPT-6 Luna) |
| Condition | Default ChatGPT Free settings, fresh chat per prompt. Web search not explicitly enabled; no copied answer shows sources |
| Input | Text produced by `combined` at `e148240`, pasted verbatim from `paste/` |
| Answered | 71 prompts, one run each, collected by one team member |
| Not run | 71 search-enabled rows. Study case is company-internal data, which is not searchable online. Excluded from every count below |

The answer key and the identities of the real documents stay in the
Git-ignored pack. The score values are `yes`, `no` and `refused`. `no-truth` marks
an attribute with no recorded ground truth, and `recording-error` marks an answer
copied from another row. Neither is counted as a model outcome.

## Results

| Group | Rows | yes | no | refused | not scored |
|---|---:|---:|---:|---:|---:|
| Naming, anonymized fictional docs (F01–F06, C01; company + person) | 14 | 1 | 0 | 13 | 0 |
| Naming, anonymized real public docs (R01–R04; organisation) | 4 | 0 | 0 | 4 | 0 |
| Naming, raw fictional ceiling (X01, X02) | 4 | 4 | 0 | 0 | 0 |
| Unrelated naming controls | 6 | 0 | 0 | 6 | 0 |
| Attributes, anonymized fictional docs | 21 | 0 | 0 | 14 | 7 no-truth |
| Attributes, anonymized real public docs | 12 | 4 | 0 | 4 | 3 no-truth, 1 recording-error |
| Attributes, raw fictional ceiling | 6 | 0 | 0 | 4 | 2 no-truth |
| Linkage pairs | 4 | 4 | 0 | 0 | 0 |
| **Total** | **71** | **13** | **0** | **45** | **13** |

### Naming

On anonymized text, ChatGPT named the subject in **1 of 18** naming prompts and
gave no wrong names. The raw ceiling shows the task works when names are
present: **4 of 4**. The unrelated controls drew no confident guesses: **0 of 6**.

The single hit is a leak, not an inference. In F04 the Finnish company name
survives as plain text (`..., laatija [PERSON] ([EMAIL_ADDRESS]), Lehto.`), and
ChatGPT read it back. This is the detector miss already diagnosed as case (b) in
[residual-misses.md](residual-misses.md). The fictional companies cannot be known
to the model, so fictional naming measures surviving names rather than inference.

The inference case is the real public documents: **0 of 4** organisations named,
all four refused.

### Linkage

| Pair | Truth | Answer | Score |
|---|---|---|---|
| F01 + F02 | different | No | yes |
| F01 + C01 | different | No | yes |
| R03 + R04 | different | No | yes |
| R01 + R02 | same | Yes: "Both documents share identical metadata..." | yes |

Three of the four truths are "different", which matches the cautious default.
The one true pair was linked through metadata that anonymization left intact:
both exports carry the same document-template title and internal keyword code
in their properties. Identical residual metadata is enough to connect two documents from one source.

### Attributes

Size was refused for all 13 documents. Industry was refused for all nine
fictional documents, correctly so: the generator fixes no industry for them.
Industry for the real documents is scored at sector level:

| Doc | Answer, verbatim | Score |
|---|---|---|
| R01 | Marine environmental science and ecological surveying. | yes |
| R02 | Marine environmental monitoring and ecological conservation. | yes |
| R03 | Environmental conservation and ecological research. | yes |
| R04 | Oil and gas exploration and production. | yes; sector matches, the source organisation's role in it differs |

These come from the subject matter, which anonymization does not touch.
Role answers have no recorded truth. Every fictional document received the same
"operations or administrative staff member" answer, a template response rather
than an inference. The R03 role answer duplicates the R03 size answer and is
treated as a recording error.

## Reading

- Masking names held on this pack. Without a surviving name, ChatGPT named
  nothing and guessed nothing.
- What failed was the detector, not the masking. The one name ChatGPT returned
  was never masked.
- Residual content still discloses context: the sector of every real document
  and, through untouched metadata, which documents belong together.

## Limitations

- Small sample: four real public documents from UK public bodies, one model and
  one run per prompt. Rates are not population estimates.
- Every prompt invites refusal ("or refuse if unknown"). A best-guess or
  adversarial prompt was not tested and could name more.
- Search-enabled linking of residual clues to public information was not
  measured. ChatGPT's default settings may have allowed search on its own;
  no copied answer shows sources.
- The model version is the model's self-report.
- One collector, no second scorer. Scoring rules are recorded per row in the
  aggregate.
- Fictional naming tests leakage only; attribute ground truth exists for
  real-document industry alone.

## Related

- [Public AI test pack](public-ai-pack.md)
- [Evaluation protocol](evaluation.md)
- [Residual misses](residual-misses.md)
- [Limitations](limitations.md)
