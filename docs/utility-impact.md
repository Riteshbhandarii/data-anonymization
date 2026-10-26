# Utility impact

[Docs index](README.md) › RQ4

The [2026-10-20 detector follow-up](role1-fixes.md) restores the twelve hour
quantities in these six memos. This measures retained text, not new answering-model
accuracy. The historical answers and tables below remain unchanged.

Does replacing identifiers destroy the task a document was meant to support? The study asks the same question of raw, redacted and pseudonymized versions of the same text. It uses six fictional memos (three English, three Finnish), nine questions per language, and one local answering model. Public-AI re-identification is a separate study ([public-ai-results.md](public-ai-results.md)).

## Key result

- Exact-answer scoring: redacted 5/9 (English) and 1/9 (Finnish); pseudonymized 4/9 and 6/9. Raw is 7/9 and 9/9.
- Counting only answers the sanitized text can support: redacted 0/9 in both languages; pseudonymized 3/9 in both.
- Generic redaction left no usable evidence on these tasks. Pseudonyms kept only who-is-who.
- The Gemma final pass changed none of the 27 prompts or answers per language, so it shows no usefulness gain in these memos.
- Scores are not pooled across languages. The sample is small and fixed.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/rq4-usefulness-dark.svg">
  <img alt="Bar chart: English raw 7, redacted 5 exact and 0 supported, pseudonyms 4 exact and 3 supported; Finnish raw 9, redacted 1 and 0, pseudonyms 6 and 3, out of 9." src="figures/rq4-usefulness-light.svg" width="720">
</picture>

## 2026-10-19 rerun

Detector source: `e148240`. The three English memos and nine questions from `eval.create_study` were run with `combined`, then with `combined + Gemma`, because the [local comparison](local-llm-comparison.md) found a one-label body-recall gain for that final pass. The Finnish counterpart uses three new fictional memos and nine questions. Finnish wording and accepted answers were reviewed on 2026-10-19 ([review](../eval/utility_fi/README.md)). They are fit for reporting this run, not a validated benchmark.

### Setup

The answering model for every condition was `qwen/qwen3.5-9b`, LM Studio 0.4.18+1 MLX 4-bit, 8192-token context and one parallel prediction on the 16 GiB host. Each request used temperature 0, `reasoning_effort=none`, `enable_thinking=false`, an answer/refused JSON schema and at most 256 output tokens. No sampling seed was set. Chats were independent, web search was off and aliases were document-scoped. Requests went only to `127.0.0.1:1234`; no paid or hosted API was used. Every linked report includes the exact answering prompt and schema.

GLiNER prepared the combined spans on CPU and froze them for the six utility memos, separately from the fourteen-document body-corpus cache. That process exited before an LLM was loaded. Gemma prepared its final-pass variants from replayed spans after validating detector-source, suite and document hashes. Gemma was then unloaded and Qwen alone answered the four packs. Accepted answers were opened for scoring only after each complete pack was answered. The [runner](../eval/local_utility.py) uses the `eval.study.score_answer` normalization and keeps invalid and error rows in the planned denominator.

### Results

There were 108 answering requests in four separately scored 27-request packs. Every planned request was attempted; there were no invalid responses, provider errors or unrun rows. R is the number of retained correct answers among that pack's raw-correct questions. English and Finnish scores are not pooled, and a retention count with raw denominator 7 is not ranked against one with raw denominator 9.

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

The English raw refusals were `request-00017` (`a1`, total hours) and `request-00067` (`b1`, total hours), in both sanitizer packs. Each recorded answer was `{"answer":"","refused":true}`. No reason was given, and no score-improving rerun was performed. The English raw-correct denominator is therefore 7. Each Finnish pack has nine raw-correct questions. These raw outcomes differ from the archived experiment, so do not reuse its 9/9 ceiling.

Gemma's final pass changed none of the utility prompts: all 27 corresponding prompts and answer payloads were identical within each language. The [paired comparison](../eval/baselines/final-evidence-utility-comparison.json) records nine identical pairs per variant per language. Its one-label gain on the separate 146-body-label corpus therefore shows **no demonstrated usefulness gain in these six memos**. Raw inputs are identical between sanitizer conditions, so any differing raw outcome in a future run would be answering variability, not detector improvement.

In both languages, the sanitized total-hours inputs replace the two hour values with `DATE_TIME` tokens. The reports record two date placeholders per memo and no literal hour values in those inputs. A correct larger-project answer can therefore be a guess even when exact-answer scoring credits it. The Finnish pseudonymized larger-project answers were correct despite missing numeric evidence. These small, fixed templates measure answer matching and contact consistency. They do not prove general task fidelity or evidence-supported reasoning.

### Evidence-supported answers

Exact-answer scoring credits guesses. In every sanitized memo both hour values become `DATE_TIME` tokens. Generic redaction turns both contacts into the same `[PERSON]` token, while pseudonyms keep them distinct (`[PERSON_1]`, `[PERSON_2]`). The memos always list the larger project first. Counting only answers the sanitized text can support:

