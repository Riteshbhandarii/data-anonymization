#!/usr/bin/env python3
"""Generate a labelled synthetic document corpus.

Everything here is fake: Faker invents the people, companies and addresses, so
there is no personal data in the output and no licence attached to it. That is
the point. It can be committed, shared, and sent to a public model in the
re-identification test, none of which is true of real documents.

Identifiers are planted in separate document locations on purpose:

    body          ordinary text
    metadata      docProps author / last-modified-by / keywords
    notes         PowerPoint speaker notes
    hidden_sheet  a hidden worksheet
    header/footer Word running header and footer
    comment       Word review comment text and author
    tracked_change Word tracked insertion
    embedded_image text rendered inside a slide or PDF image

A pipeline that only reads visible body text scores well on the body entities
and misses the rest. The labels record where each identifier lives so that gap
shows up as a number instead of a surprise.

Each writer returns the text it made visible plus the identifiers it planted
elsewhere. Body labels are then derived by looking for record values in that
text, so adding a new identifier type means editing the record and the
templates, and nothing else.

    python3 corpus/generate.py --out ~/Desktop/anonymization-corpus --n 5
"""

import argparse
import csv
import hashlib
import json
import os
import random
from importlib.metadata import version

from faker import Faker

if __package__:
    from .image_helpers import QUALITIES, image_payload, save_evidence
else:
    from image_helpers import QUALITIES, image_payload, save_evidence

LANGS = {"en": "en_US", "fi": "fi_FI"}

TEXT = {
    "en": {
        "memo": "Internal memo prepared by {PERSON} ({EMAIL}) of {COMPANY}.",
        "contact": "Direct line {PHONE}. Postal address: {ADDRESS}.",
        "payment": "Invoice {INVOICE} settled to account {IBAN} on {DATE}.",
        "hr": "{PERSON2} joined on {DATE2}, personal identity code {PERSONAL_ID}, vehicle {PLATE}.",
        "note": "Do not circulate. Questions to {PERSON} on {PHONE}.",
        "title": "Quarterly operations review",
    },
    "fi": {
        "memo": "Sisäinen muistio, laatija {PERSON} ({EMAIL}), {COMPANY}.",
        "contact": "Suora numero {PHONE}. Postiosoite: {ADDRESS}.",
        "payment": "Lasku {INVOICE} maksettu tilille {IBAN} {DATE}.",
        "hr": "{PERSON2} aloitti {DATE2}, henkilötunnus {PERSONAL_ID}, ajoneuvo {PLATE}.",
        "note": "Ei jaettavaksi. Kysymykset {PERSON}, puhelin {PHONE}.",
        "title": "Neljännesvuosikatsaus",
    },
}


def hetu(fake):
    """Finnish-shaped personal identity code. Checksum is not valid on purpose."""
    d = fake.date_of_birth(minimum_age=20, maximum_age=60)
    return f"{d:%d%m%y}-{random.randint(100, 899)}{random.choice('0123456789ABCDEFHJKLMNPRSTUVWXY')}"


def make_record(fake):
    record = {
        "PERSON": fake.name(),
        "PERSON2": fake.name(),
        "EMAIL": fake.email(),
        "PHONE": fake.phone_number(),
        "ADDRESS": fake.address().replace("\n", ", "),
        "COMPANY": fake.company(),
        "IBAN": fake.iban(),
        "PERSONAL_ID": hetu(fake),
        "PLATE": "".join(random.choices("ABCDEFGHIJKLMNOPRSTUVXYZ", k=3)) + f"-{random.randint(100, 999)}",
        "DATE": fake.date(),
        "DATE2": fake.date(),
        "INVOICE": f"INV-{random.randint(10000, 99999)}",
    }
    # Values outside the body must be independently observable. Avoid a repeated
    # name elsewhere accidentally satisfying the missing location's label.
    for key, factory in {
        "HEADER_COMPANY": fake.company, "FOOTER_PERSON": fake.name,
        "COMMENT_PERSON": fake.name, "COMMENT_EMAIL": fake.email,
        "TRACKED_PERSON": fake.name, "IMAGE_EMAIL": fake.email,
    }.items():
        value = factory()
        while any(value in existing or existing in value for existing in record.values()):
            value = factory()
        record[key] = value
    return record


