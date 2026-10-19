# Evaluation protocol

[Docs index](README.md) › Methods

This is the protocol the study follows for detection quality, residual re-identification risk and quality impact. Keep the three questions separate and do not collapse them into one score. Measured results are linked under Related.

## 1. Detection quality

Precision and recall of the detector against a labelled corpus, per entity type and per document format.

Recall is the number that matters. A missed identifier is a leak. A false positive only costs readability.

Report per entity type, since aggregate recall hides the fact that a detector can be excellent on email addresses and poor on person names in Finnish.

Baseline to beat: Presidio with default recognizers.

## 2. Residual re-identification risk

The adversarial test. Feed the sanitized output to a public model and ask it to identify the subject.

### Prompts

- **Naming.** Which company does this document come from? Which person is it about?
- **Attribute inference.** What industry, what size of organisation, what role does the author hold?
- **Linkage.** Here are two sanitized documents. Do they concern the same organisation or person?

### Rules that make this a measurement

**Give the tester web search.** Real re-identification works by linking to outside data. An offline test passes documents that fail in reality.

> **As executed, 2026-10-19:** the ChatGPT Free study did not explicitly enable web search, and the search-enabled rows were not run. The team judged that company-internal documents are not searchable online. The deviation is reported as a limitation in [public-ai-results.md](public-ai-results.md).

**Test linkage, not only naming.** A model that can tell two documents concern the same entity has leaked, even when it cannot name that entity. Inconsistent or overly consistent pseudonyms leak exactly this way.

**Score across a corpus, not per document.** Record correct, wrong, and refused. Report rates. A model will confidently invent a company name, so a wrong guess is not a failure and one lucky hit is not either.

**Include controls.** Run the same prompts on the unsanitized document, to establish the ceiling, and on an unrelated document, to establish the guess rate. Without both, the middle number means nothing.

### Recording

One row per document per prompt: document id, format, sanitization config, prompt type, model, web search on or off, model answer, ground truth, score.

## 3. Quality impact

The tradeoff nobody measures. Run the same downstream task on raw, redacted, and pseudonymized versions of the same document and compare output quality.

This answers what compliance costs in accuracy, which is the question a project owner actually wants answered.

## Related

- [Model evaluation helpers](model-evaluation.md)
- [Public AI results](public-ai-results.md) (RQ3)
- [Utility impact](utility-impact.md) (RQ4)
- [Dataset audit runs](dataset-audit-runs.md) (RQ2)
