from docx import Document
from lxml import etree
import zipfile
import os


def _clear_paragraph_keep_structure(paragraph):
    """
    Clear visible text from a paragraph while preserving paragraph/style structure
    as much as python-docx allows.
    """
    if paragraph.runs:
        for run in paragraph.runs:
            run.text = ""
    else:
        paragraph.text = ""


def _clear_docx_footnote_text(input_docx_path, output_docx_path):
    """
    Remove user-visible footnote/endnote/comment text from DOCX XML while preserving
    separator footnotes and document structure.
    """
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    ns = {"w": word_ns}

    with zipfile.ZipFile(input_docx_path, "r") as zin:
        with zipfile.ZipFile(output_docx_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename in {
                    "word/footnotes.xml",
                    "word/endnotes.xml",
                    "word/comments.xml",
                }:
                    try:
                        root = etree.fromstring(data)

                        # For footnotes/endnotes keep separator notes (-1, 0).
                        if item.filename in {"word/footnotes.xml", "word/endnotes.xml"}:
                            note_tag = "footnote" if "footnotes" in item.filename else "endnote"

                            for note in root.findall(f"w:{note_tag}", ns):
                                note_id = note.get(f"{{{word_ns}}}id")

                                if note_id in ("-1", "0"):
                                    continue

                                for text_node in note.findall(".//w:t", ns):
                                    text_node.text = ""

                        # Comments do not have separator notes, so clear all text nodes.
                        if item.filename == "word/comments.xml":
                            for text_node in root.findall(".//w:t", ns):
                                text_node.text = ""

                        data = etree.tostring(
                            root,
                            xml_declaration=True,
                            encoding="UTF-8",
                            standalone="yes",
                        )
                    except Exception:
                        # If XML parsing fails, leave this part unchanged rather than corrupting the DOCX.
                        pass

                zout.writestr(item, data)


def anonymize_docx(source_path, target_path):
    """
    Blind-review anonymization.

    This function intentionally does NOT delete paragraphs by broad keywords
    such as "university", "author", "conference", commas, or digits because that
    can remove Abstract/Introduction/body text.

    It only removes:
    1. DOCX metadata.
    2. Author block between the paper title and Abstract.
    3. Footnote/endnote/comment text.
    """
    doc = Document(source_path)

    # Clear core properties / metadata.
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
        text = " ".join(paragraph.text.strip().split()).lower()

        if title_index is None and (
            text.startswith("title of the paper")
            or "title of the paper" in text
        ):
            title_index = i

        if abstract_index is None and text.startswith("abstract"):
            abstract_index = i
            break

    # Remove only paragraphs between title and abstract.
    # This is where the author list normally appears in the GBC template.
    if title_index is not None and abstract_index is not None and title_index < abstract_index:
        for paragraph in paragraphs[title_index + 1:abstract_index]:
            _clear_paragraph_keep_structure(paragraph)

    # Backup safety: if the template title was edited and not found, remove only
    # a very small block directly above Abstract, never below Abstract.
    elif abstract_index is not None:
        removed = 0

        for j in range(abstract_index - 1, -1, -1):
            text = paragraphs[j].text.strip()

            if not text:
                continue

            # Stop as soon as we encounter a likely title/heading line.
            lower = text.lower()
            if "title" in lower or len(text) > 180:
                break

            _clear_paragraph_keep_structure(paragraphs[j])
            removed += 1

            if removed >= 3:
                break

    # Do not clear all headers/footers. They may contain conference logo/template data.
    # Only metadata and author block are removed above.

    temp_docx = target_path + ".tmp.docx"
    doc.save(temp_docx)

    _clear_docx_footnote_text(temp_docx, target_path)

    try:
        os.remove(temp_docx)
    except OSError:
        pass
