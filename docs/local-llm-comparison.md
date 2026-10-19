# Local LLM comparison, 2026-10-19

Measured detector source: `e148240`. The fresh combined gate reproduced **136/146 body labels (93.2%)**, with zero failed documents, before any LLM inference. These are current runs. The earlier experiments in [local-model-options.md](local-model-options.md) remain archived pre-audit evidence.

All five configurations use the same frozen corpus: seed 42, `--n 1`, Faker 40.39.0, fourteen documents (seven English and seven Finnish), 146 body labels (73 per language). The generator also plants 46 non-body labels, excluded from body recall. Verified corpus SHA-256: `27934f5e7fc88d0748be7b53d2d79ecfd797ad82c94c68d6fa16fd421c2e40ae`. No extraction quality or public-AI re-identification result is claimed.

Whole-value typed recall requires one correctly typed span to cover every occurrence of each labelled value. Typed overlap precision counts detections touching a label of the same type; it includes any planted value occurring in the scored body text. W = overlaps only another labelled type; U = overlaps no label. Wrong-type overlaps are classification errors, not automatically excessive masking. An unlabelled contextual span is not automatically a false positive. `QUASI_IDENTIFIER` has no labelled privacy target in this corpus.

Each column links its exact aggregate source. R = covered/planted; P = correct/detections; W/U = wrong-type/unlabelled counts. A dash means no denominator, not a successful result.

