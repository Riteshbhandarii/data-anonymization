# Dataset audit runs

[Docs index](README.md) › RQ2

How well do seven detectors find labelled personal data in English and Finnish? All seven ran offline on the same 885 documents on 2026-10-14: 140 synthetic Office and image files, the 127-document TAB test split, 18 Turku test documents, and 300 ai4privacy rows per language. Each method scores 11,070 labelled values or mentions.

## Key result

Recall of `combined`, which is highest or tied for highest on every dataset:

- Synthetic corpus: 1,849/1,919 (96.4%)
- TAB court cases: 4,269/5,112 (83.5%)
- Turku Finnish: 80/100
- ai4privacy: English 1,757/1,986 (88.5%), Finnish 1,636/1,953 (83.8%)
- Privacy Filter covers none of the selected Turku mentions. GLiNER2 ties `combined` at 83.8% on ai4privacy Finnish.

Datasets label different things, so these numbers are not comparable across rows. Recall is whole-value: one accepted detection must contain the full value or mention. Partial detections are counted separately and can still leave identifying text visible.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/rq2-recall-dark.svg">
  <img alt="Bar chart: combined finds 96.4% synthetic, 83.5% TAB, 80.0% Turku, 88.5% ai4privacy English, 83.8% ai4privacy Finnish; basic Presidio 61.4%, 65.4%, 51.0%, 54.2%, 38.7%." src="figures/rq2-recall-light.svg" width="720">
</picture>

## Comparison with the archived run

Compared with the [archived dataset tables](archive/dataset-runs.md), `combined` now covers 122 more TAB mentions (4,269 versus 4,147) and 80/100 Turku mentions versus 76/100. Its lower-bound precision is 63.7% on TAB and 26.5% on Turku, down from the archived 69.7% and 29.7%. More complete detection leaves many unlabelled detections to assess. The annotations are incomplete, so these are not all proven false positives. GLiNER and `combined` reach 80% on Turku versus GLiNER2's 78%. Keep the dataset-specific tradeoffs in view when choosing a method.

This rerun supersedes the archived accuracy comparisons for the listed selections. Unlabelled real-uk timing and detection counts, the earlier Qwen/Gemma trials and the public-model privacy experiment are outside this run.

## Details

- Measured source: commit `10d49c1` (branch `audit/corrected-matrix-source`), the corrected code before it was squash-merged. Main differs only in description text (method notes in `detect/methods.py`, summary wording in `eval/run_matrix.py`), which changes presentation, not results.
- Corpus hashes, selections, package versions, grouped results, precision denominators and timings are archived in [`eval/baselines/dataset-audit-matrix.json`](../eval/baselines/dataset-audit-matrix.json). Raw documents, model inputs, entity values and source identities are not in that archive.
- All 28 method/dataset runs completed; model failures would stop this runner. Model weights were cached. No remote request or paid API was used.
- GLiNER and `combined` use MPS; spaCy, Privacy Filter and GLiNER2 use CPU. Timings exclude model loading and are specific to this host and cached process. The `load s` column times warmup only, so it is not a complete cold-start measurement.
- Lower-bound precision accepts overlap with any annotated type. It differs from the typed precision in the fourteen-document run in [local-llm-comparison.md](local-llm-comparison.md).
- Real-document hand labels were not produced. Public-AI re-identification is in [public-ai-results.md](public-ai-results.md).

## Headline recall

