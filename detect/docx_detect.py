import docx
from presidio_analyzer import AnalyzerEngine
from pathlib import Path


def detect_docx_pii(file_path):
    doc = docx.Document(file_path)
    full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    analyzer = AnalyzerEngine()
    results = analyzer.anzlyze(text=full_text, language="en")

    print("=" * 60)
    print(f"DETECTION RESULTS: {Path(file_path).name}")
    print("=" * 60)
    print(f"Found {len(results)} sensitive entities:\n")

    for res in results:
        extracted_value = full_text[res.start:res.end]
        print(
            f"- {res.entity_type:<12} | Score: {res.score:.2f} | Value: {extracted_value}")


if __name__ == "__main__":
    target = input("Enter DOCX file path: ").strip().strip('"')
    detect_docx_pii(target)