| Scope | [Combined](../eval/baselines/final-evidence-local-combined.json) | [Qwen](../eval/baselines/final-evidence-local-qwen-alone.json) | [Gemma](../eval/baselines/final-evidence-local-gemma-alone.json) | [Combined + Qwen](../eval/baselines/final-evidence-local-qwen-final.json) | [Combined + Gemma](../eval/baselines/final-evidence-local-gemma-final.json) |
|---|---|---|---|---|---|
| All body labels | R 136/146 (2 partial); P 197/238; W/U 41/0 | R 94/146; P 100/150; W/U 50/0 | R 111/146 (1 partial); P 116/139; W/U 23/0 | R 136/146 (2 partial); P 197/241; W/U 44/0 | R 137/146 (1 partial); P 198/239; W/U 41/0 |
| English | R 70/73; P 99/128; W/U 29/0 | R 48/73; P 51/75; W/U 24/0 | R 61/73 (1 partial); P 65/76; W/U 11/0 | R 70/73; P 99/128; W/U 29/0 | R 70/73; P 99/128; W/U 29/0 |
| Finnish | R 66/73 (2 partial); P 98/110; W/U 12/0 | R 46/73; P 49/75; W/U 26/0 | R 50/73; P 51/63; W/U 12/0 | R 66/73 (2 partial); P 98/113; W/U 15/0 | R 67/73 (1 partial); P 99/111; W/U 12/0 |
| en/ADDRESS | R 6/6; P 6/7; W/U 1/0 | R 0/6; P —; W/U 0/0 | R 0/6; P —; W/U 0/0 | R 6/6; P 6/7; W/U 1/0 | R 6/6; P 6/7; W/U 1/0 |
| en/COMPANY | R 4/7; P 5/5; W/U 0/0 | R 6/7; P 9/9; W/U 0/0 | R 7/7; P 10/13; W/U 3/0 | R 4/7; P 5/5; W/U 0/0 | R 4/7; P 5/5; W/U 0/0 |
| en/DATE | R 11/11; P 22/30; W/U 8/0 | R 9/11; P 9/9; W/U 0/0 | R 11/11; P 11/11; W/U 0/0 | R 11/11; P 22/30; W/U 8/0 | R 11/11; P 22/30; W/U 8/0 |
| en/EMAIL | R 7/7; P 13/13; W/U 0/0 | R 6/7; P 6/6; W/U 0/0 | R 7/7; P 7/8; W/U 1/0 | R 7/7; P 13/13; W/U 0/0 | R 7/7; P 13/13; W/U 0/0 |
| en/IBAN | R 7/7; P 9/10; W/U 1/0 | R 2/7; P 2/2; W/U 0/0 | R 2/7; P 2/2; W/U 0/0 | R 7/7; P 9/10; W/U 1/0 | R 7/7; P 9/10; W/U 1/0 |
| en/INVOICE | R 5/5; P 5/5; W/U 0/0 | R 4/5; P 4/5; W/U 1/0 | R 5/5; P 5/7; W/U 2/0 | R 5/5; P 5/5; W/U 0/0 | R 5/5; P 5/5; W/U 0/0 |
| en/NRP | R —; P 0/3; W/U 3/0 | R —; P —; W/U 0/0 | R —; P —; W/U 0/0 | R —; P 0/3; W/U 3/0 | R —; P 0/3; W/U 3/0 |
| en/PERSON | R 13/13; P 13/15; W/U 2/0 | R 9/13; P 9/9; W/U 0/0 | R 13/13; P 13/15; W/U 2/0 | R 13/13; P 13/15; W/U 2/0 | R 13/13; P 13/15; W/U 2/0 |
| en/PERSONAL_ID | R 5/5; P 8/8; W/U 0/0 | R 4/5; P 4/7; W/U 3/0 | R 5/5; P 5/5; W/U 0/0 | R 5/5; P 8/8; W/U 0/0 | R 5/5; P 8/8; W/U 0/0 |
| en/PHONE | R 7/7; P 13/14; W/U 1/0 | R 6/7; P 6/11; W/U 5/0 | R 6/7 (1 partial); P 7/9; W/U 2/0 | R 7/7; P 13/14; W/U 1/0 | R 7/7; P 13/14; W/U 1/0 |
| en/PLATE | R 5/5; P 5/5; W/U 0/0 | R 2/5; P 2/2; W/U 0/0 | R 5/5; P 5/5; W/U 0/0 | R 5/5; P 5/5; W/U 0/0 | R 5/5; P 5/5; W/U 0/0 |
| en/QUASI_IDENTIFIER | R —; P —; W/U 0/0 | R —; P 0/15; W/U 15/0 | R —; P 0/1; W/U 1/0 | R —; P —; W/U 0/0 | R —; P —; W/U 0/0 |
| en/UK_NHS | R —; P 0/1; W/U 1/0 | R —; P —; W/U 0/0 | R —; P —; W/U 0/0 | R —; P 0/1; W/U 1/0 | R —; P 0/1; W/U 1/0 |
| en/URL | R —; P 0/7; W/U 7/0 | R —; P —; W/U 0/0 | R —; P —; W/U 0/0 | R —; P 0/7; W/U 7/0 | R —; P 0/7; W/U 7/0 |
| en/US_DRIVER_LICENSE | R —; P 0/5; W/U 5/0 | R —; P —; W/U 0/0 | R —; P —; W/U 0/0 | R —; P 0/5; W/U 5/0 | R —; P 0/5; W/U 5/0 |
| fi/ADDRESS | R 5/6 (1 partial); P 6/6; W/U 0/0 | R 2/6; P 2/2; W/U 0/0 | R 0/6; P —; W/U 0/0 | R 5/6 (1 partial); P 6/6; W/U 0/0 | R 5/6 (1 partial); P 6/6; W/U 0/0 |
| fi/COMPANY | R 2/7 (1 partial); P 4/4; W/U 0/0 | R 5/7; P 8/8; W/U 0/0 | R 2/7; P 3/4; W/U 1/0 | R 2/7 (1 partial); P 4/4; W/U 0/0 | R 3/7; P 5/5; W/U 0/0 |
| fi/DATE | R 11/11; P 21/21; W/U 0/0 | R 7/11; P 7/7; W/U 0/0 | R 11/11; P 11/11; W/U 0/0 | R 11/11; P 21/21; W/U 0/0 | R 11/11; P 21/21; W/U 0/0 |
| fi/EMAIL | R 7/7; P 14/14; W/U 0/0 | R 5/7; P 5/5; W/U 0/0 | R 7/7; P 7/7; W/U 0/0 | R 7/7; P 14/14; W/U 0/0 | R 7/7; P 14/14; W/U 0/0 |
| fi/IBAN | R 7/7; P 9/10; W/U 1/0 | R 5/7; P 5/5; W/U 0/0 | R 3/7; P 3/3; W/U 0/0 | R 7/7; P 9/10; W/U 1/0 | R 7/7; P 9/10; W/U 1/0 |
| fi/INVOICE | R 5/5; P 5/5; W/U 0/0 | R 3/5; P 3/3; W/U 0/0 | R 5/5; P 5/7; W/U 2/0 | R 5/5; P 5/5; W/U 0/0 | R 5/5; P 5/5; W/U 0/0 |
| fi/PERSON | R 12/13; P 12/14; W/U 2/0 | R 8/13; P 8/8; W/U 0/0 | R 5/13; P 5/7; W/U 2/0 | R 12/13; P 12/14; W/U 2/0 | R 12/13; P 12/14; W/U 2/0 |
| fi/PERSONAL_ID | R 5/5; P 9/9; W/U 0/0 | R 3/5; P 3/3; W/U 0/0 | R 5/5; P 5/9; W/U 4/0 | R 5/5; P 9/9; W/U 0/0 | R 5/5; P 9/9; W/U 0/0 |
| fi/PHONE | R 7/7; P 13/15; W/U 2/0 | R 5/7; P 5/7; W/U 2/0 | R 7/7; P 7/7; W/U 0/0 | R 7/7; P 13/15; W/U 2/0 | R 7/7; P 13/15; W/U 2/0 |
| fi/PLATE | R 5/5; P 5/5; W/U 0/0 | R 3/5; P 3/3; W/U 0/0 | R 5/5; P 5/5; W/U 0/0 | R 5/5; P 5/5; W/U 0/0 | R 5/5; P 5/5; W/U 0/0 |
| fi/QUASI_IDENTIFIER | R —; P —; W/U 0/0 | R —; P 0/24; W/U 24/0 | R —; P 0/3; W/U 3/0 | R —; P 0/3; W/U 3/0 | R —; P —; W/U 0/0 |
| fi/URL | R —; P 0/7; W/U 7/0 | R —; P —; W/U 0/0 | R —; P —; W/U 0/0 | R —; P 0/7; W/U 7/0 | R —; P 0/7; W/U 7/0 |
| Reported detector call s/document, en | 1.644 | 14.431 | 14.062 | 0.970 | 0.540 |
| Reported detector call s/document, fi | 0.184 | 14.532 | 11.829 | 1.430 | 0.649 |
| Reported detector call s, 14 documents | 12.796 | 202.745 | 181.232 | 16.800 | 8.321 |
| Staged s including base construction, excluding LLM load | 19.874 | 202.745 | 181.232 | 36.675 | 28.196 |
| Failed documents | 0 | 0 | 0 | 0 | 0 |