| dataset | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| fake, all locations | 61.4% (1178/1919) | 80.0% (1536/1919) | 84.2% (1615/1919) | 89.9% (1725/1919) | 96.4% (1849/1919) | 82.4% (1582/1919) | 94.3% (1809/1919) |
| fake, body only | 59.9% (874/1459) | 80.3% (1172/1459) | 83.1% (1212/1459) | 89.1% (1300/1459) | 96.2% (1404/1459) | 80.2% (1170/1459) | 94.3% (1376/1459) |
| tab, all masked mentions | 65.4% (3344/5112) | 65.4% (3344/5112) | 67.7% (3463/5112) | 76.4% (3906/5112) | 83.5% (4269/5112) | 28.6% (1461/5112) | 67.2% (3434/5112) |
| tab, DIRECT | 8.6% (32/374) | 8.6% (32/374) | 15.0% (56/374) | 61.8% (231/374) | 62.0% (232/374) | 48.9% (183/374) | 25.4% (95/374) |
| tab, QUASI | 69.9% (3312/4738) | 69.9% (3312/4738) | 71.9% (3407/4738) | 77.6% (3675/4738) | 85.2% (4037/4738) | 27.0% (1278/4738) | 70.5% (3339/4738) |
| turku (fi names, orgs, places, dates) | 51.0% (51/100) | 51.0% (51/100) | 77.0% (77/100) | 80.0% (80/100) | 80.0% (80/100) | 0.0% (0/100) | 78.0% (78/100) |
| ai4privacy, en | 54.2% (1076/1986) | 54.2% (1076/1986) | 58.1% (1154/1986) | 77.9% (1547/1986) | 88.5% (1757/1986) | 80.6% (1600/1986) | 83.0% (1648/1986) |
| ai4privacy, fi | 38.7% (756/1953) | 42.1% (822/1953) | 46.7% (912/1953) | 80.6% (1575/1953) | 83.8% (1636/1953) | 63.4% (1238/1953) | 83.8% (1636/1953) |

## Precision (share of detections that hit an annotation)

Only the span-labelled datasets. A detection over no annotation of any type counts against the method; some are unannotated personal data, so this is a lower bound on precision.

| dataset | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| tab, en | 81.0% (6511/8035) | 81.0% (6511/8035) | 82.3% (6529/7930) | 55.7% (6221/11175) | 63.7% (9162/14388) | 98.4% (1562/1587) | 65.5% (6678/10190) |
| turku, fi | 52.2% (70/134) | 52.2% (70/134) | 58.2% (89/153) | 29.1% (102/350) | 26.5% (104/393) | - | 48.7% (95/195) |
| ai4privacy, en | 89.5% (2029/2266) | 89.5% (2029/2266) | 90.8% (1884/2074) | 78.6% (1175/1495) | 86.8% (2694/3104) | 99.3% (1325/1334) | 89.1% (1453/1631) |
| ai4privacy, fi | 86.7% (1288/1486) | 87.5% (1391/1589) | 92.0% (1454/1580) | 84.5% (1324/1566) | 88.0% (2059/2341) | 94.3% (1240/1315) | 91.8% (1545/1683) |

## Fake corpus by entity type (all locations)

| entity_type | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| ADDRESS | 0.0% (0/139) | 0.0% (0/139) | 0.0% (0/139) | 95.7% (133/139) | 95.7% (133/139) | 43.9% (61/139) | 61.2% (85/139) |
| COMPANY | 26.2% (42/160) | 26.2% (42/160) | 33.1% (53/160) | 69.4% (111/160) | 69.4% (111/160) | 0.0% (0/160) | 80.0% (128/160) |
| DATE | 100.0% (220/220) | 100.0% (220/220) | 100.0% (220/220) | 99.1% (218/220) | 100.0% (220/220) | 92.7% (204/220) | 100.0% (220/220) |
| EMAIL | 96.7% (232/240) | 96.7% (232/240) | 96.7% (232/240) | 96.7% (232/240) | 96.7% (232/240) | 96.2% (231/240) | 96.7% (232/240) |
| IBAN | 97.5% (156/160) | 97.5% (156/160) | 97.5% (156/160) | 25.0% (40/160) | 97.5% (156/160) | 95.6% (153/160) | 94.4% (151/160) |
| INVOICE | 0.0% (0/100) | 100.0% (100/100) | 100.0% (100/100) | 100.0% (100/100) | 100.0% (100/100) | 100.0% (100/100) | 100.0% (100/100) |
| PERSON | 82.3% (395/480) | 82.3% (395/480) | 96.5% (463/480) | 100.0% (480/480) | 100.0% (480/480) | 92.7% (445/480) | 99.0% (475/480) |
| PERSONAL_ID | 0.0% (0/140) | 98.6% (138/140) | 98.6% (138/140) | 98.6% (138/140) | 98.6% (138/140) | 98.6% (138/140) | 98.6% (138/140) |
| PHONE | 83.1% (133/160) | 83.1% (133/160) | 83.1% (133/160) | 95.6% (153/160) | 99.4% (159/160) | 81.2% (130/160) | 100.0% (160/160) |
| PLATE | 0.0% (0/120) | 100.0% (120/120) | 100.0% (120/120) | 100.0% (120/120) | 100.0% (120/120) | 100.0% (120/120) | 100.0% (120/120) |

