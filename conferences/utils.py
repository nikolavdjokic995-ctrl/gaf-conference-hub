from docx import Document
from pathlib import Path

def anonymize_docx(source_path, target_path):
    doc = Document(source_path)

    # Remove core properties
    props = doc.core_properties
    props.author = ""
    props.last_modified_by = ""
    props.comments = ""
    props.title = ""
    props.subject = ""
    props.category = ""
    props.company = ""
    props.keywords = ""

    # Remove author lines under title
    for para in doc.paragraphs:
        text = para.text.strip()

        # remove lines with author names / affiliations
        if (
            "," in text
            and any(char.isdigit() for char in text)
            and len(text) < 300
        ):
            para.text = ""

        # remove footnote-like affiliation text
        if (
            "affiliation" in text.lower()
            or "email" in text.lower()
            or "university" in text.lower()
            or "faculty" in text.lower()
            or "department" in text.lower()
        ):
            para.text = ""

    # Remove headers
    for section in doc.sections:
        header = section.header
        for para in header.paragraphs:
            para.text = ""

        footer = section.footer
        for para in footer.paragraphs:
            para.text = ""

    doc.save(target_path)
