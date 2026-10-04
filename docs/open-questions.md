# Open questions

Decisions not yet made. Nothing here should be silently resolved in code.

## Scope

- [ ] Is the deliverable a working tool or a research report? If both, which is the deliverable and which is the bonus?
- [ ] How many formats must be covered? Word, Excel, PowerPoint and scanned PDF are four different problems.
- [ ] Do the partner organisations share a format profile, or does each need its own set?

## Output format, the biggest one

The current pipeline outputs Markdown. See [the output contract](pipeline.md#output-contract) for paths, encoding, and the returned result.

- [ ] The corpus generates Finnish identity codes with invalid checksums on purpose. Should a real deployment validate the checksum or match the shape only? Validating avoids false positives on look-alike numbers but misses typos and malformed codes that still identify someone; matching the shape catches both and over-flags.

Benchmark status: `eval/bench.py --custom` uses a shape-only pattern with no checksum validation (`detect/pattern_recognizers.py`), because the corpus codes are invalid by design. That is a benchmark choice, not an answer to the question above. Also, the earlier note here that Presidio's recognizer rejects every code was wrong: Presidio 2.2.364 does not load its Finnish identity code recognizer by default for `en` or `fi`, so the default run had no recognizer at all. Whether it would accept these codes if enabled has not been measured.

## Legal

- [ ] With no provider agreement, is there any lawful basis for sending personal data at all, or is the answer simply that it is not sent?
- [ ] Who decides that a document is clean enough to send?
- [ ] Who carries responsibility when the tool misses something?
- [ ] Is a DPIA in scope, and who owns it?

## Data

- [ ] Real data or synthetic only? Current plan assumes public and synthetic until told otherwise.
- [ ] What language: Finnish, Swedish, English, or mixed? Finnish NER quality is materially worse than English and that gap is worth measuring.
- [ ] Is any of it special category data, such as health or union membership?

## Build

- [ ] Build on Presidio, or evaluate a commercial tool? Is there budget?
- [ ] Is dedicated compute available, or is the GPU shared? A local LLM detector needs it continuously, not only for demos.
- [ ] Does this build on existing internal work in the same space, or duplicate it?

## Product

- [ ] Is the goal a tool so people stop pasting into public models on their own, or an outright block? Those need very different things.
- [ ] For CAD and 3D: is the whole model file ever sent, or only the metadata and drawings extracted from it? A language model cannot read a STEP file, so the real exposure is the extraction.
