# Final evidence run

Evidence run of 2026-10-19 on base commit `e148240`, run locally with no paid
API, cloud document upload or new account. Public primary-source documentation
was read for the desk-research rows. Later the same day the public-AI answers
were collected and scored ([results](public-ai-results.md)) and the Finnish
utility suite was reviewed ([review](../eval/utility_fi/README.md)); the status
lines below are as of this run.

## Execution record

| Task | Status / source |
|---|---|
| #44 public-AI pack | See [pack record](public-ai-pack.md). Actual answers and public-model safety test PENDING human execution. |
| #60 local LLM comparison | See [current comparison](local-llm-comparison.md); same 14 documents/146 body labels in each configuration. |
| #61 diagnosis | Complete; [residual misses](residual-misses.md), [compact evidence](../eval/baselines/residual-diagnosis-2026-10-19.json). No application fixes. |
| #62 utility | See [2026-10-19 rerun](utility-impact.md); Finnish draft NEEDS HUMAN REVIEW. |
| #63 options map | [Options map](options-map.md). The paper draft is kept local, outside the repository. |

The initial pack attempt used CPU and was terminated before real-uk completed;
its partial files remain in `outputs/2026-10-19-e148240/incomplete-cpu-runs/`.
They are not reported as a completed real-uk run. The replacement run uses MPS
with the same inputs/method and writes `runs/` and `pack/`. Detection source
files remain byte-identical to `e148240`; evaluation helpers serialize the base
stage so GLiNER and local LLMs never overlap in memory.

The first Qwen request batch encountered a stopped LM Studio server: 14
transport errors and **model inference NOT RUN**. It is preserved separately
from the successful rerun and is not used as a zero-accuracy model result.
The server was started on `127.0.0.1:1234`; only one cached LLM is loaded at a
time, with no GLiNER process beside it.

## Verification

- Full local unittest regression run: **224 passed**; `tests/eval`: **43 passed**.
- Ruff across app/corpus/pipeline/detect/redact/eval/tests/research passed.
- Focused local-model/cache/utility checks cover the later evaluation helpers.
  The full suite above preceded the final utility-preparation helper; its
  focused cache-integrity test and Ruff are recorded below. Application code
  remains unchanged.
- Fresh 70-document extraction reproduced **946/960**, including **14 OCR
  extraction failures**, with no reader exceptions. Gates were not loosened.
- Combined CPU smoke reproduced **136/146**, precision **197/238**, zero failed
  documents before either LLM was loaded.
- Run logs for the regression, scoring and both pack attempts were kept
  locally and are not part of the repository.

One regression test,
`tests/test_manual_pack.py::test_unrelated_control_truth_is_the_original_target_and_prompt_has_no_truth`,
builds and reads its own temporary synthetic fixture key. The actual study key
was not opened until every public-AI answer had been recorded.

## Open items at the time of this run

| Item | Finish condition |
|---|---|
| #44 | Review prepared documents, collect all planned model/search conditions, then score blind according to the pack instructions. Pack construction is not an experiment result. |
| Finnish utility | Review all three fictional memos, the nine questions and accepted answers in [eval/utility_fi/](../eval/utility_fi/), then accept or revise the study before using it as validated Finnish evidence. |
| #45 | Real-office documents still lack hand labels. TAB and Turku do not replace those format-specific labels; retain the paper limitation until the team resolves this. |
| Legal section | Teammate provides verified legislation/holding contribution; draft retains explicit placeholder. |
| Related work / paper claims | Verify full texts and bibliography, then write abstract/conclusion once evidence permits. |
| #32 / #64 | Team/PO scope/ownership acceptance and course/demo/handoff remain human work. |

## Results at the time of this run

| Study | Completed result |
|---|---|
| Local body recall, same 146 labels | combined 136; Qwen 94; Gemma 111; combined + Qwen 136; combined + Gemma 137 |
| English utility, each method independently | raw 7/9; redacted 5/9; pseudonyms 4/9. Paired retention 5/7 and 4/7 |
| Finnish draft utility, each method independently | raw 9/9; redacted 1/9; pseudonyms 6/9. Paired retention 1/9 and 6/9. Evidence-supported counts (0/9, 3/9 in both languages) were added after review: [utility-impact.md](utility-impact.md#evidence-supported-answers) |
| Utility method comparison | 108 requests; zero invalid/error; corresponding prompts and answer payloads identical between combined and Gemma final in both languages |
| Final resource state | No LLM loaded; LM Studio loopback server remains running |

Exact counts, precision, types, loading scope, timings, prompts, errors and
hashes are linked from the task reports above. No dataset denominators are
pooled into a common accuracy ranking.

## Exact repository files changed

Relative to `e148240` (A added, M modified). No file under `app/`, `corpus/`,
`pipeline/`, `detect/` or `redact/` changed.

| Area | Files |
|---|---|
| Overview | M `.gitignore`, M `README.md` |
| Docs | A `docs/final-evidence-run.md`, A `docs/local-llm-comparison.md`, M `docs/local-model-options.md`, A `docs/options-map.md`, A `docs/public-ai-pack.md`, A `docs/residual-misses.md`, M `docs/utility-impact.md` |
| Local detector aggregates | A `eval/baselines/final-evidence-local-combined.json`, A `eval/baselines/final-evidence-local-configuration.json`, A `eval/baselines/final-evidence-local-gemma-alone.json`, A `eval/baselines/final-evidence-local-gemma-final.json`, A `eval/baselines/final-evidence-local-qwen-alone.json`, A `eval/baselines/final-evidence-local-qwen-final.json`, A `eval/baselines/final-evidence-local-qwen-server-down.json` |
| Utility aggregates | A `eval/baselines/final-evidence-utility-comparison.json`, A `eval/baselines/final-evidence-utility-en-combined.json`, A `eval/baselines/final-evidence-utility-en-gemma-final.json`, A `eval/baselines/final-evidence-utility-fi-combined.json`, A `eval/baselines/final-evidence-utility-fi-gemma-final.json` |
| Pack / diagnosis records | A `eval/baselines/public-ai-pack-e148240.json`, A `eval/baselines/residual-diagnosis-2026-10-19.json` |
| Evaluation helpers | A `eval/local_base_cache.py`, M `eval/local_llm_bench.py`, A `eval/local_utility.py`, A `eval/prepare_utility_rerun.py` |
| Finnish utility draft | A `eval/utility_fi/README.md`, A `eval/utility_fi/a1.md`, A `eval/utility_fi/a2.md`, A `eval/utility_fi/b1.md`, A `eval/utility_fi/suite.json` |
| Tests | A `tests/test_local_base_cache.py`, A `tests/test_local_utility.py`, A `tests/test_utility_rerun_preparation.py` |

Generated source documents, raw local model answers, base-span caches, packs
and full extraction output remain under Git-ignored `outputs/`. Only safe
aggregates, fictional Finnish tasks, evaluation helpers and documentation are
committed.