## Fake corpus by location

| location | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| body | 59.9% (874/1459) | 80.3% (1172/1459) | 83.1% (1212/1459) | 89.1% (1300/1459) | 96.2% (1404/1459) | 80.2% (1170/1459) | 94.3% (1376/1459) |
| comment | 95.0% (38/40) | 95.0% (38/40) | 100.0% (40/40) | 100.0% (40/40) | 100.0% (40/40) | 100.0% (40/40) | 100.0% (40/40) |
| embedded_image | 92.5% (37/40) | 92.5% (37/40) | 92.5% (37/40) | 92.5% (37/40) | 92.5% (37/40) | 92.5% (37/40) | 92.5% (37/40) |
| footer | 75.0% (15/20) | 75.0% (15/20) | 90.0% (18/20) | 100.0% (20/20) | 100.0% (20/20) | 100.0% (20/20) | 95.0% (19/20) |
| header | 15.0% (3/20) | 15.0% (3/20) | 0.0% (0/20) | 40.0% (8/20) | 40.0% (8/20) | 0.0% (0/20) | 40.0% (8/20) |
| hidden_sheet | 0.0% (0/60) | 66.7% (40/60) | 66.7% (40/60) | 100.0% (60/60) | 100.0% (60/60) | 83.3% (50/60) | 83.3% (50/60) |
| metadata | 81.7% (147/180) | 81.7% (147/180) | 97.8% (176/180) | 100.0% (180/180) | 100.0% (180/180) | 93.9% (169/180) | 99.4% (179/180) |
| notes | 68.8% (55/80) | 93.8% (75/80) | 95.0% (76/80) | 75.0% (60/80) | 100.0% (80/80) | 95.0% (76/80) | 100.0% (80/80) |
| tracked_change | 45.0% (9/20) | 45.0% (9/20) | 80.0% (16/20) | 100.0% (20/20) | 100.0% (20/20) | 100.0% (20/20) | 100.0% (20/20) |

## Fake corpus by language

| language | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| en | 65.1% (624/959) | 83.6% (802/959) | 84.6% (811/959) | 89.5% (858/959) | 95.8% (919/959) | 87.3% (837/959) | 92.7% (889/959) |
| fi | 57.7% (554/960) | 76.5% (734/960) | 83.8% (804/960) | 90.3% (867/960) | 96.9% (930/960) | 77.6% (745/960) | 95.8% (920/960) |

## Fake corpus by format

| format | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| csv | 52.2% (94/180) | 74.4% (134/180) | 77.8% (140/180) | 95.0% (171/180) | 95.0% (171/180) | 79.4% (143/180) | 94.4% (170/180) |
| docx | 63.0% (252/400) | 78.0% (312/400) | 84.5% (338/400) | 90.0% (360/400) | 95.0% (380/400) | 85.8% (343/400) | 93.2% (373/400) |
| pdf | 66.9% (200/299) | 87.0% (260/299) | 89.0% (266/299) | 92.0% (275/299) | 98.7% (295/299) | 82.9% (248/299) | 97.0% (290/299) |
| png | 55.8% (268/480) | 80.4% (386/480) | 82.7% (397/480) | 86.7% (416/480) | 95.6% (459/480) | 79.8% (383/480) | 91.9% (441/480) |
| pptx | 67.0% (201/300) | 80.3% (241/300) | 84.7% (254/300) | 84.0% (252/300) | 97.3% (292/300) | 82.3% (247/300) | 95.7% (287/300) |
| xlsx | 62.7% (163/260) | 78.1% (203/260) | 84.6% (220/260) | 96.5% (251/260) | 96.9% (252/260) | 83.8% (218/260) | 95.4% (248/260) |

