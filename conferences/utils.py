from docx import Document
from lxml import etree

import os
import re
import shutil
import tempfile
import zipfile


EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")


def _clear_paragraph_keep_structure(para):
    """Clear paragraph text but keep the paragraph/runs/styles in the DOCX."""
    for run in para.runs:
        run.text = ""
    if not para.runs:
        para.text = ""


def _normalize_text(value):
    return " ".join((value or "").split()).strip()


def _is_abstract_paragraph(text):
    lower = _normalize_text(text).lower()
    return lower.startswith("abstract")


def _is_title_placeholder(text):
    lower = _normalize_text(text).lower()
    return "title of the paper" in lower or lower.startswith("title of the paper")


def _looks_like_author_block(text):
    """
    Detect only short author-name blocks, not normal body text.
    Example: Nikola Nikolic1, Nenad Simic2, Marko Markovic3
    """
    clean = _normalize_text(text)
    if not clean:
        return False

    lower = clean.lower()

    if EMAIL_RE.search(clean):
        return True

    if any(word in lower for word in ["corresponding author", "co-author", "coauthor", "orcid"]):
        return True

    # Author lines are usually short, before abstract, contain separators or superscript digits,
    # and do not look like a real sentence.
    if len(clean) > 220:
        return False

    sentence_markers = [". ", ";", " should ", " is ", " are ", " provides ", " international "]
    if any(marker in lower for marker in sentence_markers):
        return False

    has_digit = any(ch.isdigit() for ch in clean)
    has_comma = "," in clean
    words = [w for w in re.split(r"[\s,]+", clean) if w]
    capitalized_words = sum(1 for w in words if w[:1].isupper())

    return len(words) >= 2 and capitalized_words >= 2 and (has_digit or has_comma)


def _blank_author_block_before_abstract(doc):
    """
    Remove only the author block immediately above Abstract.
    This avoids deleting Abstract, Introduction, tables, or body paragraphs.
    """
    paragraphs = list(doc.paragraphs)

    abstract_index = None
    for i, para in enumerate(paragraphs):
        if _is_abstract_paragraph(para.text):
            abstract_index = i
            break

    if abstract_index is None:
        return

    # Walk upwards from Abstract and delete only likely author lines.
    deleted_any = False
    for j in range(abstract_index - 1, -1, -1):
        text = _normalize_text(paragraphs[j].text)

        if not text:
            continue

        if _is_title_placeholder(text):
            break

        if _looks_like_author_block(text):
            _clear_paragraph_keep_structure(paragraphs[j])
            deleted_any = True
            continue

        # If we already deleted the author block and reached another non-author line, stop.
        if deleted_any:
            break

        # For conference templates, the author line is normally the first non-empty line above Abstract.
        # If it is not an author-looking line, do not delete anything else.
        break


def _clear_docx_identity_xml(source_docx, target_docx):
    """
    Clear footnote/endnote/comment text while preserving Word's separator footnotes.
    This keeps the footnote line/marker structure but removes affiliation/email content.
    """
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    w_id = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id"

    with zipfile.ZipFile(source_docx, "r") as zin:
        with zipfile.ZipFile(target_docx, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename in {"word/footnotes.xml", "word/endnotes.xml"}:
                    try:
                        root = etree.fromstring(data)
                        note_tag = "w:footnote" if item.filename.endswith("footnotes.xml") else "w:endnote"

                        for note in root.findall(note_tag, ns):
                            note_id = note.get(w_id)
                            # -1 and 0 are Word separator/continuation separator notes. Keep them intact.
                            if note_id in ("-1", "0"):
                                continue
                            for text_node in note.findall(".//w:t", ns):
                                text_node.text = ""

                        data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
                    except Exception:
                        pass

                elif item.filename == "word/comments.xml":
                    try:
                        root = etree.fromstring(data)
                        for text_node in root.findall(".//w:t", ns):
                            text_node.text = ""
                        data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
                    except Exception:
                        pass

                zout.writestr(item, data)


def anonymize_docx(source_path, target_path):
    doc = Document(source_path)

    props = doc.core_properties
    for field in [
        "author",
        "last_modified_by",
        "comments",
        "title",
        "subject",
        "category",
        "keywords",
    ]:
        try:
            setattr(props, field, "")
        except Exception:
            pass

    _blank_author_block_before_abstract(doc)

    # Do not clear headers/footers blindly: the template logo/header should remain.
    # Only remove explicit emails from headers/footers, if present.
    for section in doc.sections:
        for part in [section.header, section.footer]:
            for para in part.paragraphs:
                if EMAIL_RE.search(para.text or ""):
                    _clear_paragraph_keep_structure(para)

    tmp_fd, tmp_docx = tempfile.mkstemp(suffix=".docx")
    os.close(tmp_fd)

    try:
        doc.save(tmp_docx)
        _clear_docx_identity_xml(tmp_docx, target_path)
    finally:
        if os.path.exists(tmp_docx):
            os.remove(tmp_docx)
