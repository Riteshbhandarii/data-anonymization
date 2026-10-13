# Dataset runs

Every free detection method over every dataset we have. Aggregate numbers only:
the anonymized outputs and the manual-test pack are built locally and never
committed.

Reproduce:

```bash
export PATH="/opt/homebrew/bin:$PATH"
python -m eval.run_matrix --out outputs/runs --tab-docs 0   # fake, tab, turku, ai4privacy, real-uk
python -m eval.make_pack --runs outputs/runs --pack outputs/pack
```

`--datasets` and `--methods` rerun a subset and merge into the existing CSVs.
`--tab-docs 0` scores the whole TAB test split (127 documents); the default is
a 40-document sample. The `gliner` and `combined` methods need
`pip install gliner` and a one-time model download
(`urchade/gliner_multi_pii-v1`, weights only; no text leaves the machine). It
picks cuda, then mps, then cpu; `GLINER_DEVICE` overrides.

Methods: `basic` (Presidio, small spaCy), `rules` (+ our patterns), `rules-lg`
(+ large spaCy), `gliner` (GLiNER plus the same three patterns), `combined`
(every GLiNER span, plus `rules` without its spaCy PERSON, ORGANIZATION and
LOCATION; see `detect/combined.py`).

Scoring is whole-value: a mention counts only if one correctly typed detection
holds all of it; partial detections are recorded separately and still leak.
Type mappings for TAB, Turku and ai4privacy are at the top of `eval/run_matrix.py`.

## Headline recall

| dataset | basic | rules | rules-lg | gliner | combined |
|---|---|---|---|---|---|
| fake, all locations | 61.4% (1178/1919) | 80.0% (1536/1919) | 84.2% (1615/1919) | 86.9% (1668/1919) | 95.9% (1840/1919) |
| fake, body only | 59.9% (874/1459) | 80.3% (1172/1459) | 83.1% (1212/1459) | 87.3% (1274/1459) | 96.2% (1404/1459) |
| tab, all masked mentions | 65.4% (3344/5112) | 65.4% (3344/5112) | 67.7% (3463/5112) | 70.7% (3616/5112) | 81.1% (4147/5112) |
| tab, DIRECT | 8.6% (32/374) | 8.6% (32/374) | 15.0% (56/374) | 61.0% (228/374) | 61.2% (229/374) |
| tab, QUASI | 69.9% (3312/4738) | 69.9% (3312/4738) | 71.9% (3407/4738) | 71.5% (3388/4738) | 82.7% (3918/4738) |
| turku (fi names, orgs, places, dates) | 51.0% (51/100) | 51.0% (51/100) | 77.0% (77/100) | 76.0% (76/100) | 76.0% (76/100) |
| ai4privacy, en | 54.2% (1076/1986) | 54.2% (1076/1986) | 58.1% (1154/1986) | 75.9% (1507/1986) | 87.7% (1741/1986) |
| ai4privacy, fi | 38.7% (756/1953) | 42.1% (822/1953) | 46.7% (912/1953) | 79.0% (1543/1953) | 82.5% (1611/1953) |

TAB is the whole test split (127 documents, 5112 masked mentions).

## Precision

