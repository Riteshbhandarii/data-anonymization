# redact

Replace sensitive information in Markdown before the pipeline saves the result.

The pipeline integration contract is a function that accepts one Markdown string and returns one Markdown string:

```python
def anonymize_markdown(markdown: str) -> str:
    ...
```

Pass the function to `pipeline.run_pipeline` through its required `anonymizer` argument. The pipeline calls the anonymization module with the complete normalized Markdown. Return the complete processed Markdown string; the pipeline receives it, saves the file, and returns its path and text to the caller.

See [the pipeline integration guide](../docs/pipeline.md#connect-an-anonymization-module) for import examples and wrappers for modules with different input/output formats.
