# Free local model options

Issue [#29](https://github.com/Riteshbhandarii/data-anonymization/issues/29)
collects the measured options. Detection runs locally; spaCy, GLiNER, GLiNER2
and Privacy Filter need a one-time weight download. The LLM route uses cached
weights through LM Studio's loopback server and needs no API key or paid API.

The main dataset results below come from [the dataset runs](dataset-runs.md)
and PRs [#53](https://github.com/Riteshbhandarii/data-anonymization/pull/53)
and [#54](https://github.com/Riteshbhandarii/data-anonymization/pull/54).
Fake recall covers 1,919 labels in all extracted locations. TAB covers 5,112
masked mentions in all 127 test documents. ai4privacy uses 300 rows per language
(1,986 English and 1,953 Finnish labels); Turku uses 100 Finnish mentions.
These are whole-value recalls, not a shared accuracy score across datasets.

| Kind / local option | Fake recall (all locations except marked body trial) | TAB recall | ai4privacy recall, en / fi | Finnish evidence | Hardware used / weight footprint | Detection time | Producing work |
|---|---|---|---|---|---|---|---|
| spaCy small + Presidio/project patterns (`rules`) | 80.0% (1536/1919) | 65.4% (3344/5112) | 54.2% / 42.1% | `fi_core_news_sm`; Turku 51.0% | Laptop CPU; no GPU required for these runs | ~4 s / 140 fake documents; ~25 s / 127 TAB documents | [#6](https://github.com/Riteshbhandarii/data-anonymization/issues/6), [#38](https://github.com/Riteshbhandarii/data-anonymization/pull/38), [#41](https://github.com/Riteshbhandarii/data-anonymization/pull/41) |
| spaCy large + Presidio/project patterns (`rules-lg`) | 84.2% (1615/1919) | 67.7% (3463/5112) | 58.1% / 46.7% | `fi_core_news_lg`; Turku 77.0% | Laptop CPU; ~800 MB model download reported in #29; runtime memory unmeasured | Not separately isolated in current summary | [#6](https://github.com/Riteshbhandarii/data-anonymization/issues/6), [#38](https://github.com/Riteshbhandarii/data-anonymization/pull/38), [#41](https://github.com/Riteshbhandarii/data-anonymization/pull/41) |
| Stanza | Not run | Not run | Not run | Not evaluated | No project hardware measurement | Not measured | [#7](https://github.com/Riteshbhandarii/data-anonymization/issues/7): owner dropped this comparison in favor of combined detection and Privacy Filter/GLiNER2 |
| GLiNER + project patterns (`urchade/gliner_multi_pii-v1`) | 86.9% (1668/1919) | 70.7% (3616/5112) | 75.9% / 79.0% | Turku 76.0%; measured despite Finnish not being listed separately in the model card | Apple MPS in dataset run; adapter also supports CPU/CUDA | 21 s / 140 fake documents; 143 s / 127 TAB documents | [#8](https://github.com/Riteshbhandarii/data-anonymization/issues/8), [#41](https://github.com/Riteshbhandarii/data-anonymization/pull/41) |
| Combined Presidio + GLiNER (`combined`) | **95.9% (1840/1919)** | **81.1% (4147/5112)** | **87.7% / 82.5%** | Turku 76.0%; strongest overall existing combination | spaCy CPU + GLiNER MPS on same laptop | 22 s / 140 fake documents; 146 s / 127 TAB documents | [#42](https://github.com/Riteshbhandarii/data-anonymization/issues/42), [#53](https://github.com/Riteshbhandarii/data-anonymization/pull/53) |
| Privacy Filter + project patterns (`openai/privacy-filter`) | 82.4% (1582/1919) | 28.1% (1439/5112) | 80.6% / 63.4% | Model card says primarily English; Turku 0.0% | CPU on 16 GB Mac; ~2.8 GB weights; peak runtime RAM unmeasured | 43 s / 140 fake documents; 175 s / 127 TAB documents | [#43](https://github.com/Riteshbhandarii/data-anonymization/issues/43), [#54](https://github.com/Riteshbhandarii/data-anonymization/pull/54) |
| GLiNER2-PII + project patterns (`fastino/gliner2-privacy-filter-PII-multi`) | 94.3% (1809/1919) | 67.2% (3434/5112) | 83.0% / **83.8%** | Finnish absent from seven stated training languages; Turku **78.0%** | CPU on 16 GB Mac; ~1.2 GB weights; peak runtime RAM unmeasured | 26 s / 140 fake documents; 184 s / 127 TAB documents | [#43](https://github.com/Riteshbhandarii/data-anonymization/issues/43), [#54](https://github.com/Riteshbhandarii/data-anonymization/pull/54) |
| Local Qwen 3.5 9B, LM Studio MLX 4-bit | **Body trial:** 64.4% (94/146); combined + Qwen 93.2% (136/146), same as combined alone | Not run | Not run | Body trial 63.0% (46/73); no public Finnish corpus measurement | Cached 5.98 GB on 16 GiB Mac (`Mac17,2`); 8192-token loaded context; no minimum-RAM claim | Standalone 13.3 / 11.5 s per en / fi document; pages not timed | [#9](https://github.com/Riteshbhandarii/data-anonymization/issues/9) folded into [#29](https://github.com/Riteshbhandarii/data-anonymization/issues/29) |
| Local Gemma 4 E4B, LM Studio MLX 4-bit | **Body trial:** 76.0% (111/146); full matrix not run | Not run | Not run | Body trial 68.5% (50/73); no public Finnish corpus measurement | Cached 6.86 GB on same 16 GiB Mac; 8192-token loaded context; no minimum-RAM claim | Standalone 12.9 / 10.8 s per en / fi document; pages not timed | [#9](https://github.com/Riteshbhandarii/data-anonymization/issues/9) folded into [#29](https://github.com/Riteshbhandarii/data-anonymization/issues/29) |

The earlier #29 spaCy comment used 2,450 body identifiers and rounded recalls
of 80% and 82%. The table uses the later dataset matrix and its different
corpus/denominator. Do not combine those runs. Timings exclude extraction and
model loading; other jobs ran concurrently, so they are approximate. No peak
RAM or VRAM measurement exists for the historical dataset runs.

Recall alone rewards excessive masking. The dataset runs also report lower-bound
precision: on TAB, GLiNER 61.7%, combined 69.7%, Privacy Filter 98.5%, GLiNER2
65.5%; on ai4privacy Finnish, respectively 88.8%, 90.9%, 94.3%, 91.8%.
Annotations are incomplete, so unlabelled detections are not proven mistakes.
Privacy Filter has no organization category and misses all Turku mentions;
GLiNER2 often omits the honorific that TAB includes in a person annotation.

## Local LLM trial and final pass

`detect/local_llm.py` exposes `LocalLLMDetector(model=...)` using the detector
interface (`detect(text, language)`). It requests JSON through the documented
[LM Studio structured-output endpoint](https://lmstudio.ai/docs/developer/openai-compat/structured-output),
sets temperature 0 and `reasoning_effort: "none"`, and also requests
`chat_template_kwargs.enable_thinking: false`. In the installed LM Studio
0.4.18+1 MLX runtime, the template flag alone put JSON into `reasoning_content`
with empty `content`. Adding `reasoning_effort: "none"` produced ordinary
content with zero reasoning tokens in the live smoke test. The adapter fails
on empty/malformed output rather than pretending it found no identifiers.

Returned values must be exact substrings; Python finds every occurrence and
assigns its offsets. Unknown types, invented strings and truncated JSON are
errors. Long input uses 4,000-character windows with 400-character overlap;
identifiers longer than that overlap can still cross a window boundary.
The `score=1.0` field is a compatibility flag, not calibrated confidence.

`FinalPassDetector(base, final)` masks the base detector's spans with equal-length
blocks, preserving line breaks and offsets, before calling the local model.
It retains the base spans and adds the local model's spans. The prompt includes
job/place combinations and relationships as `QUASI_IDENTIFIER`, but the
synthetic corpus has no labels for these: contextual privacy improvement is
**not measured** by this trial. The final pass remains optional and is not
enabled in the application by default.

Only loopback HTTP literals (or `localhost`, normalized to `127.0.0.1`) are
accepted. Environment proxies and redirects are disabled. No hosted client,
search tool or credentials are involved. Both requested models were cached as `lmstudio-community/Qwen3.5-9B-MLX-4bit`
and `lmstudio-community/gemma-4-E4B-it-MLX-4bit`; the unrelated uncensored
Qwen variant was not used.

Reproduce on already downloaded models:

```bash
lms server start --bind 127.0.0.1 --port 1234
lms load qwen/qwen3.5-9b --context-length 8192 --identifier qwen-local --yes
python corpus/generate.py --out outputs/local-corpus --n 1 --seed 42
python -m eval.local_llm_bench outputs/local-corpus --model qwen-local --out outputs/local-qwen.json
HF_HUB_OFFLINE=1 GLINER_DEVICE=cpu python -m eval.local_llm_bench outputs/local-corpus \
  --model qwen-local --base-method combined --out outputs/local-qwen-final.json
lms unload qwen-local
lms load google/gemma-4-e4b --context-length 8192 --identifier gemma-local --yes
python -m eval.local_llm_bench outputs/local-corpus --model gemma-local --out outputs/local-gemma.json
```

The CLI verifies the corpus SHA-256 before inference, writes per-type/language
recall and typed-overlap precision counts, records detection seconds per
**document**, and keeps failed documents in recall denominators. It exits
nonzero if any document fails. Reports contain aggregates only and stay in the
ignored `outputs/` directory; they do not store prompts or model-returned strings.

The trial uses seed 42, `--n 1`, Faker 40.39.0, 14 documents (seven per
language), and **146 body labels**, 73 per language. Corpus digest:
`27934f5e7fc88d0748be7b53d2d79ecfd797ad82c94c68d6fa16fd421c2e40ae`.
The generator also planted 46 non-body labels; they are excluded here. This
is a smoke comparison on short templates, not a rerun of the 1,919-label
extracted-location matrix. All four reports completed with no failed
documents. Aggregate artifacts are archived at:

- [Qwen standalone](../eval/baselines/local-qwen-smoke.json): 94/146 (64.4%); English 48/73 (65.8%), Finnish 46/73 (63.0%). Typed precision 100/150 (66.7%); 50 wrong-type overlaps, zero unlabelled detections. Detection averages 13.3 s per English document and 11.5 s per Finnish document.
- [Combined baseline on this exact corpus](../eval/baselines/local-combined-smoke.json): 136/146 (93.2%); English 70/73 (95.9%), Finnish 66/73 (90.4%). Typed precision 227/268 (84.7%). GLiNER ran on CPU.
- [Combined plus Qwen final pass](../eval/baselines/local-qwen-final-smoke.json): the same 136/146 correctly typed body labels; typed precision 227/271 (83.8%). The final pass added three Finnish `QUASI_IDENTIFIER` detections overlapping labels; these do not establish contextual identification accuracy. Detection including the base averages 2.4 s per English document and 1.1 s per Finnish document. The first English document includes lazy base-model initialization, so these averages are not steady-state benchmarks.

Qwen alone is weaker than the existing combination in this trial. Its final
pass did not recover additional correctly typed body identifiers. A labelled
contextual test is still needed before claiming that job/place or relationship
masking reduces re-identification. Per-type and language counts are in the
linked artifacts. Synthetic typed precision counts overlaps of the same type,
other-type overlaps, and unlabelled spans separately; it does not establish
whether an unlabelled quasi-identifier is useful or excessive masking.

[Gemma standalone](../eval/baselines/local-gemma-smoke.json) covered 111/146
(76.0%): English 61/73 (83.6%), Finnish 50/73 (68.5%). Typed precision was
116/139 (83.5%), with 23 wrong-type overlaps and zero unlabelled detections.
Detection averaged 12.9 s per English document and 10.8 s per Finnish document.
It found no whole addresses with the LOCATION type in either language. It
outperformed Qwen standalone here but remained below the combined baseline.
Gemma as a final pass and the full public-dataset matrix have not been run.

Official model references: [Qwen 3.5 9B](https://huggingface.co/Qwen/Qwen3.5-9B),
[Gemma 4 E4B](https://huggingface.co/google/gemma-4-E4B-it),
[Privacy Filter](https://huggingface.co/openai/privacy-filter),
[GLiNER2-PII](https://huggingface.co/fastino/gliner2-privacy-filter-PII-multi),
[GLiNER](https://huggingface.co/urchade/gliner_multi_pii-v1), and
[Stanza model catalog](https://stanfordnlp.github.io/stanza/available_models.html).
