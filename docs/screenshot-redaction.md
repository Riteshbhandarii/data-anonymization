# Screenshot redaction

Issue #30. Staff take a screenshot or snip of part of a document and paste the
image into a public chat model. The image has no file metadata to clean, but
every visible name, number and address is still there as pixels, together with
logos, letterheads, signatures and stamps. The job is to clean the image before
it is pasted.

This page covers the available tools, a measurement of automatic redaction on
the synthetic PNGs, and what no text-based tool can catch.

## Tools

Checked against each tool's own page on 2026-10-13 unless a cell says
otherwise. "Unverified" means no primary source was found or the page could not
be opened.

| Tool | Cost and licence | Runs | Finnish | Finds identifiers | Hides with |
|---|---|---|---|---|---|
| [Presidio Image Redactor](https://github.com/microsoft/presidio/tree/main/presidio-image-redactor) 0.0.60 | Free, MIT ([PyPI](https://pypi.org/project/presidio-image-redactor/)) | Local with Tesseract. An optional `DocumentIntelligenceOCR` class sends the image to Azure instead | Tesseract `fin` for OCR. Detection is whatever Presidio analyzer it is given; the default is English spaCy | Automatic: OCR, Presidio analyzer, boxes per word | Solid fill |
| `redact/image.py` in this repository | Free, MIT | Local | Tesseract `eng+fin`, and any method in `detect/` | Automatic | Solid fill |
| Windows 11 Snipping Tool, Text Actions | Free, bundled with Windows | Unverified whether text recognition runs on the device | Unverified | "Quick Redact" hides email addresses and phone numbers automatically; any other text is selected by hand ([Windows Insider blog, 2023-09-14](https://blogs.windows.com/windows-insider/2023/09/14/new-updates-for-snipping-tool-and-phone-link-begin-rolling-out-to-windows-insiders/)) | Unverified |
| macOS screenshot and Markup | Free, bundled | Local | Not applicable | Manual: draw a shape. Preview's Redact tool works on PDFs according to third-party guides; Apple's own page was not found (unverified) | Filled shape if the user picks one |
| [ShareX](https://github.com/ShareX/ShareX) | Free, GPL-3.0, Windows | Local | Not applicable | Manual. [OCR](https://getsharex.com/) is a separate task, not tied to redaction | Blur, pixelate, highlight or rectangle |
| [Greenshot](https://github.com/greenshot/greenshot) | Free, GPL-3.0, Windows | Local | Not applicable | Manual "obfuscate". The repository documents an [OCR-based text obfuscation](https://github.com/greenshot/greenshot/blob/main/TEXT_OBFUSCATION_FEATURE.md) feature using Windows OCR; release status unverified | Obfuscation; the OCR feature pixelates only |
| [Flameshot](https://github.com/flameshot-org/flameshot) | Free, GPLv3+, Linux, Windows, macOS | Local | Not applicable | Manual | Pixelate or rectangle |
| Adobe Acrobat Pro | Paid. Redaction needs Pro according to third-party guides | Local desktop | Unverified | Find Text & Redact with patterns (phone, card, email, dates) on PDF text. An image must be made into a PDF and run through Recognize Text first. Unverified: [Adobe's help page](https://helpx.adobe.com/acrobat/current/removing-sensitive-content-pdfs.html) refused the request; taken from search summaries | Removes content on apply |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) redaction | Free under AGPL-3.0, or a commercial Artifex licence | Local library | Depends on the OCR used | Programmatic: the caller supplies the areas | Removes the content under the area when applied |
| [Google Cloud Sensitive Data Protection](https://docs.cloud.google.com/sensitive-data-protection/docs/concepts-image-redaction) | Paid API | Cloud | Unverified for image OCR | Automatic: OCR and infoTypes | Opaque rectangle |
| Azure AI Language PII | Paid API | Cloud | Finnish listed for text and document PII ([language support](https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/language-support)) | Automatic on text; an image needs OCR first, for example Azure Document Intelligence | Returns text spans, does not draw on images |
| Amazon Comprehend PII with Textract | Paid API | Cloud | No: Comprehend PII is [English and Spanish only](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html), and Textract does not list Finnish ([OCR survey](ocr-survey.md)) | Automatic on text | Returns spans or masked text |
| [Private AI](https://private-ai.com/) | Commercial | Container in the customer's environment | Unverified for images; the text product claims 52 languages | Automatic, text and faces, according to the vendor | Blur, according to the vendor page (unverified) |

Cloud services are listed for completeness only. Sending an image to one is
the same disclosure this work is meant to prevent, and none was run.

Two things matter more than the choice of tool:

- **Pixelation and blur are not redaction.** [Depix](https://github.com/spipm/Depix),
  a proof of concept, recovers text from pixelated screenshots. Only a solid
  fill removes the pixels. ShareX, Greenshot and Flameshot all offer pixelation
  or blur.
- **The saved file must not keep the original.** The "aCropalypse" bugs let
  anyone recover cropped or covered parts of screenshots saved by Pixel's Markup
  (CVE-2023-21036) and by the Windows Snipping Tool and Snip & Sketch, fixed
  under CVE-2023-28303 ([The Record](https://therecord.media/microsoft-patch-acropalypse-bug-vulnerability)).
  `redact/image.py` writes a new PNG from the redacted pixels, so nothing of
  the source file is carried over.

## Method

`redact/image.py` reads the image with Tesseract (`image_to_data`, `eng+fin`),
joins the words into text with spaces inside a line and line breaks between
lines, and passes that text to any detector in `detect/`. Every word a detected
span overlaps, even by one character, is filled black. Each box grows by a
third of the word's height, at least 3 pixels: Tesseract's boxes sometimes cut
the first or last glyph, and with this margin no word in the corpus had ink
left or right of its box.

`eval/screenshot_bench.py` scores each method on every PNG:

1. OCR the original as an attacker would. A labelled value is readable before
   when the whole value appears in that text. This is the same Tesseract read
   as in the [OCR survey](ocr-survey.md).
2. Redact the image with the method.
3. Judge each readable value on the redacted pixels. **Leaked**: OCR still
   reads the whole value. **Partial**: not leaked, but at least one of its
   words is not covered with black. **Hidden**: every word of every occurrence
   is covered. Coverage is checked on the output image, at least 90% of each
   word box near-black, not on the boxes a tool reports, so every tool is
   judged the same way.

**Image recall** is hidden / readable before. A partly hidden address counts as
a miss, the same strict rule the text benchmarks use. **Hidden / planted** also
counts the values Tesseract could not read before redaction: a person or a
vision model may still read them, so it is the safer number. **Text recall**
runs the same detector on the generator's text for the same image, out of all
planted values, so it compares with hidden / planted. It is not comparable to
the [dataset runs](archive/dataset-runs.md), which also require the correct entity
type; for an image, any box hides the value.

**Words blacked** is the share of all OCR words filled. The synthetic snips
are dense with identifiers: 52% of the OCR words belong to a labelled value.
**Non-label words blacked** counts only words outside every labelled value and
is the over-redaction that costs readability. Words of a value that OCR misread
cannot be matched to its label, so blacking them out also counts here.

`presidio-image` and `presidio-image-rules` are Presidio Image Redactor given
the same analyzer and threshold as `basic` and `rules`, with `eng+fin` OCR and
the document's language, so only the OCR handling and box drawing differ.

## Results

40 PNGs from `corpus/generate.py --n 10 --seed 42` (corpus fingerprint
`334a5819…6acdaed`): 10 English and 10 Finnish documents, each at clean
(1600 px wide) and half resolution, 480 labelled values. Tesseract 5.5.3,
presidio-analyzer 2.2.364, presidio-image-redactor 0.0.60, GLiNER 0.2.29 (on
MPS), on an Apple Silicon Mac.

Image recall:

| Method | EN clean | EN low-res | FI clean | FI low-res | All | Hidden / planted | Text recall | Words blacked | Non-label words blacked | Seconds / image |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| basic | 78.8% | 77.3% | 75.4% | 74.1% | 76.4% | 74.4% | 75.8% | 43.7% | 6.4% | 0.44 |
| rules | 87.3% | 86.6% | 88.6% | 87.1% | 87.4% | 85.0% | 87.1% | 47.0% | 6.4% | 0.49 |
| rules-lg | 86.4% | 86.6% | 90.4% | 88.8% | 88.0% | 85.6% | 87.1% | 46.1% | 8.9% | 0.47 |
| gliner | 90.7% | 90.8% | 90.4% | 89.7% | **90.4%** | 87.9% | 90.0% | 49.8% | **1.5%** | 0.99 |
| presidio-image | 79.7% | 77.3% | 75.4% | 75.0% | 76.9% | 74.8% | 75.8% | 45.3% | 9.3% | 0.49 |
| presidio-image-rules | 87.3% | 86.6% | 87.7% | 87.1% | 87.2% | 84.8% | 87.1% | 48.4% | 9.3% | 0.48 |

Readable before redaction: 467 of 480 values (EN 118 + 119 of 120, FI 114 + 116
of 120). Seconds include OCR and detection; the GLiNER figure includes loading
the model on the first image.

Words blacked / non-label words blacked:

| Method | EN clean | EN low-res | FI clean | FI low-res |
|---|---:|---:|---:|---:|
| basic | 43.3% / 8.6% | 42.9% / 8.7% | 44.2% / 2.8% | 44.9% / 2.2% |
| rules | 45.6% / 8.6% | 45.3% / 8.7% | 48.9% / 2.8% | 49.5% / 2.2% |
| rules-lg | 42.7% / 10.8% | 43.1% / 11.3% | 50.8% / 7.1% | 50.5% / 3.7% |
| gliner | 46.0% / 0.4% | 46.2% / 0.4% | 55.1% / 5.7% | 54.8% / 0.7% |
| presidio-image | 45.6% / 12.5% | 44.7% / 12.1% | 44.9% / 4.3% | 46.1% / 4.5% |
| presidio-image-rules | 47.6% / 12.5% | 47.1% / 12.1% | 49.2% / 4.3% | 50.5% / 4.5% |

GLiNER's 5.7% on clean Finnish images is not over-redaction: every one of those
words belongs to an identifier OCR misread (an address and a company read
without their umlauts, and an email), which GLiNER still blacked out.

Leaked and partial values, all 40 images:

| Method | Hidden | Partial | Leaked | Main misses |
|---|---:|---:|---:|---|
| basic | 357 | 52 | 58 | No recognizer for them: 23 plates, 14 invoices and 12 identity codes leak whole; 38 addresses partial |
| rules | 408 | 50 | 9 | 38 addresses partial (street or city left); 8 phones leak |
| rules-lg | 411 | 48 | 8 | As `rules` |
| gliner | 422 | 5 | 40 | 33 IBANs leak whole, and 5 phones, 2 dates |
| presidio-image | 359 | 49 | 59 | As `basic` |
| presidio-image-rules | 407 | 49 | 11 | As `rules` |

What this shows:

- **Once OCR has read a value, the image step loses nothing; detection is
  the limit.** Over the 467 values OCR read, each method hides as many in the
  image as its detector covers in the text, within one point (`rules` 87.4%
  against 86.9%, `gliner` 90.4% against 90.6%).
- **OCR misreads cost about two points.** Against all 480 planted values the
  image trails the text by 1 to 2 points (`rules` 85.0% against 87.1%): the
  text detector would have caught 9 to 12 of the 13 values Tesseract misread,
  and the image redactor never sees them.
- **Presidio misses two phone formats in this corpus**: US numbers written
  `001-…x…` and Finnish `+358` numbers without spaces. All 8 phone leaks in
  every Presidio method are these four numbers at both resolutions; GLiNER
  hides them.
- **Half resolution made no difference** at these sizes (about 16 px text).
  Real screenshots at 100% scaling have smaller text; that was not tested.
- **The families fail in opposite places, as on text.** Presidio's methods
  leave most addresses partly visible; GLiNER hides addresses but leaves IBANs
  whole. Neither reaches the full set, so combining them is the next step for
  images too.
- **Presidio Image Redactor matches our module on recall but blacks out more.**
  With the same analyzer, recall is 87.2% against 87.4%, but 9.3% of
  non-identifier words are blacked out against 6.4%. It joins every OCR word
  with one space, so the title runs into the first line: the word "Internal"
  after the English title is blacked out in all 20 English images. Its default settings are English OCR and English
  detection; the run above passes `eng+fin` and the document language.
- **The 13 values OCR misread** are 5 emails, 4 IBANs, 2 identity codes, an
  address and a company. An OCR-based redactor can only cover them by chance,
  when the detector still recognises the misread text.

Limits of this measurement: one font, black text on white, printed only, no
application window around the text. Dark mode, coloured backgrounds, tables,
small UI text and photographed screens are untested. Coverage is judged on
Tesseract's word boxes of the original, so ink outside those boxes would not be
counted; on this corpus no word had ink beyond the margin to either side.

## What no text tool covers

A snip identifies an organisation without any readable identifier. OCR and
text detection never see these:

| Element | Why it leaks | What would address it |
|---|---|---|
| Logos and letterheads | Name the company directly or through a known design | Match against the organisation's own logos and letterhead templates, an image deny list; or crop rules that cut the header before pasting |
| Signatures | Identify a person; often next to a printed name | A signature detection model, or a rule that signature blocks are never snipped |
| Stamps and seals | Carry the organisation's name in curved or rotated text that OCR misses | Detect by colour and shape and black out; untested |
| Handwriting | Tesseract reads printed text only; Azure Read lists Finnish for printed text but not handwriting ([OCR survey](ocr-survey.md)) | Manual redaction |
| Faces and photos | Biometric, identify people directly | Face detection with solid fill |
| QR codes and barcodes | Encode URLs, invoice references or IDs that are not visible as text | Decode locally (OpenCV or zbar) and black out every code |
| Window titles, browser tabs, user names, avatars | Show the system, tenant, file path or the person taking the snip | Crop to the document area before redaction |
| Layout and template | A company's form or report layout can be recognisable on its own | Not addressable by redaction; covered by the re-identification test |

Whether a public model can name the organisation from a redacted snip with the
logo left in is the manual test in #44; it has not been run on these images.

## Reproduce

```bash
export PATH="/opt/homebrew/bin:$PATH"   # Tesseract with eng and fin data
python -m pip install -r requirements-evaluation.txt gliner
python -m spacy download en_core_web_sm && python -m spacy download fi_core_news_sm
python -m spacy download en_core_web_lg && python -m spacy download fi_core_news_lg
python corpus/generate.py --out outputs/screenshot/corpus --n 10 --seed 42
python -m eval.screenshot_bench outputs/screenshot/corpus --out outputs/screenshot/report
```

`--methods` runs a subset. The report directory gets `summary.md`,
`summary.csv`, `by_method.csv`, `values.csv` (state of every labelled value),
`details.json` and the redacted PNGs under `redacted/<method>/`. Everything
stays under `outputs/`, which git ignores; only synthetic images are used.

To redact one image:

```python
from PIL import Image
from detect.methods import get_detector
from redact.image import redact_image

with Image.open("snip.png") as image:
    redacted, boxes = redact_image(image, get_detector("rules"), language="fi")
redacted.save("snip_redacted.png")
```