## TAB by entity type (masked mentions)

| entity_type | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| ADDRESS | 68.8% (231/336) | 68.8% (231/336) | 69.3% (233/336) | 88.7% (298/336) | 88.7% (298/336) | 1.5% (5/336) | 88.4% (297/336) |
| CODE | 9.1% (30/329) | 9.1% (30/329) | 4.3% (14/329) | 0.9% (3/329) | 7.9% (26/329) | 0.6% (2/329) | 7.9% (26/329) |
| COMPANY | 62.9% (363/577) | 62.9% (363/577) | 66.0% (381/577) | 80.2% (463/577) | 80.2% (463/577) | 0.0% (0/577) | 79.5% (459/577) |
| DATE | 94.5% (2319/2454) | 94.5% (2319/2454) | 97.3% (2387/2454) | 85.9% (2109/2454) | 97.5% (2392/2454) | 30.4% (747/2454) | 89.6% (2200/2454) |
| DEM | 44.9% (75/167) | 44.9% (75/167) | 44.9% (75/167) | 20.4% (34/167) | 53.3% (89/167) | 3.6% (6/167) | 10.2% (17/167) |
| MISC | 18.1% (26/144) | 18.1% (26/144) | 18.8% (27/144) | 38.2% (55/144) | 39.6% (57/144) | 16.0% (23/144) | 25.0% (36/144) |
| PERSON | 30.2% (287/951) | 30.2% (287/951) | 36.2% (344/951) | 98.1% (933/951) | 98.1% (933/951) | 71.3% (678/951) | 41.9% (398/951) |
| QUANTITY | 8.4% (13/154) | 8.4% (13/154) | 1.3% (2/154) | 7.1% (11/154) | 7.1% (11/154) | 0.0% (0/154) | 0.6% (1/154) |

## TAB by identifier type

| identifier_type | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| DIRECT | 8.6% (32/374) | 8.6% (32/374) | 15.0% (56/374) | 61.8% (231/374) | 62.0% (232/374) | 48.9% (183/374) | 25.4% (95/374) |
| QUASI | 69.9% (3312/4738) | 69.9% (3312/4738) | 71.9% (3407/4738) | 77.6% (3675/4738) | 85.2% (4037/4738) | 27.0% (1278/4738) | 70.5% (3339/4738) |

## Turku by entity type

| entity_type | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| ADDRESS | 60.5% (23/38) | 60.5% (23/38) | 81.6% (31/38) | 78.9% (30/38) | 78.9% (30/38) | 0.0% (0/38) | 81.6% (31/38) |
| COMPANY | 39.1% (9/23) | 39.1% (9/23) | 73.9% (17/23) | 47.8% (11/23) | 47.8% (11/23) | 0.0% (0/23) | 52.2% (12/23) |
| DATE | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 0.0% (0/2) | 100.0% (2/2) |
| PERSON | 45.9% (17/37) | 45.9% (17/37) | 73.0% (27/37) | 100.0% (37/37) | 100.0% (37/37) | 0.0% (0/37) | 89.2% (33/37) |

## ai4privacy by entity type

