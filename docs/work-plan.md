# Work plan and pathway ownership

Current plan for #32, updated 2026-10-13 from repository issues, submitted PRs
and the established pipeline split. Build work and the owner's survey pathways
both have deliverables below. **Group agreement and a named #27 issue owner
are still pending; publishing this plan does not invent either.**

| Pathway / work | Confirmed owner or contributor | Reviewable deliverable / evidence | Remaining finish condition |
|---|---|---|---|
| Commercial products, free and paid (#27) | Commercial research contributors: @SiriwitW (#46), @anuntachin (#51); #27 has no assignee | [Nine-option inventory](product-options.md), free-tool research #51 and commercial research #46 | Review the inventory; group confirms one accountable #27 owner |
| Own algorithms/toolkit | @Riteshbhandarii: detection/evaluation; @wycffff: extraction/redaction | Existing pipeline and techniques; combined method and precision #53 | Review pending changes; maintain per-language/per-type metrics |
| Local models (#29, #43) | @Riteshbhandarii | Model matrix #54, local-model overview and LM Studio experiments tracked by #29 | Review local-model PR and preserve measured/unmeasured distinctions |
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

1. Review #50 (UI), then #52 (screenshots), then #53 (combined/precision), then
   #54 (new detectors). #53/#54 and #50 edit the same detector registry. A local
   trial integration retains #54's builder registry, which also includes the
   combined method, while keeping #50's tests and labels. Resolve that file
   during owner-approved integration and rerun checks.
2. Review #46 and #51 independently. #49 is superseded by the clean free-tool
   branch #51; keep the duplicate out of the integration rather than including
   both versions of its research.
3. Review #55 and the local-model overview/adapter PR for #29. The local-model
   PR is stacked on #54 and should follow it. All approval and merge decisions
   remain with the owner; automatic merge is disabled.
4. Complete the manual public-AI run (#44) and the real-document annotation
   study (#45). CI checks software and synthetic extraction; it cannot supply
   these results or certify anonymized documents safe to upload.
5. Write the final comparison/cookbook/paper from the measured results and
   explicit limitations. Confirm the plan and outstanding ownership in the
   group before closing #32.

Cloud products remain research comparators. Routine new detector experiments
use free local models. Published aggregate results must keep corpus scope,
language, detector configuration, denominator and measurement type attached.
