# Work plan and pathway ownership

Current plan for #32, updated 2026-10-14 from repository issues, submitted PRs
and the established pipeline split. Build work and the owner's survey pathways
both have deliverables below. **Group agreement and a named #27 issue owner
are still pending; publishing this plan does not invent either.**

The owner authorized integration on 2026-10-14. All ten intended PRs are
merged into `main`; duplicate #49 is closed. #30's confirmed screenshot/snips
meaning and tool survey are complete. Remaining human work is #44's public-AI
experiment, #45's real-document hand labels, and group acceptance/ownership
under #32, followed by the paper/cookbook.

| Pathway / work | Confirmed owner or contributor | Reviewable deliverable / evidence | Remaining finish condition |
|---|---|---|---|
| Commercial products, free and paid (#27) | Commercial research contributors: @SiriwitW (#46), @anuntachin (#51); #27 has no assignee | [Nine-option inventory](product-options.md), free-tool research #51 and commercial research #46 | Review the inventory; group confirms one accountable #27 owner |
| Own algorithms/toolkit | @Riteshbhandarii: detection/evaluation; @wycffff: extraction/redaction | Existing pipeline and techniques; combined method and precision #53; hidden-content and evaluation audit #58 | Review pending changes; maintain per-language/per-type metrics and reader limits |
| Local models (#29, #43) | @Riteshbhandarii | Model methods #54; overview/LM Studio experiments and corrected smoke #56; seven-method corrected labelled matrix #58 | Review #54/#56/#58; keep current matrix and archived local-LLM trials separate |
| Data clipping (#30) | @Riteshbhandarii | Meaning confirmed as screenshots/snips; image redaction and tool survey #52 | Review screenshot work; public-model logo/letterhead test remains in #44 |
| Is OCR needed (#31, closed) | @wycffff, extraction/redaction lane | Existing OCR routing, validation and OCR survey | Keep image-only extraction regressions and English/Finnish OCR evidence passing |
| Number and kind of options (owner's point 6) | Each pathway owner; #27 ownership pending | Counts/categories in product inventory; methods and clipping surveys | Keep scope, local/cloud boundary and unsupported formats visible in each overview |
| Work plan update (#32) | @Riteshbhandarii, project coordination | This plan and linked deliverables | Group accepts the plan and confirms remaining ownership |
| UI (#48) | @wycffff | Findings-first interface, GLiNER selection and UI regressions #50 | Owner review; PR remains open |
| Precision and full TAB (#11, #42, #45) | @Riteshbhandarii | Combined/precision #53; corrected seven-method full TAB/DIRECT/QUASI matrix #58 | Review #53/#58; hand-label about 20 real documents for the remaining part of #45 |
| Downstream usefulness (#19) | @Riteshbhandarii + @wycffff | Paired manual workflow and actual local utility results #55 | Review measurement; repeat on the chosen public model as part of #44 |
| Public-AI experiment (#44) | @Riteshbhandarii | Existing manual pack, controls and prompts; utility workflow #55 | A person reviews real-public anonymized documents, runs free public-model prompts with/without search and records actual answers |

The pipeline split is documented in
[#32's discussion](https://github.com/Riteshbhandarii/data-anonymization/issues/32).
Research contributor names above come from PR authors; they are not new
assignments made on their behalf.

## Execution order after integration

1. Use the merged pipeline, UI, model methods and utility workflow on `main`.
   The [audit](pre-review-audit.md) records fixed defects and reader limits;
   the [current matrix](dataset-audit-runs.md) records the measured tradeoffs.
   Registry/window conflicts retained #54's builders and pattern helper,
   with all UI labels and regression tests. #49's duplicate work was excluded.
2. Complete the manual public-AI run (#44) and the real-document annotation
   study (#45). CI checks software and synthetic extraction; it cannot supply
   these results or certify anonymized documents safe to upload.
3. Write the final comparison/cookbook/paper from the measured results and
   explicit limitations. Confirm the plan and outstanding ownership in the
   group before closing #32.

Cloud products remain research comparators. Routine new detector experiments
use free local models. Published aggregate results must keep corpus scope,
language, detector configuration, denominator and measurement type attached.

## Pre-review evidence and limits

The deeper audit fixed image alpha exposure, omitted Office/PDF/TIFF content,
stale UI results, detector window boundaries, negative-document precision and
manual-study accounting. #58 records the findings and unsupported reader
features. The combined local checkout passes 222 regression tests, 43 scoring
tests, full Ruff and unchanged acceptance gates on the 70-document extraction
corpus. The ten intended PRs and updated conflict-resolution heads passed
corpus/scoring/pipeline CI before merging. #49 is closed as superseded.

The corrected labelled matrix in #58 reruns all seven methods on the same
885 documents: 140 fake, full TAB 127, Turku 18 and ai4privacy 300 per language.
All 28 method/dataset runs complete, with exact counts/hashes archived.
Combined recall is 96.4% fake, 83.5% TAB, 80.0% Turku and 88.5%/83.8%
ai4privacy English/Finnish. Its lower-bound precision is 63.7% TAB and 26.5%
Turku; retain that tradeoff. Old tables remain historical, including the
unlabelled real-uk timings/counts and local-LLM trials outside this rerun.

#56 separately records a fresh offline CPU combined smoke: 136/146 body
labels (93.2%), zero failed documents and typed precision 197/238 (82.8%)
on fourteen synthetic documents. Its precision metric differs from the
matrix's any-annotation lower bound. Public-AI answers, real-document labels,
OCR misses, unsupported embedded content and unmeasured contextual
re-identification remain explicit limits.
