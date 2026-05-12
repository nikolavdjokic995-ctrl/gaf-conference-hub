from docx import Document
from pathlib import Path


def anonymize_docx(source_path, target_path):
    doc = Document(source_path)

    for paragraph in doc.paragraphs:
        text = paragraph.text.lower()

        if "author" in text and "surname" in text:
            paragraph.text = ""

        if "title, position, affiliation" in text:
            paragraph.text = ""

    for section in doc.sections:
        footer = section.footer
        for p in footer.paragraphs:
            if "affiliation" in p.text.lower() or "email" in p.text.lower():
                p.text = ""

    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""

    doc.save(target_path)
