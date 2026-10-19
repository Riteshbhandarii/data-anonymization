# Public-AI manual pack at e148240

Complete locally on 2026-10-19. Method: **combined**, GLiNER on Apple MPS.
The actual study answer key was not read, printed or hashed. No public-model
request was made. Public-AI re-identification remains **PENDING #44**.

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

The request expected 130 rows. The audited builder at `e148240` produces
**142**: the original 130 plus 12 target-specific unrelated naming-control
rows. Those controls measure guesses against the original target rather than
correctly naming the unrelated input. They are retained. Do not silently drop
them or mix 130-row and 142-row study denominators.

## Finnish documents

These IDs come from the builder's language/format selections, without reading
the answer key.

| ID | Language / format | Role |
|---|---|---|
| F04 | Finnish DOCX | Anonymized fictional document |
| F05 | Finnish PPTX | Anonymized fictional document |
| F06 | Finnish PDF | Anonymized fictional document |
| X02 | Finnish DOCX | Raw fictional ceiling control; same source document as F04 |

These are four pack IDs from three Finnish source documents. Other pack IDs
are English. Real-public files appear only in anonymized form under neutral
IDs. Staff organograms are excluded by the builder; source filenames and
identities are not reproduced here.

## Reproduction and runtime

The pack was absent. The completed rebuild used the requested arguments:

```bash
HF_HUB_OFFLINE=1 GLINER_DEVICE=mps TOKENIZERS_PARALLELISM=false \
python -m eval.run_matrix \
  --out outputs/2026-10-19-e148240/runs \
  --datasets fake real-uk --methods combined \
  --pack outputs/2026-10-19-e148240/pack
```

The completed process exited zero. No LLM was loaded alongside GLiNER.
The first CPU attempt was stopped before completion and retained separately
under `outputs/2026-10-19-e148240/incomplete-cpu-runs/`; it is not included in
the completed runtime below. The MPS run's metadata is in the linked safe
verification record and `runs/runtime.csv`.

| Completed preparation dataset | Documents | Characters | Extraction s | Detection s | Warmup/load s |
|---|---:|---:|---:|---:|---:|
| Synthetic office/images | 140 | 76,592 | 24.2 | 29.0 | 10.3 |
| Real-public UK exports | 17 | 2,040,231 | 32.4 | 1,178.2 | 0.3 |

These are matrix-preparation timings, not the time to answer the manual pack.
The runner times model warmup separately; constructors may fall outside that
interval, so this is not a complete cold-start measurement. No recall or
precision is available for the unlabelled real-public documents.

Two exports were truncated by the runner's default 400,000-character limit.
The pack has a separate 12,000-character per-document paste limit, which cuts
at a line break where possible. Neither limit establishes whole-source coverage.
Pack creation refuses to overwrite an existing pack; preserve answers and use
a new directory for another experiment.

## Human execution

Review `README.md` and the actual document outputs, then paste only the files
in `paste/` into fresh chats under the specified search conditions. Record the
exact answer, model/version and actual search condition in `answers.csv`.
Leave requests that were not run blank. Record all answers before consulting
the answer key, then score under the existing protocol.

The study tests the prepared, possibly truncated inputs. It does not test a
rebuilt Office/PDF original or establish safety for arbitrary company files.
The separate screenshot logo/letterhead experiment remains PENDING; this text
pack does not supply a visual re-identification result.