| entity_type | basic | rules | rules-lg | gliner | combined | privacy-filter | gliner2 |
|---|---|---|---|---|---|---|---|
| AGE | 35.6% (84/236) | 35.6% (84/236) | 43.6% (103/236) | 5.5% (13/236) | 37.7% (89/236) | 6.8% (16/236) | 5.9% (14/236) |
| BUILDINGNUM | 23.3% (49/210) | 23.3% (49/210) | 12.4% (26/210) | 92.4% (194/210) | 93.8% (197/210) | 54.3% (114/210) | 75.2% (158/210) |
| CITY | 22.7% (66/291) | 22.7% (66/291) | 36.4% (106/291) | 90.7% (264/291) | 90.7% (264/291) | 39.2% (114/291) | 86.6% (252/291) |
| CREDITCARD | 3.4% (5/145) | 3.4% (5/145) | 3.4% (5/145) | 45.5% (66/145) | 47.6% (69/145) | 75.9% (110/145) | 77.2% (112/145) |
| DATE | 60.7% (313/516) | 60.7% (313/516) | 62.8% (324/516) | 91.9% (474/516) | 95.9% (495/516) | 84.9% (438/516) | 99.0% (511/516) |
| DRIVERLICENSENUM | 29.8% (37/124) | 29.8% (37/124) | 32.3% (40/124) | 21.0% (26/124) | 27.4% (34/124) | 84.7% (105/124) | 63.7% (79/124) |
| EMAIL | 100.0% (323/323) | 100.0% (323/323) | 100.0% (323/323) | 100.0% (323/323) | 100.0% (323/323) | 96.9% (313/323) | 100.0% (323/323) |
| IDCARDNUM | 41.5% (59/142) | 41.5% (59/142) | 33.8% (48/142) | 48.6% (69/142) | 67.6% (96/142) | 91.5% (130/142) | 87.3% (124/142) |
| PASSPORTNUM | 52.8% (47/89) | 52.8% (47/89) | 57.3% (51/89) | 20.2% (18/89) | 64.0% (57/89) | 88.8% (79/89) | 85.4% (76/89) |
| PERSON | 52.5% (508/967) | 52.5% (508/967) | 65.9% (637/967) | 96.7% (935/967) | 96.7% (935/967) | 75.3% (728/967) | 93.5% (904/967) |
| PHONE | 39.2% (98/250) | 39.2% (98/250) | 39.2% (98/250) | 94.4% (236/250) | 94.8% (237/250) | 90.0% (225/250) | 94.8% (237/250) |
| SOCIALNUM | 83.2% (89/107) | 99.1% (106/107) | 99.1% (106/107) | 63.6% (68/107) | 100.0% (107/107) | 99.1% (106/107) | 95.3% (102/107) |
| STREET | 11.3% (25/222) | 11.3% (25/222) | 19.8% (44/222) | 95.0% (211/222) | 95.0% (211/222) | 52.3% (116/222) | 78.4% (174/222) |
| TAXNUM | 44.4% (56/126) | 83.3% (105/126) | 84.1% (106/126) | 53.2% (67/126) | 88.1% (111/126) | 92.9% (117/126) | 78.6% (99/126) |
| ZIPCODE | 38.2% (73/191) | 38.2% (73/191) | 25.7% (49/191) | 82.7% (158/191) | 88.0% (168/191) | 66.5% (127/191) | 62.3% (119/191) |

## Runtime (detection only, models already loaded)

