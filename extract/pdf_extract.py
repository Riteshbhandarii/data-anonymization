from pathlib import Path
import pymupdf


def extract_pdf(file_path):
    file_path = Path(file_path)

    doc = pymupdf.open(file_path)

    print("=" * 70)
    print(f"FILE: {file_path.name}")
    print("=" * 70)

    # --------------------------------------------------
    # METADATA
    # --------------------------------------------------

    metadata = doc.metadata or {}

    print("\n[METADATA]")

    print(f"Title: {metadata.get('title', '')}")
    print(f"Author: {metadata.get('author', '')}")
    print(f"Subject: {metadata.get('subject', '')}")
    print(f"Keywords: {metadata.get('keywords', '')}")
    print(f"Creator: {metadata.get('creator', '')}")
    print(f"Producer: {metadata.get('producer', '')}")
    print(f"Creation date: {metadata.get('creationDate', '')}")
    print(f"Modification date: {metadata.get('modDate', '')}")

    # --------------------------------------------------
    # PAGE TEXT
    # --------------------------------------------------

    print("\n[PAGES]")

    for page_number, page in enumerate(doc, start=1):

        text = page.get_text("text").strip()

        print(f"\nPage {page_number}")

        if text:
            print(text)
        else:
            print("[No native text found]")

    doc.close()


if __name__ == "__main__":

    file_path = input(
        "Enter PDF file path: "
    ).strip().strip('"')

    extract_pdf(file_path)