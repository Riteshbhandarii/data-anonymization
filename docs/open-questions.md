# Open questions

Decisions not yet made. Nothing here should be silently resolved in code.

## Scope

- [ ] Is the deliverable a working tool or a research report? If both, which is the deliverable and which is the bonus?
- [ ] How many formats must be covered? Word, Excel, PowerPoint and scanned PDF are four different problems.
- [ ] Do the partner organisations share a format profile, or does each need its own set?

## Output format, the biggest one

- [ ] Must the output be the same format as the input, so people can keep working with the document, or is clean text enough because it is only ever fed to a model?

Rebuilding a redacted `.docx` that still looks like a real document is roughly ten times the work of extracting to text. This decision shapes the whole `redact` stage and should be settled before any of it is written.

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
