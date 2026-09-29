"""Create a small, fully fictional study with known relationships and answers."""

import argparse
import json
from pathlib import Path


def create_suite(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    specifications = [
        ("a1", "A", "Aster Example Analytics", "Alice Example", "Bob Example", "software", "project manager"),
        ("a2", "A", "Aster Example Analytics", "Alice Example", "Bob Example", "software", "project manager"),
        ("b1", "B", "Birch Example Foods", "Carla Example", "David Example", "food", "operations manager"),
    ]
    documents = []
    for index, (doc_id, subject, company, person, other, industry, role) in enumerate(specifications):
        same_contact = index != 1
        second_contact = person if same_contact else other
        content = (
            "# Project allocation memo\n\n"
            f"Organisation: {company}. Industry: {industry}.\n"
            f"Prepared by {person}, {role}.\n\n"
            f"Project Cedar: contact {person}; allocated hours 18.\n"
            f"Project Pine: contact {second_contact}; allocated hours 12.\n"
            "Project scope: process document uploads. Status: approved.\n"
        )
        (directory / f"{doc_id}.md").write_text(content, encoding="utf-8")
        documents.append({
            "id": doc_id, "file": f"{doc_id}.md", "language": "en", "subject_id": subject,
            "naming": {"company": [company], "author": [person]},
            "attributes": {"industry": [industry], "author_role": [role]},
            "utility": [
                {"id": "total_hours", "question": "What is the total allocated hours across both projects? Return only the number.", "answers": ["30"]},
                {"id": "larger_project", "question": "Which project has more allocated hours? Return only Cedar or Pine.", "answers": ["Cedar"]},
                {"id": "same_contact", "question": "Do Cedar and Pine have the same contact person? Answer yes or no, or refuse if unknown.", "answers": ["yes" if same_contact else "no"]},
            ],
        })
    suite = {"schema_version": 1, "synthetic": True, "documents": documents}
    path = directory / "suite.json"
    path.write_text(json.dumps(suite, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    print(create_suite(args.out))
