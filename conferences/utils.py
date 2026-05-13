from docx import Document
from lxml import etree
import zipfile
import os
import re


def _clear_paragraph_text_only(paragraph):
    """
    Clear visible text from a paragraph while keeping the paragraph object/style.
    """
    for run in paragraph.runs:
        run.text = ""


def _clear_docx_review_xml_text(input_docx_path, output_docx_path):
    """
    Clear footnote/endnote/comment text, but preserve footnote separator notes.
    """
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    ns = {"w": word_ns}

    with zipfile.ZipFile(input_docx_path, "r") as zin:
        with zipfile.ZipFile(output_docx_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename in {"word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}:
                    try:
                        root = etree.fromstring(data)

                        if item.filename in {"word/footnotes.xml", "word/endnotes.xml"}:
                            note_tag = "footnote" if item.filename == "word/footnotes.xml" else "endnote"

                            for note in root.findall(f"w:{note_tag}", ns):
                                note_id = note.get(f"{{{word_ns}}}id")

                                # Word uses -1 and 0 for separator/continuation separator.
                                if note_id in ("-1", "0"):
                                    continue

                                for t in note.findall(".//w:t", ns):
                                    t.text = ""

                        if item.filename == "word/comments.xml":
                            for t in root.findall(".//w:t", ns):
                                t.text = ""

                        data = etree.tostring(
                            root,
                            xml_declaration=True,
                            encoding="UTF-8",
                            standalone="yes",
                        )
                    except Exception:
                        # Do not corrupt the DOCX if an XML part cannot be parsed.
                        pass

                zout.writestr(item, data)


def _normal_text(paragraph):
    return " ".join((paragraph.text or "").strip().split())


def _looks_like_author_line(text):
    """
    Conservative detection for the author line in the GBC template.
    It should not match abstract/body text.
    """
    if not text:
        return False

    lower = text.lower()

    if lower.startswith("abstract"):
        return False

    if len(text) > 220:
        return False

    # Typical author blocks contain several names separated by commas
    # and often superscript numbers are flattened as digits by python-docx.
    has_digit = any(ch.isdigit() for ch in text)
    has_comma = "," in text
    words = [w for w in re.split(r"[\s,;]+", text) if w]
    capitalized_words = sum(1 for w in words if w[:1].isupper())

    if has_digit and has_comma and capitalized_words >= 2:
        return True

    # Fallback for a short comma-separated list of names without visible numbers.
    if has_comma and len(words) <= 18 and capitalized_words >= max(2, len(words) // 2):
        return True

    return False


def anonymize_docx(source_path, target_path):
    """
    Very conservative blind-review anonymization.

    It removes only:
    - DOCX metadata,
    - the author line directly between the title and Abstract,
    - footnote/endnote/comment text.

    It does NOT remove abstract, introduction, body paragraphs, tables, figures,
    headers, or footers.
    """
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

    paragraphs = list(doc.paragraphs)

    title_index = None
    abstract_index = None

    for i, paragraph in enumerate(paragraphs):
        text = _normal_text(paragraph).lower()

        if title_index is None and (
            text.startswith("title of the paper")
            or "title of the paper" in text
        ):
            title_index = i

        if abstract_index is None and text.startswith("abstract"):
            abstract_index = i
            break

    # Best case: title and abstract were found. Only inspect the small area between them.
    if title_index is not None and abstract_index is not None and title_index < abstract_index:
        for paragraph in paragraphs[title_index + 1:abstract_index]:
            text = _normal_text(paragraph)
            if _looks_like_author_line(text):
                _clear_paragraph_text_only(paragraph)

    # Fallback: title text was edited. Clear only the nearest author-looking line above Abstract.
    elif abstract_index is not None:
        checked = 0
        for j in range(abstract_index - 1, -1, -1):
            text = _normal_text(paragraphs[j])

            if not text:
                continue

            checked += 1

            if _looks_like_author_line(text):
                _clear_paragraph_text_only(paragraphs[j])
                break

            # Never search too far upward, to avoid deleting body/title/template content.
            if checked >= 4:
                break

    temp_docx = target_path + ".tmp.docx"
    doc.save(temp_docx)

    _clear_docx_review_xml_text(temp_docx, target_path)

    try:
        os.remove(temp_docx)
    except OSError:
        pass
