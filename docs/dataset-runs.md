# Dataset runs

Every free detection method over every dataset we have. Aggregate numbers only:
the anonymized outputs and the manual-test pack are built locally and never
committed.

Reproduce:

```bash
export PATH="/opt/homebrew/bin:$PATH"
python -m eval.run_matrix --out outputs/runs      # fake, tab, turku, ai4privacy, real-uk
python -m eval.make_pack --runs outputs/runs --pack outputs/pack
```

`--datasets` and `--methods` rerun a subset and merge into the existing CSVs.
The `gliner` method needs `pip install gliner` and a one-time model download
(`urchade/gliner_multi_pii-v1`, weights only; no text leaves the machine). It
picks cuda, then mps, then cpu; `GLINER_DEVICE` overrides.

Methods: `basic` (Presidio, small spaCy), `rules` (+ our patterns), `rules-lg`
(+ large spaCy), `gliner` (GLiNER plus the same three patterns).

Scoring is whole-value: a mention counts only if one correctly typed detection
holds all of it; partial detections are recorded separately and still leak.
Type mappings for TAB, Turku and ai4privacy are at the top of `eval/run_matrix.py`.

## Headline recall

| dataset | basic | rules | rules-lg | gliner |
|---|---|---|---|---|
| fake, all locations | 61.4% (1178/1919) | 80.0% (1536/1919) | 84.2% (1615/1919) | 86.9% (1668/1919) |
| fake, body only | 59.9% (874/1459) | 80.3% (1172/1459) | 83.1% (1212/1459) | 87.3% (1274/1459) |
| tab, all masked mentions | 63.9% (956/1497) | 63.9% (956/1497) | 66.1% (989/1497) | 70.7% (1059/1497) |
| tab, DIRECT | 5.0% (6/120) | 5.0% (6/120) | 10.0% (12/120) | 62.5% (75/120) |
| tab, QUASI | 69.0% (950/1377) | 69.0% (950/1377) | 71.0% (977/1377) | 71.5% (984/1377) |
| turku (fi names, orgs, places, dates) | 51.0% (51/100) | 51.0% (51/100) | 77.0% (77/100) | 76.0% (76/100) |
| ai4privacy, en | 54.2% (1076/1986) | 54.2% (1076/1986) | 58.1% (1154/1986) | 75.9% (1507/1986) |
| ai4privacy, fi | 38.7% (756/1953) | 42.1% (822/1953) | 46.7% (912/1953) | 79.0% (1543/1953) |


## Findings

- GLiNER is clearly better on names, companies and addresses. Fake PERSON 98%
  (basic 82%), ADDRESS 96% (Presidio 0%), COMPANY 70% (26-33%). On TAB, PERSON
  recall is 96.5% against 28-31% for Presidio, which lifts DIRECT identifiers from
  5-10% to 62.5%. On Turku, Finnish PERSON is 37/37 against 17/37 (sm) and 27/37 (lg).
- GLiNER is worse on formatted values. Fake IBAN 25% (Presidio 97.5%), DATE 88%
  (100%), EMAIL 88% (97%). On TAB, DATE 80% against 94-98%. Presidio's patterns
  and GLiNER are complementary, which is the case for combining them.
- Embedded image text (OCR) is GLiNER's weak spot in the fake corpus: 42.5% against
  92.5% for Presidio. Headers and tracked changes are weak for every method.
- Presidio's built-in recognizers miss most Finnish PII (ai4privacy fi 39% basic,
  47% large models, GLiNER 79%).
- Our patterns matter: hidden sheets go from 0% to 67% and INVOICE, PLATE,
  PERSONAL_ID from 0% to ~100%, though by construction (see caveats).
- TAB CODE (case numbers), DEM and QUANTITY are near 0% for every method.
- Large spaCy models help Finnish and companies (Turku 51% to 77%) but not
  codes and numbers.

## Runtime (detection only)

Presidio methods take 2 to 6 seconds for the 140 fake documents and 600
ai4privacy rows. GLiNER takes 20 and 56 seconds on the same sets. The 17
real-uk files (2.0 M characters after truncation) take 207 to 249 s with
Presidio and 557 s with GLiNER. Extraction runs once per dataset and is shared
by all methods (fake 24 s with OCR, real-uk 33 s). GLiNER on MPS gave
detections identical to CPU on nine documents and was about 1.25 times
faster (6.8 s against 8.5 s).

## Caveats

- Fake data is template text and an upper bound. Pattern types score well by
  construction because the patterns were written for the generator.
- TAB, Turku and ai4privacy label different things, so cross-dataset numbers are
  not comparable.
- Types without a Presidio counterpart accept a detection of any type, which
  flatters them.
- Samples: TAB test split every third document (40), Turku test files up to 300
  sentences (18 files, 100 mentions), ai4privacy 300 random rows per language.
- real-uk has 17 files in its manifest (not 18), none missing. It has no labels,
  so only detection counts exist. Two spreadsheets over 400 000 characters are
  truncated to that length.