def lines(lang, r):
    t = TEXT[lang]
    return (t["title"],
            [t[k].format(**r) for k in ("memo", "contact", "payment", "hr")],
            t["note"].format(**r))


def write_docx(path, title, body, note, r):
    import docx
    from docx.opc.constants import RELATIONSHIP_TYPE
    from docx.opc.packuri import PackURI
    from docx.opc.part import Part
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from lxml import etree

    d = docx.Document()
    d.add_heading(title, 1)
    for line in body:
        d.add_paragraph(line)
    p = d.core_properties
    p.author, p.last_modified_by, p.keywords, p.comments = r["PERSON"], r["PERSON2"], r["EMAIL"], note
    d.sections[0].header.paragraphs[0].text = r["HEADER_COMPANY"]
    d.sections[0].footer.paragraphs[0].text = f"Contact: {r['FOOTER_PERSON']}"

    # Write real OOXML review structures, including the relationship and anchors.
    # This works with python-docx releases predating its public comments API.
    paragraph = d.add_paragraph()
    start = OxmlElement("w:commentRangeStart")
    start.set(qn("w:id"), "0")
    paragraph._p.append(start)
    paragraph.add_run("Review note.")
    end = OxmlElement("w:commentRangeEnd")
    end.set(qn("w:id"), "0")
    paragraph._p.append(end)
    reference = OxmlElement("w:commentReference")
    reference.set(qn("w:id"), "0")
    paragraph.add_run()._r.append(reference)
    comments = OxmlElement("w:comments")
    comment = OxmlElement("w:comment")
    for name, value in {"id": "0", "author": r["COMMENT_PERSON"], "initials": "RV",
                        "date": "2024-01-01T00:00:00Z"}.items():
        comment.set(qn(f"w:{name}"), value)
    comment_paragraph, comment_run, comment_text = (OxmlElement(name) for name in ("w:p", "w:r", "w:t"))
    comment_text.text = f"Please contact {r['COMMENT_EMAIL']} before release."
    comment_run.append(comment_text)
    comment_paragraph.append(comment_run)
    comment.append(comment_paragraph)
    comments.append(comment)
    part = Part(PackURI("/word/comments.xml"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
                etree.tostring(comments, xml_declaration=True, encoding="UTF-8", standalone=True),
                d.part.package)
    d.part.relate_to(part, RELATIONSHIP_TYPE.COMMENTS)

    insertion = OxmlElement("w:ins")
    for name, value in {"id": "1", "author": r["TRACKED_PERSON"],
                        "date": "2024-01-01T00:00:00Z"}.items():
        insertion.set(qn(f"w:{name}"), value)
    tracked_run, tracked_text = OxmlElement("w:r"), OxmlElement("w:t")
    tracked_text.text = f"Approved by {r['TRACKED_PERSON']}."
    tracked_run.append(tracked_text)
    insertion.append(tracked_run)
    d.add_paragraph()._p.append(insertion)
    d.save(path)
    return body, [("PERSON", "metadata"), ("PERSON2", "metadata"), ("EMAIL", "metadata"),
                  ("HEADER_COMPANY", "header"), ("FOOTER_PERSON", "footer"),
                  ("COMMENT_PERSON", "comment"), ("COMMENT_EMAIL", "comment"),
                  ("TRACKED_PERSON", "tracked_change")]


def write_pptx(path, title, body, note, r):
    from pptx import Presentation
    from pptx.util import Inches
    pr = Presentation()
    s = pr.slides.add_slide(pr.slide_layouts[1])
    s.shapes.title.text = title
    s.placeholders[1].text = "\n".join(body[:2])
    s.notes_slide.notes_text_frame.text = f"{note} {r['IBAN']} {r['PERSONAL_ID']}"
    s2 = pr.slides.add_slide(pr.slide_layouts[5])
    s2.shapes.title.text = r["COMPANY"]
    s2.shapes.add_textbox(Inches(1), Inches(2), Inches(6), Inches(1)).text_frame.text = body[2]
    picture, recipe = image_payload("Image contact", [r["IMAGE_EMAIL"]])
    s2.shapes.add_picture(picture, Inches(1), Inches(4), width=Inches(8))
    pr.core_properties.author = r["PERSON"]
    pr.core_properties.last_modified_by = r["PERSON2"]
    pr.save(path)
    save_evidence(path, [recipe])
    return body[:3] + [r["COMPANY"]], [("PERSON", "notes"), ("PHONE", "notes"),
                                       ("IBAN", "notes"), ("PERSONAL_ID", "notes"),
                                       ("PERSON", "metadata"), ("PERSON2", "metadata"),
                                       ("IMAGE_EMAIL", "embedded_image")]


def write_xlsx(path, title, body, note, r):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:28]
    visible = [["Name", "Email", "Phone", "Company", "IBAN", "Date"],
               [r["PERSON"], r["EMAIL"], r["PHONE"], r["COMPANY"], r["IBAN"], r["DATE"]],
               [r["PERSON2"], "", "", r["COMPANY"], "", r["DATE2"]]]
    for row in visible:
        ws.append(row)
    hid = wb.create_sheet("internal")
    hid.append(["personal_id", "plate", "address"])
    hid.append([r["PERSONAL_ID"], r["PLATE"], r["ADDRESS"]])
    hid.sheet_state = "hidden"
    wb.properties.creator, wb.properties.lastModifiedBy = r["PERSON"], r["PERSON2"]
    wb.save(path)
    return [" ".join(map(str, row)) for row in visible], [
        ("PERSONAL_ID", "hidden_sheet"), ("PLATE", "hidden_sheet"), ("ADDRESS", "hidden_sheet"),
        ("PERSON", "metadata"), ("PERSON2", "metadata")]


