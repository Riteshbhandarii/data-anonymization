# Utility impact of redaction

Issue #19 asks whether replacing identifiers destroys the task a document was
meant to support. `eval.utility_bench` exports the same question against raw,
redacted and pseudonymized versions, then scores manually recorded answers.
It makes no model calls. A free public model can be tested by pasting prompts
individually; the public-AI experiment in #44 remains separate.

## Prepare and score

Use the fictional study and the existing local preparation command:

```bash
python -m eval.create_study outputs/utility/suite
python -m eval.study prepare outputs/utility/suite/suite.json --out outputs/utility/plan.json
python -m eval.utility_bench prepare outputs/utility/plan.json --out outputs/utility/pack
```

These commands create 27 utility prompts: three documents, three questions per
document and three variants. Copy only `prompts/*.txt` into fresh chats, with
web search off. Use the same model and version throughout. Record its exact
short answer, model/version and `refused=true` or `false` in `answers.csv`.
Leave unrun rows blank. The raw controls contain fictional identities in this
example. Review other source material before any upload.

Keep `plan.json` local: it holds accepted answers and document content. Do not
show it to the model or consult it while collecting answers. Then run:

```bash
python -m eval.utility_bench score outputs/utility/pack --out outputs/utility/report
```

The output includes `scored.csv`, `summary.csv`, `paired.csv` and `summary.md`.
Exact matching uses the existing Unicode/case/whitespace normalization in
`eval.study.score_answer`. Wrong answers, refusals, invalid answers and unrun
requests are separate; all remain in the planned-request denominator.

Retention is measured on paired questions the model answered correctly on raw
text. A sanitized answer becoming wrong or refused is a loss. A wrong raw
answer becoming correct is a gain, reported separately. Invalid or unrun
answers make that pair incomplete rather than silently removing it. Mixed
models, duplicate IDs, unknown IDs, missing variants, differing questions and
differing accepted answers are rejected. Existing packs and reports are never
overwritten.

## First local experiment

Measured 2026-10-13 on the three fictional English project-allocation memos
from `eval.create_study`, through the actual extraction, Presidio `rules`
detector and redaction pipeline. This is an initial controlled utility result,
not a Finnish benchmark or a public-model re-identification result.

Model: `qwen/qwen3.5-9b`, LM Studio MLX 4-bit, about 6 GB cached weights, on a
16 GB Mac. Requests went only to `127.0.0.1:1234`, used temperature 0,
`reasoning_effort=none`, JSON-schema answers, at most 256 output tokens, web
search off, independent chats and document-scoped pseudonyms. There were 27
requests, no provider/parser errors and no unrun rows. The run's raw responses,
plan, CSV answers and reports stay under Git-ignored
`outputs/utility-qwen/` in the experiment checkout.

| Variant | Correct / questions | Wrong | Refused | Retained / raw-correct |
|---|---:|---:|---:|---:|
| Raw | 9/9 | 0 | 0 | — |
| Generic replacement | 1/9 | 2 | 6 | 1/9 |
| Consistent pseudonyms | 1/9 | 2 | 6 | 1/9 |

The three questions ask for the total hours, the project with more hours and
whether both projects have the same contact. Presidio's small-model rules
configuration tags the fragments `hours 18` and `hours 12` as `DATE_TIME`,
`Project Cedar` as `PERSON`, and `Project Pine` as `ORGANIZATION`. Replacement
therefore destroys the numeric values and project labels needed for the first
two tasks. Numbered aliases preserve contact identity in the text, but this
model still returns a wrong answer on two of the three contact comparisons.
Pseudonymization alone does not repair these detection mistakes.

This nine-question experiment cannot establish general accuracy. Its purpose
is to make the cost measurable and expose over-redaction that high recall can
hide. Repeat the paired study with the combined/new methods, Finnish questions
and the public model selected for #44 before claiming deployment utility.