The base cache replay gives the final pass exactly the original base spans and masking. GLiNER ran offline on CPU in a separate process that exited before loading an LLM. Its cache verifies corpus, method and detector-source hashes. The combined baseline/cache ran while pack preparation was active on the same host; its timing is approximate under background load. LLM inference started after pack preparation exited. These timings support practical cost estimates, not a controlled speed ranking.

The reported baseline detector calls include lazy GLiNER loading in the first English document; spaCy/construction took 7.078 s separately. LLM reports exclude model loading. Final-pass detector-call timings include cached-span replay and LLM requests; the staged row adds the original base construction and detector calls. No extraction is timed. Standalone precedes the final pass for each loaded model, so warmup conditions differ.

Both cached models use LM Studio 0.4.18+1 with MLX 4-bit weights on this 16 GiB Apple host: `qwen/qwen3.5-9b` (5,977,257,833 bytes) and `google/gemma-4-e4b` (6,861,915,950 bytes). Each loads at 8192-token context and one parallel prediction. The first Qwen load took 12.542 s; the Gemma load took 13.445 s. These are CLI wall times with cached weights, not cold-download or minimum-RAM measurements. Peak RAM/VRAM was not measured. Exactly one LLM was loaded at a time, without GLiNER.

Temperature is 0; `reasoning_effort=none`, `enable_thinking=false`, JSON-schema entities, maximum 2048 output tokens, 4000-character windows with 400-character overlap. The exact system prompt, schema, user-prompt template, quantization, loaded-state records and load commands are in [configuration](../eval/baselines/final-evidence-local-configuration.json). Final passes replace base spans with equal-length blocks before inference and retain the original spans. Requests go only to `127.0.0.1:1234`; proxies and redirects are disabled.