def write_pdf(path, title, body, note, r):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4, invariant=1)
    c.setAuthor(r["PERSON"])
    c.setTitle(title)
    c.setSubject(r["EMAIL"])
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, 790, title)
    c.setFont("Helvetica", 10)
    shown = [line[:110] for line in body]
    for i, line in enumerate(shown):
        c.drawString(60, 766 - i * 24, line)
    picture, recipe = image_payload("Image contact", [r["IMAGE_EMAIL"]])
    reader = ImageReader(picture)
    width, height = reader.getSize()
    c.drawImage(reader, 60, 470, width=475, height=475 * height / width)
    c.save()
    save_evidence(path, [recipe])
    return shown, [("PERSON", "metadata"), ("EMAIL", "metadata"),
                   ("IMAGE_EMAIL", "embedded_image")]


def write_png(path, title, body, note, r, quality="clean"):
    """Draw fake text directly into pixels; no real photograph is needed."""
    picture, recipe = image_payload(title, body, quality)
    with open(path, "wb") as stream:
        stream.write(picture.getvalue())
    save_evidence(path, [recipe])
    return body, []


def write_csv(path, title, body, note, r):
    rows = [["name", "email", "phone", "address", "company", "iban", "personal_id", "plate"],
            [r["PERSON"], r["EMAIL"], r["PHONE"], r["ADDRESS"], r["COMPANY"], r["IBAN"],
             r["PERSONAL_ID"], r["PLATE"]],
            [r["PERSON2"], "", "", "", r["COMPANY"], "", "", ""]]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return [" ".join(row) for row in rows], []


WRITERS = {"docx": write_docx, "pptx": write_pptx, "xlsx": write_xlsx,
           "pdf": write_pdf, "csv": write_csv, "png": write_png}