Share of detections that overlap an annotation of any type. Only the
span-labelled datasets have one. These datasets leave some personal data
unannotated, so a detection over nothing is not always a mistake, and the
numbers are a lower bound on precision. The fake corpus is measured by
`eval/bench.py` instead; its counting rule and results are in
[eval/README.md](../eval/README.md#precision).

| dataset | basic | rules | rules-lg | gliner | combined |
|---|---|---|---|---|---|
| tab, en | 81.0% (6511/8035) | 81.0% (6511/8035) | 82.3% (6529/7930) | 61.7% (5336/8655) | 69.7% (8277/11868) |
| turku, fi | 53.0% (70/132) | 53.0% (70/132) | 59.3% (89/150) | 34.0% (86/253) | 29.7% (88/296) |
| ai4privacy, en | 89.5% (2029/2266) | 89.5% (2029/2266) | 90.8% (1884/2074) | 84.1% (1108/1318) | 89.8% (2627/2927) |
| ai4privacy, fi | 86.7% (1288/1486) | 87.5% (1391/1589) | 92.0% (1454/1580) | 88.8% (1241/1398) | 90.9% (1976/2173) |

## Findings

- The combined detector has the best recall on every labelled set except Turku:
  fake 95.9% (GLiNER 86.9%, rules 80.0%), TAB 81.1% (70.7%, 65.4%), ai4privacy
  en 87.7% (75.9%) and fi 82.5% (79.0%). Each family covers the other's gaps:
  fake IBAN 97.5% (GLiNER alone 25%), TAB DATE 97.1% (79.0%), embedded image
  text 92.5% (42.5%), ai4privacy PASSPORTNUM 61.8% (15.7%) and SOCIALNUM 100%
  (59.8%) from Presidio; ADDRESS, STREET, CITY and PERSON from GLiNER.
- On Turku the combined detector equals GLiNER (76%). The large spaCy models
  still do better there on places (31/38 against 27/38) and companies (17/23
  against 10/23), and the combined detector uses the small ones.
- Precision costs something. On TAB the combined detector keeps 69.7% of its
  detections on an annotation, between GLiNER (61.7%) and Presidio (81.0%); on
  ai4privacy it matches Presidio (about 90%). On Turku it is the lowest
  (29.7%).
- GLiNER's unannotated detections are mostly real over-redaction, not
  personal data the annotators missed. In the earlier 40-document TAB sample,
  317 of its 570 PERSON detections over no annotation were the word
  "applicant", followed by "applicants", "landlord", "he" and "defendant", and
  its ORGANIZATION ones were mostly "Court", "Government" and "Chamber". On
  Turku they are words like "tyttö", "nainen" and "komissio". Presidio's are
  mostly "Court" as ORGANIZATION and phrases like "the same day" as DATE_TIME.
- TAB on the whole test split: DIRECT identifiers stay at 61% for GLiNER and
  the combined detector. They are 233 PERSON mentions, of which the combined
  detector finds 226 (97%), and 140 CODE mentions (case and application
  numbers), of which it finds 3. QUASI identifiers go from 70-72% for single
  methods to 82.7% combined. Against the earlier 40-document sample, the
  all-mentions figures moved by at most 1.6 points; Presidio's DIRECT figures
  moved more (5.0% to 8.6% basic, 10.0% to 15.0% large models), since the
  sample held only 120 DIRECT mentions.
- Presidio's NRP is kept in the combined detector because GLiNER has no such
  label: without it TAB DEM recall falls from 44% to 26%.
- TAB CODE (case numbers) and QUANTITY are still near 0% for every method.
- On real-uk (public petroleum and statistics spreadsheets, no labels) the
  combined detector returns 74 403 detections, against 24 431 for GLiNER.
  Presidio's US_DRIVER_LICENSE (15 130) and US_BANK_NUMBER (9 938) patterns fire
  on numeric columns, and these are almost certainly not personal data. The
  same patterns are what lift the ai4privacy ID classes, so they trade one for
  the other.
- Large spaCy models help Finnish and companies (Turku 51% to 77%) but not
  codes and numbers.

## Runtime (detection only)

The combined detector costs GLiNER plus Presidio: 22 s for the 140 fake
documents, 146 s for the 127 TAB documents and 61 s for the 600 ai4privacy
rows, against 21, 143 and 55 s for GLiNER and 4, 25 and 11 s for Presidio. The
17 real-uk files (2.0 M characters after truncation) take 781 s combined, 557 s
GLiNER and 207 to 249 s Presidio. Extraction runs once per dataset and is
shared by all methods (fake 24 s with OCR, real-uk 31 s). GLiNER runs on MPS.
The machine was running other jobs during these runs, and the Presidio times
roughly doubled against the first run, so treat timings as rough.

## Caveats

- Fake data is template text and an upper bound. Pattern types score well by
  construction because the patterns were written for the generator.
- TAB, Turku and ai4privacy label different things, so cross-dataset numbers are
  not comparable.
- Types without a Presidio counterpart accept a detection of any type, which
  flatters them, and flatters the method with the most detections most.
- Samples: TAB the whole test split (127 documents), Turku test files up to 300
  sentences (18 files, 100 mentions), ai4privacy 300 random rows per language.
- real-uk has 17 files in its manifest (not 18), none missing. It has no labels,
  so only detection counts exist. Two spreadsheets over 400 000 characters are
  truncated to that length. Only the combined detector was rerun on it; the
  other methods' real-uk counts are from the first run.
