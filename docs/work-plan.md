# Work plan and pathway ownership

Current plan for #32, updated 2026-10-14 from repository issues, submitted PRs
and the established pipeline split. Build work and the owner's survey pathways
both have deliverables below. **Group agreement and a named #27 issue owner
are still pending; publishing this plan does not invent either.**

| Pathway / work | Confirmed owner or contributor | Reviewable deliverable / evidence | Remaining finish condition |
|---|---|---|---|
| Commercial products, free and paid (#27) | Commercial research contributors: @SiriwitW (#46), @anuntachin (#51); #27 has no assignee | [Nine-option inventory](product-options.md), free-tool research #51 and commercial research #46 | Review the inventory; group confirms one accountable #27 owner |
| Own algorithms/toolkit | @Riteshbhandarii: detection/evaluation; @wycffff: extraction/redaction | Existing pipeline and techniques; combined method and precision #53; hidden-content and evaluation audit #58 | Review pending changes; maintain per-language/per-type metrics and reader limits |
| Local models (#29, #43) | @Riteshbhandarii | Model matrix #54; local-model overview, LM Studio experiments and corrected-code smoke #56 | Review #54/#56; rerun the historical full matrix before treating its figures as current |
| Data clipping (#30) | @Riteshbhandarii | Meaning confirmed as screenshots/snips; image redaction and tool survey #52 | Review screenshot work; public-model logo/letterhead test remains in #44 |
| Is OCR needed (#31, closed) | @wycffff, extraction/redaction lane | Existing OCR routing, validation and OCR survey | Keep image-only extraction regressions and English/Finnish OCR evidence passing |
| Number and kind of options (owner's point 6) | Each pathway owner; #27 ownership pending | Counts/categories in product inventory; methods and clipping surveys | Keep scope, local/cloud boundary and unsupported formats visible in each overview |
| Work plan update (#32) | @Riteshbhandarii, project coordination | This plan and linked deliverables | Group accepts the plan and confirms remaining ownership |
| UI (#48) | @wycffff | Findings-first interface, GLiNER selection and UI regressions #50 | Owner review; PR remains open |
| Precision and full TAB (#11, #42, #45) | @Riteshbhandarii | Combined detector and precision #53; TAB full split and DIRECT/QUASI results | Review #53; hand-label about 20 real documents for the remaining part of #45 |
| Downstream usefulness (#19) | @Riteshbhandarii + @wycffff | Paired manual workflow and actual local utility results #55 | Review measurement; repeat on the chosen public model as part of #44 |
| Public-AI experiment (#44) | @Riteshbhandarii | Existing manual pack, controls and prompts; utility workflow #55 | A person reviews real-public anonymized documents, runs free public-model prompts with/without search and records actual answers |

The pipeline split is documented in
[#32's discussion](https://github.com/Riteshbhandarii/data-anonymization/issues/32).
Research contributor names above come from PR authors; they are not new
assignments made on their behalf.

## Review and execution order

1. Review #50 (UI), then [#58 (core audit)](https://github.com/Riteshbhandarii/data-anonymization/pull/58),
   then #52 (screenshots), #53 (combined/precision), #54 (new detectors) and
   #56 (local models). #58 is stacked on #50; #56 is stacked on #54.
   #53/#54 and #50 edit the same detector registry, and #53/#54 both change
   GLiNER windowing. The tested local integration retains #54's builder
   registry and pattern helper while keeping all UI labels and regressions.
   Apply those resolutions during owner-approved integration and rerun checks.
2. Review #46 and #51 independently. #49 is superseded by the clean free-tool
   branch #51; keep the duplicate out of the integration rather than including
   both versions of its research.
3. Review #55 and this product/work-plan PR independently. All approval and
   merge decisions remain with the owner; automatic merge is disabled.
4. Complete the manual public-AI run (#44) and the real-document annotation
   study (#45). CI checks software and synthetic extraction; it cannot supply
   these results or certify anonymized documents safe to upload.
5. Write the final comparison/cookbook/paper from the measured results and
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
corpus. All eleven open PR heads pass corpus/scoring/pipeline CI; no PR was
merged. #49 remains open only as a superseded duplicate.

Corrected windowing and span counting can change accuracy and runtime. The
old full-matrix and local-LLM tables remain historical; #56 separately records
a fresh offline CPU combined smoke run: 136/146 body labels (93.2%), zero
failed documents and typed precision 197/238 (82.8%) on fourteen synthetic
documents. That small result does not complete the matrix, public-AI study
or real-document annotation. OCR misses, unsupported embedded content and
unmeasured contextual re-identification remain explicit limits.