| dataset | method | device | documents | characters | extract s (shared) | detect s | load s |
|---|---|---|---|---|---|---|---|
| fake | basic | cpu | 140 | 76592 | 14.0 | 2.1 | 0.0 |
| fake | rules | cpu | 140 | 76592 | 14.0 | 2.3 | 0.0 |
| fake | rules-lg | cpu | 140 | 76592 | 14.0 | 2.2 | 0.0 |
| fake | gliner | mps | 140 | 76592 | 14.0 | 17.3 | 5.3 |
| fake | combined | mps | 140 | 76592 | 14.0 | 19.5 | 0.1 |
| fake | privacy-filter | cpu | 140 | 76592 | 14.0 | 28.4 | 7.0 |
| fake | gliner2 | cpu | 140 | 76592 | 14.0 | 14.8 | 6.9 |
| tab | basic | cpu | 127 | 647638 | 0.0 | 12.4 | 0.0 |
| tab | rules | cpu | 127 | 647638 | 0.0 | 12.7 | 0.0 |
| tab | rules-lg | cpu | 127 | 647638 | 0.0 | 14.4 | 0.0 |
| tab | gliner | mps | 127 | 647638 | 0.0 | 160.7 | 4.2 |
| tab | combined | mps | 127 | 647638 | 0.0 | 170.7 | 0.1 |
| tab | privacy-filter | cpu | 127 | 647638 | 0.0 | 129.4 | 0.5 |
| tab | gliner2 | cpu | 127 | 647638 | 0.0 | 120.1 | 0.2 |
| turku | basic | cpu | 18 | 33491 | 0.0 | 0.7 | 0.1 |
| turku | rules | cpu | 18 | 33491 | 0.0 | 0.8 | 0.0 |
| turku | rules-lg | cpu | 18 | 33491 | 0.0 | 1.6 | 0.0 |
| turku | gliner | mps | 18 | 33491 | 0.0 | 9.8 | 1.1 |
| turku | combined | mps | 18 | 33491 | 0.0 | 8.5 | 0.0 |
| turku | privacy-filter | cpu | 18 | 33491 | 0.0 | 10.3 | 0.2 |
| turku | gliner2 | cpu | 18 | 33491 | 0.0 | 8.7 | 0.1 |
| ai4privacy | basic | cpu | 600 | 205188 | 0.6 | 5.4 | 0.0 |
| ai4privacy | rules | cpu | 600 | 205188 | 0.6 | 5.0 | 0.0 |
| ai4privacy | rules-lg | cpu | 600 | 205188 | 0.6 | 6.8 | 0.0 |
| ai4privacy | gliner | mps | 600 | 205188 | 0.6 | 45.9 | 0.2 |
| ai4privacy | combined | mps | 600 | 205188 | 0.6 | 48.9 | 0.1 |
| ai4privacy | privacy-filter | cpu | 600 | 205188 | 0.6 | 94.2 | 0.9 |
| ai4privacy | gliner2 | cpu | 600 | 205188 | 0.6 | 52.3 | 0.2 |

## Caveats

- The fake corpus is template text with generated names. It is an upper bound; real documents score lower.
- PLATE, INVOICE and PERSONAL_ID are scored against recognizers written for the generator's own formats, so they score well by construction.
- TAB, Turku and ai4privacy label different things (court-case identifiers, Finnish named entities, synthetic PII classes). Their numbers are not comparable across datasets.
- Types without a Presidio counterpart (TAB CODE, DEM, QUANTITY, MISC; ai4privacy ID numbers, ZIPCODE, BUILDINGNUM, AGE) accept a detection of any type, which flatters them.
- Presidio LOCATION is mostly cities and countries, so ADDRESS, CITY and STREET recall measures partial luck as much as design.
- Subsets: TAB 127 of the 127 test documents (a sample takes every third), Turku test files up to a sentence budget, ai4privacy 300 random rows per language (seed 42).
- Unlabelled real-uk is excluded from this rerun; no current recall or precision is claimed for it.
- This rerun includes synthetic Office extraction; it does not establish coverage for unsupported embedded document features.

## Reproduce

Use the archived package versions and cached external datasets:

```bash
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false python -m eval.run_matrix \
  --out outputs/audit-matrix --fake-dir outputs/audit-matrix-corpus \
  --datasets fake tab turku ai4privacy \
  --methods basic rules rules-lg gliner combined privacy-filter gliner2 \
  --tab-docs 0
```

## Related

- [residual-misses.md](residual-misses.md): why the remaining misses happen
- [local-llm-comparison.md](local-llm-comparison.md): adding a local LLM final pass
- [extraction-validation.md](extraction-validation.md): what reaches the detector
- [archive/dataset-runs.md](archive/dataset-runs.md): superseded earlier tables