The first Qwen transport attempt found the HTTP server stopped: fourteen `URLError` rows, **model inference NOT RUN**. This [preserved attempt](../eval/baselines/final-evidence-local-qwen-server-down.json) is excluded from the completed quality table. Starting the loopback server and repeating produced the current Qwen report. Completed-run error classes remain in every report.

## Final-pass verdict

Qwen's final pass shows no demonstrated recall gain: 136/146 (+0 labels), typed precision 81.7% versus 82.8% for combined, 44 wrong-type overlaps and 0 unlabelled detections, with 0 failed documents. Gemma's final pass helps typed body recall: 137/146 (+1 labels), typed precision 82.8% versus 82.8% for combined, 41 wrong-type overlaps and 0 unlabelled detections, with 0 failed documents. These counts do not establish contextual re-identification protection. Usefulness is evaluated separately in [the utility rerun](utility-impact.md#2026-10-19-rerun).

## Reproduce

Use already cached weights and the project virtual environment. Never run the original simultaneous `combined`/LLM path on this host: create the base cache first and let that process exit.

```bash
python corpus/generate.py --out outputs/local-corpus --n 1 --seed 42
HF_HUB_OFFLINE=1 GLINER_DEVICE=cpu python -m eval.local_base_cache outputs/local-corpus \
  --method combined --out outputs/final-evidence-local/combined-cache.json
lms server start --bind 127.0.0.1 --port 1234
lms load qwen/qwen3.5-9b --context-length 8192 --parallel 1 --identifier qwen-local --yes
HF_HUB_OFFLINE=1 GLINER_DEVICE=cpu python -m eval.local_llm_bench outputs/local-corpus \
  --model qwen-local --out outputs/final-evidence-local/qwen-alone.json
HF_HUB_OFFLINE=1 GLINER_DEVICE=cpu python -m eval.local_llm_bench outputs/local-corpus \
  --model qwen-local --base-method combined --base-cache outputs/final-evidence-local/combined-cache.json \
  --out outputs/final-evidence-local/qwen-final.json
lms unload qwen-local
lms load google/gemma-4-e4b --context-length 8192 --parallel 1 --identifier gemma-local --yes
HF_HUB_OFFLINE=1 GLINER_DEVICE=cpu python -m eval.local_llm_bench outputs/local-corpus \
  --model gemma-local --out outputs/final-evidence-local/gemma-alone.json
HF_HUB_OFFLINE=1 GLINER_DEVICE=cpu python -m eval.local_llm_bench outputs/local-corpus \
  --model gemma-local --base-method combined --base-cache outputs/final-evidence-local/combined-cache.json \
  --out outputs/final-evidence-local/gemma-final.json
lms unload gemma-local
```

Use a new cache/output path on a repeat. Reports contain aggregates only. Corpus text, cached offsets and raw local responses remain under ignored `outputs/`. The archived pre-audit and 885-document matrix results are separate evidence, with different metrics and denominators.
