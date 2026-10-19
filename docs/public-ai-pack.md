# Public AI test pack

[Docs index](README.md) › RQ3

This page describes the manual test pack used to ask a public chat model to re-identify anonymized documents. The pack was built locally on 2026-10-19 from the fictional and real public documents, using the `combined` method (GLiNER on Apple MPS) at `e148240`. The answers and scores are in [public-ai-results.md](public-ai-results.md).

The answer key was not read, printed or hashed during preparation. No public-model request was made at preparation time.

## Pack contents

| Item | Verified at preparation |
|---|---|
| Pack | `outputs/2026-10-19-e148240/pack/` |
| Instructions | `README.md` and `prompts.md` present |
| Document IDs | 13 Markdown files in `docs/` |
| Paste prompts | 71 text files in `paste/` |
| Answer rows | **142**, all model/answer/score fields blank |
| Search conditions | 71 without search, 71 with search; exactly one of each per prompt |
| Prompt coverage | Every answer prompt ID has its matching paste file; no duplicate prompt/search pair |
| Safe verification record | [public-ai-pack-e148240.json](../eval/baselines/public-ai-pack-e148240.json), including hashes of non-key files |

The builder at `e148240` produces **142** rows: 130 base rows plus 12
target-specific unrelated naming-control rows. These controls measure guesses
against the original target, not correct naming of the unrelated input. Keep
them, and do not mix 130-row and 142-row denominators.

## Finnish documents

These IDs come from the builder's language and format selections, not from the answer key.

| ID | Language / format | Role |
|---|---|---|
| F04 | Finnish DOCX | Anonymized fictional document |
| F05 | Finnish PPTX | Anonymized fictional document |
| F06 | Finnish PDF | Anonymized fictional document |
| X02 | Finnish DOCX | Raw fictional ceiling control; same source document as F04 |

These are four pack IDs from three Finnish source documents. All other pack IDs
are English. Real public files appear only in anonymized form under neutral
IDs. The builder excludes staff organograms. Source filenames and identities are
not reproduced here.

## Human execution

1. Review `README.md` and the document outputs.
2. Paste only the files in `paste/` into fresh chats, under the specified search condition.
3. Record the exact answer, model and version, and actual search condition in `answers.csv`. Leave requests that were not run blank.
4. Record all answers before consulting the answer key, then score under the existing protocol.

The pack tests the prepared, possibly truncated inputs. It does not test a
rebuilt Office or PDF original and does not show safety for arbitrary company
files. The screenshot logo and letterhead experiment is PENDING; this text pack
gives no visual re-identification result.

## Reproduce

The pack was built with these arguments:

```bash
HF_HUB_OFFLINE=1 GLINER_DEVICE=mps TOKENIZERS_PARALLELISM=false \
python -m eval.run_matrix \
  --out outputs/2026-10-19-e148240/runs \
  --datasets fake real-uk --methods combined \
  --pack outputs/2026-10-19-e148240/pack
```

The process exited zero. No LLM was loaded alongside GLiNER. A first CPU attempt
was stopped before completion and kept separately under
`outputs/2026-10-19-e148240/incomplete-cpu-runs/`; it is not in the timings
below. The MPS run's metadata is in the verification record above and in
`runs/runtime.csv`.

| Preparation dataset | Documents | Characters | Extraction s | Detection s | Warmup/load s |
|---|---:|---:|---:|---:|---:|
| Synthetic office/images | 140 | 76,592 | 24.2 | 29.0 | 10.3 |
| Real-public UK exports | 17 | 2,040,231 | 32.4 | 1,178.2 | 0.3 |

These are matrix-preparation timings, not the time to answer the pack. The
runner times model warmup separately and constructors may fall outside that
interval, so this is not a cold-start measurement. The real public documents are
unlabelled, so no recall or precision is available for them.

Two exports were truncated by the runner's default 400,000-character limit. The
pack applies a separate 12,000-character paste limit per document, cut at a line
break where possible. Neither limit establishes whole-source coverage. Pack
creation refuses to overwrite an existing pack, so use a new directory for
another experiment and keep the answers.

## Related

- [Public AI results](public-ai-results.md)
- [Evaluation protocol](evaluation.md)
- [Residual misses](residual-misses.md)
- [Limitations](limitations.md)
