# Re-identification and utility experiments

`eval/study.py` implements the experiment protocol for issues #18 and #19.
It prepares document variants locally, runs independent model requests, and
reports outcomes with raw and unrelated controls. The current implementation
has been tested offline; no external-model result is claimed by those tests.

## Prepare a study

Install optional evaluation dependencies and the existing detector models:

```bash
python -m pip install -r requirements-evaluation.txt
python -m spacy download en_core_web_sm
python -m spacy download fi_core_news_sm
```

Create a small fictional study and prepare its requests:

```bash
python -m eval.create_study outputs/study
python -m eval.study prepare outputs/study/suite.json --out outputs/study/plan.json --alias-scope corpus
python -m eval.study run outputs/study/plan.json
```

These commands do not call an external model. The last command prints the
number of prepared requests. The example has three Markdown documents, two
organisations, and 84 requests including all controls and variants.

`prepare` reads the actual files through the extraction pipeline, normalizes
their Markdown, detects spans, and creates these variants from the same text
and detections:

| Variant | Processing |
|---|---|
| `raw` | Extracted Markdown without replacement |
| `redacted` | Generic type tokens such as `[PERSON]` |
| `pseudonymized` | Numbered tokens such as `[PERSON_1]` |

`--alias-scope document` starts a fresh map for each file. `--alias-scope corpus`
shares a map across the study. The chosen scope is recorded in each request.
Run separate plans to compare scopes; document-local numbering can itself
create misleading similarities between different subjects.

## Define the ground truth

The example generator creates `suite.json` and actual `.md` source files. To
use another corpus, create the same JSON structure beside its source files:

```json
{
  "schema_version": 1,
  "synthetic": true,
  "documents": [
    {
      "id": "document-001",
      "file": "documents/report.docx",
      "language": "en",
      "subject_id": "organisation-A",
      "naming": {"company": ["Example Company"]},
      "attributes": {"industry": ["software", "software development"]},
      "utility": [
        {
          "id": "total_hours",
          "question": "What is the total allocated hours? Return only the number.",
          "answers": ["30"]
        }
      ]
    }
  ]
}
```

The single record above illustrates the schema; a runnable suite needs at least
three documents providing both a same-subject pair and an unrelated subject.
Use verified ground truth, not model-generated guesses. Accepted answers are
lists of strings, including any legitimate spelling variants. All source paths
must remain inside the directory containing the suite.

`subject_id` defines the true organisation used to score linkage and choose
unrelated controls. It is never sent as part of a prompt. Labels, accepted
answers and source filenames also remain outside prompts; document text may
naturally contain names in the raw control. Plans contain source text and ground
truth and are stored under the Git-ignored `outputs/` directory.

The example's utility questions test a numeric total, a comparison, and whether
two projects have the same contact. Both yes and no relationship answers are
represented. The exact same question is applied to raw, redacted and
pseudonymized versions; only document content changes.

## Controls and scoring

| Request | Purpose |
|---|---|
| Raw naming / attribute inference | Establish how answerable the task is before replacement |
| Sanitized naming / attribute inference | Measure surviving identifying information |
| Same prompt, unrelated raw document | Measure agreement with the original target's answer by chance |
| Linkage on same-subject and different-subject pairs | Measure whether a model can distinguish shared subjects, with raw and sanitized versions |
| Utility on all three variants | Measure task accuracy lost or retained after replacement |

The unrelated control retains the original target's expected answer while
changing its input document. It does not count correctly naming the unrelated
document as successful identification of the target. Linkage pairs have their
own true yes/no answer; they are not scored against an unrelated naming answer.

Answers are scored by exact accepted-answer matching after Unicode, casing,
whitespace and terminal-period normalization. Substrings and long speculative
answers do not count as correct. Outcomes are `correct`, `wrong`, `refused`,
`invalid` and `error`. API failures and malformed answers remain separate from
refusals and stay in the attempted-request denominator. Review raw answers
when extending the accepted-answer list, then rerun scoring consistently.

Reports group results by task, prompt, variant and control. The output includes
counts and correct/wrong/refused rates. Compare utility `correct_rate` with the
matching raw row, and compare re-identification rows with both control rows.
Record the difference rather than combining privacy and utility into one score.

The invented identities in the example are not a benchmark of real-world web
re-identification: they have no established public footprint. Their purpose is
to exercise the protocol and compare relational task behavior. Use a separately
agreed, suitable labelled dataset for a substantive re-identification study.

## Run model requests later

After reviewing the local plan and choosing a model, set `OPENAI_API_KEY` in the
environment and explicitly execute:

```bash
python -m eval.study run outputs/study/plan.json --execute --model YOUR_MODEL --out outputs/study/run-001 --max-requests 100
```

Choose a model supporting Responses API structured outputs and `web_search`.
The implementation follows OpenAI's [web search documentation](https://developers.openai.com/api/docs/guides/tools-web-search)
and [structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs).
External calls are confined to this evaluation command, not `run_pipeline()`.

Re-identification requests enable web search and record attempted and completed
tool execution separately. An ordinary answer without a completed required
search is an error; an explicit refusal remains a refusal with search use false.
This prevents a failed tool call from being counted as a web-enabled result.
Utility requests use only the document. `--no-web-search` is available for an
explicitly labelled offline ablation, not a substitute for the protocol's web
condition. Requests do not share a conversation or previous model response.
Provider storage is disabled and SDK automatic retries are disabled.

`--max-requests` checks the complete plan before the first call. It does not
truncate the plan, drop controls or impose a dollar budget. Review model and
tool prices before execution. Each request limits model output to 600 tokens
and at most one web tool call. Use a new output directory for each run.

| Output | Contents |
|---|---|
| `answers.jsonl` | One flushed row per request, including document/format, variant, prompt, model, search settings and actual tool calls, answer, truth, score, usage, plan hash and time |
| `summary.csv` | Grouped counts and rates, with provider and parsing errors visible |

The plan also records document hashes, suite hash, detector threshold and
installed model/library versions. The raw provider output preserves web search
citations for inspection. Keep those citations attached when sharing excerpts.

CI tests controls, scoring, request limits and the provider boundary with an
injected fake client. It does not use credentials, download detector models, or
call paid APIs.
