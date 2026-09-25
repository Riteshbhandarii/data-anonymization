import docx
from pathlib import Path

def extract_docx_text(file_path):
    try:
        doc = docx.Document(file_path)
        full_text = []

        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        extracted_text = "\n".join(full_text)

        print("=" * 60)
        print(f"FILE: {Path(file_path).name}")
        print("=" * 60)
        print("[EXTRACTED TEXT PREVIEW]")
        print(extracted_text[:500] + "...\n" if len(extracted_text) > 500 else extracted_text)

        return extracted_text

    except Exception as e:
        print(f"Error reading {file_path}. Ensure it is a valid .docx file.")
        print(f"Details: {e}")
        return None

if __name__ == "__main__":
    target_file = input("Enter DOCX file path: ").strip().strip('"')
    extract_docx_text(target_file)