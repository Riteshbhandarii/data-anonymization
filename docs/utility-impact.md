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
The CSV separates `planned` from `attempted`, so blank rows increase the accuracy
denominator without inventing model calls. Mixed models are rejected even when
one model produced an invalid answer.

Retention is measured on paired questions the model answered correctly on raw
text. A sanitized answer becoming wrong or refused is a loss. A wrong raw
answer becoming correct is a gain, reported separately. Invalid or unrun
answers make that pair incomplete rather than silently removing it. Mixed
models, duplicate IDs, unknown IDs, missing variants, differing questions and
differing accepted answers are rejected. Existing packs and reports are never
overwritten.

## Archived pre-audit local experiment

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
hide. Repeat the paired study with the other new methods, Finnish questions
and the public model selected for #44 before claiming deployment utility.

## 2026-10-19 rerun

Measured detector source: `e148240`. The existing three English memos and nine questions from `eval.create_study` were rerun with `combined`, then with `combined + Gemma` because the [local comparison](local-llm-comparison.md) found a one-label body-recall gain for that final pass. The Finnish counterpart uses three new fictional memos and nine questions. **Finnish wording and accepted answers: NEEDS HUMAN REVIEW.** These current results are separate from the archived pre-audit tables above.

The answering model for every condition was `qwen/qwen3.5-9b`, LM Studio 0.4.18+1 MLX 4-bit, 8192-token context and one parallel prediction on the 16 GiB host. Each request used temperature 0, `reasoning_effort=none`, `enable_thinking=false`, an answer/refused JSON schema and at most 256 output tokens; no sampling seed was set. Chats were independent, web search was off and aliases were document-scoped. Requests went only to `127.0.0.1:1234`; no paid or hosted API was used. The exact answering prompt and schema are included in every linked report.

Combined spans were prepared with GLiNER on CPU and frozen for the six utility memos, separately from the fourteen-document body-corpus cache. That process exited before an LLM was loaded. Gemma prepared its final-pass variants from replayed spans after validating detector-source, suite and document hashes. Gemma was then unloaded and Qwen alone answered the four packs. Accepted answers were opened for scoring only after answering each complete pack. The [runner](../eval/local_utility.py) uses the existing `eval.study.score_answer` normalization and keeps invalid/error rows in the planned denominator.

There were 108 answering requests: four separately scored 27-request packs. Every planned request was attempted; no invalid responses, provider errors or unrun rows occurred. R means retained correct answers among that exact pack’s raw-correct questions. No English/Finnish score is pooled, and a retention count with raw denominator 7 is not ranked against one with raw denominator 9.

| Language | Sanitizer / source | Variant | Correct / planned | Wrong | Refused | Invalid | Error | R / raw-correct |
|---|---|---|---:|---:|---:|---:|---:|---:|
| English | [Combined](../eval/baselines/final-evidence-utility-en-combined.json) | raw | 7/9 | 0 | 2 | 0 | 0 | — |
| English | [Combined](../eval/baselines/final-evidence-utility-en-combined.json) | redacted | 5/9 | 1 | 3 | 0 | 0 | 5/7 |
| English | [Combined](../eval/baselines/final-evidence-utility-en-combined.json) | pseudonymized | 4/9 | 0 | 5 | 0 | 0 | 4/7 |
| English | [Combined + Gemma](../eval/baselines/final-evidence-utility-en-gemma-final.json) | raw | 7/9 | 0 | 2 | 0 | 0 | — |
| English | [Combined + Gemma](../eval/baselines/final-evidence-utility-en-gemma-final.json) | redacted | 5/9 | 1 | 3 | 0 | 0 | 5/7 |
| English | [Combined + Gemma](../eval/baselines/final-evidence-utility-en-gemma-final.json) | pseudonymized | 4/9 | 0 | 5 | 0 | 0 | 4/7 |
| Finnish draft | [Combined](../eval/baselines/final-evidence-utility-fi-combined.json) | raw | 9/9 | 0 | 0 | 0 | 0 | — |
| Finnish draft | [Combined](../eval/baselines/final-evidence-utility-fi-combined.json) | redacted | 1/9 | 5 | 3 | 0 | 0 | 1/9 |
| Finnish draft | [Combined](../eval/baselines/final-evidence-utility-fi-combined.json) | pseudonymized | 6/9 | 0 | 3 | 0 | 0 | 6/9 |
| Finnish draft | [Combined + Gemma](../eval/baselines/final-evidence-utility-fi-gemma-final.json) | raw | 9/9 | 0 | 0 | 0 | 0 | — |
| Finnish draft | [Combined + Gemma](../eval/baselines/final-evidence-utility-fi-gemma-final.json) | redacted | 1/9 | 5 | 3 | 0 | 0 | 1/9 |
| Finnish draft | [Combined + Gemma](../eval/baselines/final-evidence-utility-fi-gemma-final.json) | pseudonymized | 6/9 | 0 | 3 | 0 | 0 | 6/9 |

