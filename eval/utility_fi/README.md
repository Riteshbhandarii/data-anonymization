# Finnish utility draft

NEEDS HUMAN REVIEW. Review the Finnish wording, factual answers and accepted
answer forms before treating this as an accepted Finnish utility benchmark.
The three memos and all identities are fictional. The tasks mirror the English
study: total hours, larger project and whether the contacts are the same.

| Memo | Total hours | Larger project | Same contact |
|---|---:|---|---|
| a1.md | 30 | Kuusi | kyllä |
| a2.md | 30 | Kuusi | ei |
| b1.md | 30 | Kuusi | kyllä |

The model receives each question and document, never suite.json or this file.

## Review, 2026-10-19

Checked against the memos and the recorded
[combined answers](../baselines/final-evidence-utility-fi-combined.json).

- Wording is natural Finnish; questions are unambiguous. All nine accepted
  answers are correct (18 + 12 = 30; Kuusi larger; contacts same, different,
  same).
- Answer format is not a scoring problem: every recorded answer is a bare
  value (`30`, `Kuusi`, `kyllä`/`ei`), so exact matching lost nothing.
- **Design flaw: guessing scores.** Kuusi is always the larger project and is
  always listed first, and the total is always 30. With both hour values
  replaced by `DATE_TIME`, pseudonymized `larger_project` was still correct
  3/3 and redacted answered Mänty 3/3. Pseudonymized 6/9 is therefore 3/9
  evidence-supported (`same_contact`) plus 3/9 guesses.
- **Name collision.** `Kuusi` also means "six" and overlaps a participating
  company's name. It did not affect these runs, but a replacement suite
  should use project names without those readings.

Fit for reporting the current run with the limitation above. Not fit as a
validated Finnish utility benchmark until allocation, order and totals vary
between memos.
