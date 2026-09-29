# corpus

Public and synthetic test data only. Never place real data here.

## Generate and verify fixtures

Run these commands from the repository root:

```bash
python -m pip install -r requirements-validation.txt
python corpus/generate.py --out outputs/corpus --n 5 --seed 42
python corpus/verify.py outputs/corpus
```

The generator creates English and Finnish documents using Faker. `--n` is the
number of documents per language and ordinary format. PNG has two quality
variants per record, so `--n 5` creates 70 documents in total:

| Format | Documents for `--n 5` | Label locations |
| --- | ---: | --- |
| DOCX | 10 | Body, metadata, header, footer, comment, tracked change |
| PPTX | 10 | Body, metadata, speaker notes, embedded image |
| XLSX | 10 | Visible cells, metadata, hidden worksheet |
| PDF | 10 | Text body, metadata, embedded image on the same page |
| CSV | 10 | Body |
| PNG | 20 | Body, with `clean` and `low_resolution` variants |

The DOCX header contains a company, the footer a contact person, and a real
review comment contains a reviewer name and an email address. A tracked
insertion contains another person's name. These identifiers are different from
the body values. PPTX and PDF embed a rendered contact image with an email that
does not occur in the text body. The PDF is a mixed page: it contains selectable
text and the raster image together.

PNG fixtures render the title and the same fake body paragraphs directly into
pixels. The canvas grows to the measured width of the longest line, so neither
titles nor body lines wrap or clip their identifiers.
The ReportLab package supplies the Vera font, including Finnish characters;
generation does not download fonts or photographs. `low_resolution` resizes the
clean image to half its width and height with Lanczos resampling. Both variants
share the same expected labels and saved body text. Other formats use quality
`standard`.

## Corpus files and labels

```text
corpus.json              Seed, size, Faker version and corpus fingerprint
index.csv                The authoritative list of documents for this run
labels/<stem>.json       Identifiers, their types and source locations
text/<stem>.txt          Body text saved before extraction
evidence/<stem>.json     Rendering recipes for documents containing images
docx/, pptx/, xlsx/,
pdf/, csv/, png/         Generated source documents
```

A label file has this structure:

```json
{
  "file": "docx/en_docx_00.docx",
  "language": "en",
  "format": "docx",
  "quality": "standard",
  "entities": [
    {"type": "COMPANY", "value": "Example Company", "location": "header"}
  ]
}
```

The supported location values are `body`, `metadata`, `notes`, `hidden_sheet`,
`header`, `footer`, `comment`, `tracked_change`, and `embedded_image`. A label
describes an identifier at a location, not each repeated occurrence of that
identifier. `PERSON2` and `DATE2` remain types `PERSON` and `DATE`; location-specific
record fields similarly retain their normal identifier type.

`index.csv` includes `file`, `language`, `format`, `entities`, `hidden`, and
`quality`. The historical `hidden` column counts all labels outside `body`,
including visible headers, footers and image text. `text/` contains only body
text, so detector benchmarks can continue to run without an extraction stage.
Embedded-image text and other document locations are not appended to it.

`corpus_sha256` fingerprints label JSON and saved text in manifest order, using
the existing fingerprint convention. It does not hash the Office/PDF container
bytes. Reuse the seed, generator version and pinned Faker version when comparing
runs, and keep the fingerprint with results. Files from an earlier larger run
may remain in an output directory; the verifier checks only `index.csv`, rather
than treating these stale files as part of the new corpus.

## What verification means

`verify.py` reads Office XML parts, workbook values and PDF text independently
of the pipeline's extractors. Word review comments must have an actual comment
relationship and reference, and header/footer text must be linked from the
document. The verifier checks each identifier in the location named by its
label. A match in the body cannot compensate for a missing header or comment.

For image text, verification checks the generator's rendering evidence instead
of depending on OCR. Each sidecar records a SHA-256 of the saved source document,
a rendering version, title, paragraphs, quality, and an RGB pixel digest. The
verifier reads the actual image from the PNG, PPTX, or PDF, re-renders the recipe,
and compares the pixels. Editing the evidence text alone, replacing the image,
or modifying the source document causes verification to fail.

This establishes that the expected text was rendered into the fixture. It does
**not** establish that OCR recovered it. The pipeline must read the original
document; rendering evidence and `text/` are never extractor output. Measure
OCR and extraction separately:

```bash
python -m pipeline.validation outputs/corpus --report-dir outputs/extraction-report
```

Verification exits with a nonzero status for missing documents or label files,
invalid labels, manifest/count/fingerprint mismatches, missing labelled values,
or inconsistent rendering evidence. It reports the affected file and location.

## Regression checks

```bash
python -m unittest discover -s tests -p test_corpus_locations.py -v
```

These checks cover all generated locations, both image qualities, reproducible
labels and saved text, stale files, missing labels, removed Word content, altered
images and evidence, and unclipped long/Finnish text. They validate fixture
construction without treating successful generation as successful OCR.