| Language | Raw | Redacted, exact / supported | Pseudonymized, exact / supported |
|---|---:|---:|---:|
| English | 7/9 | 5/9 / **0/9** | 4/9 / **3/9** |
| Finnish | 9/9 | 1/9 / **0/9** | 6/9 / **3/9** |

Redacted answers to total hours were refused, larger-project answers were unsupported guesses, and same-contact answers cannot be supported once both contacts read `[PERSON]`. The supported pseudonymized answers are the three same-contact questions in each language. The results are identical for `combined + Gemma`, whose prompts and answers matched `combined`. A replacement suite should vary allocation, order and totals.

### Runtime

| Pack | Answering seconds / 27 requests | Runtime scope |
|---|---:|---|
| [en-combined](../eval/baselines/final-evidence-utility-en-combined.json) | 35.402 | Loopback HTTP answering only |
| [en-gemma-final](../eval/baselines/final-evidence-utility-en-gemma-final.json) | 32.869 | Loopback HTTP answering only |
| [fi-combined](../eval/baselines/final-evidence-utility-fi-combined.json) | 37.961 | Loopback HTTP answering only |
| [fi-gemma-final](../eval/baselines/final-evidence-utility-fi-gemma-final.json) | 37.998 | Loopback HTTP answering only |

Answering times exclude extraction, base detection, final-pass preparation and model loading. The utility Qwen reload took 9.229 s, recorded in [the configuration archive](../eval/baselines/final-evidence-local-configuration.json). No peak-memory measurement was made. All LLMs were unloaded after the last request; the loopback server remains running.

### Finnish suite

Reviewed 2026-10-19: wording and accepted answers are correct, but the design lets guesses score ([review](../eval/utility_fi/README.md)). See the [questions and accepted answers](../eval/utility_fi/suite.json). All companies and people are fictional.

| Memo | Total hours | Project with more hours | Same contact |
|---|---:|---|---|
| [a1](../eval/utility_fi/a1.md) | 30 | Kuusi | kyllä |
| [a2](../eval/utility_fi/a2.md) | 30 | Kuusi | ei |
| [b1](../eval/utility_fi/b1.md) | 30 | Kuusi | kyllä |

The exact model answers, including wrong and refused answers, are in the four aggregate reports linked in the results table. The raw prompt and response logs and the local scoring plans stay in the Git-ignored `outputs/` folder. No public-AI outcome is inferred from this local study.

## Earlier experiment

The first run, on 2026-10-13, used rules-only and combined detectors on English only. It is archived in [archive/utility-impact-2026-10-13.md](archive/utility-impact-2026-10-13.md). Its 9/9 raw ceiling and sanitized scores are not comparable with the rerun above.

## Reproduce

### Prepare and score

`eval.utility_bench` exports the same question against raw, redacted and pseudonymized versions, then scores manually recorded answers. It makes no model calls. A free public model can be tested by pasting prompts individually.

Use the fictional study and the local preparation commands:

```bash
python -m eval.create_study outputs/utility/suite
python -m eval.study prepare outputs/utility/suite/suite.json --out outputs/utility/plan.json
python -m eval.utility_bench prepare outputs/utility/plan.json --out outputs/utility/pack
```

These commands create 27 utility prompts: three documents, three questions per document and three variants. Copy only `prompts/*.txt` into fresh chats, with web search off. Use the same model and version throughout. Record its exact short answer, model and version, and `refused=true` or `false` in `answers.csv`. Leave unrun rows blank. The raw controls contain fictional identities in this example. Review other source material before any upload.

Keep `plan.json` local, because it holds accepted answers and document content. Do not show it to the model or consult it while collecting answers. Then run:

```bash
python -m eval.utility_bench score outputs/utility/pack --out outputs/utility/report
```

The output includes `scored.csv`, `summary.csv`, `paired.csv` and `summary.md`. Exact matching uses the Unicode, case and whitespace normalization in `eval.study.score_answer`. Wrong answers, refusals, invalid answers and unrun requests are separate, and all remain in the planned-request denominator. The CSV separates `planned` from `attempted`, so blank rows raise the accuracy denominator without inventing model calls. Mixed models are rejected even when one model produced an invalid answer.

Retention is measured on paired questions the model answered correctly on raw text. A sanitized answer becoming wrong or refused is a loss. A wrong raw answer becoming correct is a gain, reported separately. Invalid or unrun answers make that pair incomplete rather than silently removing it. Mixed models, duplicate IDs, unknown IDs, missing variants, differing questions and differing accepted answers are rejected. Existing packs and reports are never overwritten.

### Staged rerun

The 2026-10-19 run called `eval.study.prepare` and `eval.utility_bench.build_pack` with recorded and replayed combined spans. [prepare_utility_rerun](../eval/prepare_utility_rerun.py) exposes those same stages for a repeat. Use a new directory. Before the base stage, confirm `lms ps` shows no loaded LLM. Each stage must exit before the next model loads.

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

## Related

- [Public AI results](public-ai-results.md)
- [Local LLM comparison](local-llm-comparison.md)
- [Evaluation protocol](evaluation.md)
- [Options map](options-map.md)
- [Limitations](limitations.md)