def entity_type(key):
    """PERSON2 and DATE2 are second instances, not second types."""
    if "_" in key and key not in {"PERSONAL_ID"}:
        return key.rsplit("_", 1)[1]
    return key.rstrip("2") if key[-1] == "2" else key


def build_labels(visible, extras, r):
    text = " ".join(visible)
    seen, out = set(), []
    for key, value in r.items():
        if value and value in text and (entity_type(key), value) not in seen:
            seen.add((entity_type(key), value))
            out.append({"type": entity_type(key), "value": value, "location": "body"})
    for key, where in extras:
        out.append({"type": entity_type(key), "value": r[key], "location": where})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/Desktop/anonymization-corpus"))
    ap.add_argument("--n", type=int, default=5, help="documents per format per language")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if args.n < 1:
        ap.error("--n must be at least 1")

    random.seed(args.seed)
    out = os.path.expanduser(args.out)
    os.makedirs(os.path.join(out, "labels"), exist_ok=True)

    os.makedirs(os.path.join(out, "text"), exist_ok=True)

    index = []
    for lang, locale in LANGS.items():
        fake = Faker(locale)
        Faker.seed(args.seed + len(lang))
        for fmt, writer in WRITERS.items():
            os.makedirs(os.path.join(out, fmt), exist_ok=True)
            for i in range(args.n):
                r = make_record(fake)
                title, body, note = lines(lang, r)
                for quality in QUALITIES if fmt == "png" else ("standard",):
                    stem = f"{lang}_{fmt}_{i:02d}" + (f"_{quality}" if fmt == "png" else "")
                    rel = f"{fmt}/{stem}.{fmt}"
                    kwargs = {"quality": quality} if fmt == "png" else {}
                    visible, extras = writer(os.path.join(out, rel), title, body, note, r, **kwargs)
                    ents = build_labels(visible, extras, r)
                    # Saved body text isolates detector evaluation from extraction.
                    with open(os.path.join(out, "text", f"{stem}.txt"), "w", encoding="utf-8") as f:
                        f.write("\n".join(visible))
                    with open(os.path.join(out, "labels", f"{stem}.json"), "w", encoding="utf-8") as f:
                        json.dump({"file": rel, "language": lang, "format": fmt,
                                   "quality": quality, "entities": ents},
                                  f, ensure_ascii=False, indent=2)
                    index.append({"file": rel, "language": lang, "format": fmt,
                                  "quality": quality, "entities": len(ents),
                                  "hidden": sum(e["location"] != "body" for e in ents)})

    # Provenance. A recall number is only comparable against another run of the
    # same corpus, so the seed and size travel with the documents. The seed alone
    # does not pin them: new Faker data or an edited template changes every value
    # while the seed stays 42, so the labels and the saved text are fingerprinted together.
    # Hashed from the manifest, not from whatever the directory happens to hold,
    # or reusing an output directory with a smaller --n leaves older documents
    # behind and the hash describes a corpus nobody generated. The saved text is
    # included because that, not the label file, is what a detector reads: an
    # edited template can keep every value and still change every detection.
    digest = hashlib.sha256()
    for entry in index:
        stem = os.path.splitext(os.path.basename(entry["file"]))[0]
        for part in ("labels/" + stem + ".json", "text/" + stem + ".txt"):
            with open(os.path.join(out, part), "rb") as f:
                digest.update(f.read())
    with open(os.path.join(out, "corpus.json"), "w", encoding="utf-8") as f:
        json.dump({"seed": args.seed, "n": args.n, "documents": len(index),
                   "identifiers": sum(i["entities"] for i in index),
                   "faker": version("faker"), "corpus_sha256": digest.hexdigest()},
                  f, indent=2)

    with open(os.path.join(out, "index.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "language", "format", "entities", "hidden", "quality"])
        w.writeheader()
        w.writerows(index)

    tot = sum(i["entities"] for i in index)
    print(f"{len(index)} documents, {tot} labelled identifiers, "
          f"{sum(i['hidden'] for i in index)} of them outside the body text")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
