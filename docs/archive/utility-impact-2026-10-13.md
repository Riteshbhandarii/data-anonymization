# Utility impact: pre-audit experiment, 2026-10-13

> **Archived.** Superseded by the [2026-10-19 rerun](../utility-impact.md#2026-10-19-rerun). Kept as the record of the first utility measurement.

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

The same model and settings were then run on the identical suite with the
`combined` detector from #53 (27 additional requests, no errors). This second
run used the locally integrated detector/UI/screenshot branches; aggregate
scoring used the same code above. Its plan and raw answers are saved under
`outputs/utility-qwen-combined/` in the integration checkout.

| Combined-detector variant | Correct / questions | Wrong | Refused | Retained / raw-correct |
|---|---:|---:|---:|---:|
| Raw | 9/9 | 0 | 0 | — |
| Generic replacement | 5/9 | 1 | 3 | 5/9 |
| Consistent pseudonyms | 6/9 | 0 | 3 | 6/9 |

The combined detector preserves project names and detects the company, which
the rules-only run missed. Numbered aliases also restore the contact comparison
on all three documents in this run. Both sanitized variants still fail all
three total-hours questions because the retained Presidio date recognizer
removes `hours 18` and `hours 12`. Higher recall therefore leaves a measurable
utility problem even when the combined detector improves other tasks.

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
hide. The 2026-10-19 rerun repeats the paired study with Finnish
questions; the public model was not used for utility.

