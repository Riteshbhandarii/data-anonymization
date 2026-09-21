# redact

Replace sensitive information in Markdown before the pipeline saves the result.

The pipeline integration contract is a function that accepts one Markdown string and returns one Markdown string:

```python
def anonymize_markdown(markdown: str) -> str:
    ...
```

Pass the function to `pipeline.run_pipeline` through its `anonymizer` argument. See `docs/pipeline.md` for a complete example.