The English raw refusals were `request-00017` (`a1`, total hours) and `request-00067` (`b1`, total hours), in both sanitizer packs. Each recorded answer was `{"answer":"","refused":true}`. No reason was given, and no score-improving rerun was performed. Their raw-correct denominator is therefore 7. The Finnish packs each have nine raw-correct questions. These raw outcomes also differ from the archived experiment; do not reuse its 9/9 ceiling.

Gemma’s final pass changed none of the utility prompts: all 27 corresponding prompts and answer payloads were identical within each language. The [paired comparison](../eval/baselines/final-evidence-utility-comparison.json) records nine identical pairs per variant per language. Its one-label gain on the separate 146-body-label corpus therefore shows **no demonstrated usefulness gain in these six memos**. Raw inputs are identical between sanitizer conditions; any differing raw outcome in a future run would be answering variability, not detector improvement.

Both English and Finnish sanitized total-hours inputs replace the two hour values with `DATE_TIME` tokens. The reports record two date placeholders per memo and absence of the literal hour values in those inputs. A correct larger-project answer can therefore be a guess even when exact-answer scoring credits it. In particular, the Finnish pseudonymized larger-project answers were correct despite missing numeric evidence. These small, fixed templates measure answer matching and contact consistency; they do not prove general task fidelity or evidence-supported reasoning.

| Pack | Answering seconds / 27 requests | Runtime scope |
|---|---:|---|
| [en-combined](../eval/baselines/final-evidence-utility-en-combined.json) | 35.402 | Loopback HTTP answering only |
| [en-gemma-final](../eval/baselines/final-evidence-utility-en-gemma-final.json) | 32.869 | Loopback HTTP answering only |
| [fi-combined](../eval/baselines/final-evidence-utility-fi-combined.json) | 37.961 | Loopback HTTP answering only |
| [fi-gemma-final](../eval/baselines/final-evidence-utility-fi-gemma-final.json) | 37.998 | Loopback HTTP answering only |

Answering times exclude extraction, base detection, final-pass preparation and model loading. The utility Qwen reload took 9.229 s, recorded in [the configuration archive](../eval/baselines/final-evidence-local-configuration.json). No peak-memory measurement was made. All LLMs were unloaded after the last request; the loopback server remains running.

### Finnish human review

**NEEDS HUMAN REVIEW.** Read the [draft questions and accepted answers](../eval/utility_fi/suite.json) and the three memo texts. Verify the Finnish phrasing and exact accepted answer forms before accepting this as a Finnish utility benchmark. All companies and people are fictional.

| Memo | Total hours | Project with more hours | Same contact |
|---|---:|---|---|
| [a1](../eval/utility_fi/a1.md) | 30 | Kuusi | kyllä |
| [a2](../eval/utility_fi/a2.md) | 30 | Kuusi | ei |
| [b1](../eval/utility_fi/b1.md) | 30 | Kuusi | kyllä |

The exact model answers, including wrong and refused answers, are in the four aggregate/answer reports linked in the results table. The raw prompt/response logs and local scoring plans remain in ignored `outputs/final-evidence-utility/`. No public-AI #44 outcome is inferred from this local study.

### Reproduce the staged rerun

The current run called `eval.study.prepare` and `eval.utility_bench.build_pack` with recorded/replayed combined spans. [prepare_utility_rerun](../eval/prepare_utility_rerun.py) exposes those same stages for a repeat. Use a new directory. Before the base stage, confirm `lms ps` shows no loaded LLM. Each stage must exit before loading the next model.

```bash
python -m eval.create_study outputs/utility-repeat/en-suite
HF_HUB_OFFLINE=1 GLINER_DEVICE=cpu python -m eval.prepare_utility_rerun \
  --english-suite outputs/utility-repeat/en-suite/suite.json \
  --out outputs/utility-repeat --tag combined
lms server start --bind 127.0.0.1 --port 1234
lms load google/gemma-4-e4b --context-length 8192 --parallel 1 --identifier gemma-local --yes
HF_HUB_OFFLINE=1 GLINER_DEVICE=cpu python -m eval.prepare_utility_rerun \
  --english-suite outputs/utility-repeat/en-suite/suite.json \
  --out outputs/utility-repeat --tag gemma-final \
  --base-cache outputs/utility-repeat/combined-spans.json --model gemma-local
lms unload gemma-local
lms load qwen/qwen3.5-9b --context-length 8192 --parallel 1 --identifier qwen-local --yes
python -m eval.local_utility outputs/utility-repeat/en-combined-pack \
  --model qwen-local --out outputs/utility-repeat/en-combined-run
python -m eval.local_utility outputs/utility-repeat/fi-combined-pack \
  --model qwen-local --out outputs/utility-repeat/fi-combined-run
python -m eval.local_utility outputs/utility-repeat/en-gemma-final-pack \
  --model qwen-local --out outputs/utility-repeat/en-gemma-final-run
python -m eval.local_utility outputs/utility-repeat/fi-gemma-final-pack \
  --model qwen-local --out outputs/utility-repeat/fi-gemma-final-run
lms unload qwen-local
```
