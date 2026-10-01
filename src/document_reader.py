from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

SUPPORTED_DOCUMENT_EXTENSIONS = {".docx", ".md", ".pdf", ".txt"}
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_CHARACTERS = 50_000


class DocumentInputError(ValueError):
    pass


def _extract_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    blocks: list[str] = []
    for element in document.element.body.iterchildren():
        if isinstance(element, CT_P):
            paragraph = Paragraph(element, document).text.strip()
            if paragraph:
                blocks.append(paragraph)
        elif isinstance(element, CT_Tbl):
            table = Table(element, document)
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(cells):
                    blocks.append("\t".join(cells))
    return "\n".join(blocks)


def _extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data), strict=False)
    if reader.is_encrypted:
        raise DocumentInputError("Password-protected PDFs are not supported.")
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_document_text(
    filename: str,
    data: bytes,
    max_bytes: int = MAX_DOCUMENT_BYTES,
    max_characters: int = MAX_DOCUMENT_CHARACTERS,
) -> str:
    if not data:
        raise DocumentInputError("The selected document is empty.")
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise DocumentInputError(f"Unsupported document type. Choose one of: {supported}.")
    if len(data) > max_bytes:
        raise DocumentInputError(f"Document exceeds the {max_bytes // (1024 * 1024)} MB limit.")

    try:
        if extension in {".md", ".txt"}:
            text = data.decode("utf-8-sig")
        elif extension == ".docx":
            text = _extract_docx(data)
        else:
            text = _extract_pdf(data)
    except DocumentInputError:
        raise
    except (UnicodeDecodeError, Exception) as error:
        raise DocumentInputError("Could not read this document. Check that it is valid and not password-protected.") from error

    text = text.strip()
    if not text:
        if extension == ".pdf":
            raise DocumentInputError("No selectable text found. Scanned PDFs need OCR, which this app does not provide.")
        raise DocumentInputError("No readable text was found in this document.")
    if len(text) > max_characters:
        raise DocumentInputError(
            f"Document text exceeds the {max_characters:,}-character limit. Shorten it and try again."
        )
    return text