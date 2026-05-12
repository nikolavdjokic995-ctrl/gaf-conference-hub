from docx import Document
import os
import re
import shutil
import tempfile
import zipfile

AUTHOR_KEYWORDS = (
    "affiliation", "email", "e-mail", "university", "faculty", "department",
    "institute", "college", "school", "laboratory", "centre", "center",
    "author", "coauthor", "co-author", "corresponding author", "orcid",
)
STOP_SECTION_WORDS = ("abstract", "keywords", "key words", "introduction")


def _iter_paragraphs(parent):
    """Yield normal paragraphs and paragraphs nested inside tables."""
    for para in parent.paragraphs:
        yield para

    for table in parent.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from _iter_paragraphs(cell)


def _blank_paragraph(para):
    """Clear paragraph text while keeping the document structure valid."""
    para.text = ""


def _looks_like_identity_line(text, before_main_text=False):
    clean = " ".join(text.split())
    lower = clean.lower()

    if not clean:
        return False

    if any(word in lower for word in AUTHOR_KEYWORDS):
        return True

    if "@" in clean or "http" in lower or "www." in lower:
        return True

    # Common affiliation markers: superscript numbers are often flattened by python-docx.
    if "," in clean and any(char.isdigit() for char in clean) and len(clean) < 300:
        return True

    # Author/co-author line near the top: short comma-separated list of names.
    if before_main_text and "," in clean and len(clean) < 180:
        words = [w for w in re.split(r"[\s,;]+", clean) if w]
        capitalized = sum(1 for w in words if w[:1].isupper())
        if len(words) >= 2 and capitalized >= max(2, len(words) // 2):
            return True

    return False


def _strip_docx_xml_text(docx_path):
    """Remove identity text from DOCX XML parts not fully exposed by python-docx."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".docx")
    os.close(tmp_fd)

    text_pattern = re.compile(r"(<w:t(?:\s+[^>]*)?>)(.*?)(</w:t>)", re.DOTALL)

    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            if item.filename in {"word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}:
                xml = data.decode("utf-8", errors="ignore")
                xml = text_pattern.sub(r"\1\3", xml)
                data = xml.encode("utf-8")

            zout.writestr(item, data)

    shutil.move(tmp_path, docx_path)


def anonymize_docx(source_path, target_path):
    doc = Document(source_path)

    props = doc.core_properties
    props.author = ""
    props.last_modified_by = ""
    props.comments = ""
    props.title = ""
    props.subject = ""
    props.category = ""
    props.company = ""
    props.keywords = ""

    before_main_text = True

    for para in _iter_paragraphs(doc):
        text = para.text.strip()
        lower = text.lower()

        if any(lower.startswith(word) for word in STOP_SECTION_WORDS):
            before_main_text = False

        if _looks_like_identity_line(text, before_main_text=before_main_text):
            _blank_paragraph(para)

    for section in doc.sections:
        for para in _iter_paragraphs(section.header):
            _blank_paragraph(para)
        for para in _iter_paragraphs(section.footer):
            _blank_paragraph(para)

    doc.save(target_path)
    _strip_docx_xml_text(target_path)
