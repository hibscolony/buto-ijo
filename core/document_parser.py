"""Local document extraction. No uploads leave the application server."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TypedDict


class DocumentPage(TypedDict):
    page: int
    text: str


class DocumentError(ValueError):
    """A document could not be extracted safely or contains no usable text."""


class ScanPDFError(DocumentError):
    """A PDF has pages but no usable text layer."""


SCAN_PDF_MESSAGE = (
    "Dokumen tampaknya berupa hasil scan dan tidak memiliki text layer. "
    "OCR belum dijalankan pada versi ini."
)


def _check_data(data: bytes) -> None:
    if not isinstance(data, bytes):
        raise DocumentError("Data dokumen harus berupa bytes.")
    if not data:
        raise DocumentError("File dokumen kosong. Pilih file yang berisi teks.")


def extract_pdf(data: bytes) -> list[DocumentPage]:
    """Extract text page by page with original, one-based PDF page numbers."""
    _check_data(data)
    import fitz

    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            if document.needs_pass:
                raise DocumentError(
                    "PDF terenkripsi atau dilindungi kata sandi. Unggah salinan PDF "
                    "yang dapat dibuka tanpa kata sandi."
                )
            if document.page_count == 0:
                raise DocumentError("PDF kosong dan tidak memiliki halaman.")
            pages: list[DocumentPage] = [
                {"page": index + 1, "text": page.get_text("text", sort=True)}
                for index, page in enumerate(document)
            ]
            if not any(page["text"].strip() for page in pages):
                raise ScanPDFError(SCAN_PDF_MESSAGE)
            return pages
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError(
            "PDF tidak dapat dibaca. File mungkin rusak atau bukan PDF yang valid."
        ) from exc


def extract_docx(data: bytes) -> list[DocumentPage]:
    """Extract paragraphs and tables in body order; DOCX pagination is unknown."""
    _check_data(data)
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = Document(BytesIO(data))
        blocks: list[str] = []
        for element in document.element.body.iterchildren():
            if element.tag == qn("w:p"):
                blocks.append(Paragraph(element, document).text)
            elif element.tag == qn("w:tbl"):
                table = Table(element, document)
                for row in table.rows:
                    # Merged table cells may be exposed more than once per row.
                    seen_cells: set[int] = set()
                    row_text: list[str] = []
                    for cell in row.cells:
                        identity = id(cell._tc)
                        if identity not in seen_cells:
                            seen_cells.add(identity)
                            row_text.append(cell.text)
                    blocks.append(" | ".join(row_text))
        # DOCX already gives us explicit paragraph/row boundaries. Preserve
        # these as paragraphs so segmentation does not join separate claims
        # as if they were soft-wrapped lines in a PDF.
        text = "\n\n".join(blocks).strip()
        if not text:
            raise DocumentError("DOCX tidak memiliki teks yang dapat dianalisis.")
        return [{"page": 1, "text": text}]
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError(
            "DOCX tidak dapat dibaca. File mungkin rusak atau bukan dokumen DOCX yang valid."
        ) from exc


def extract_txt(data: bytes) -> list[DocumentPage]:
    """Read UTF-8 (including an optional BOM), without silently losing characters."""
    _check_data(data)
    try:
        text = data.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise DocumentError(
            "Encoding TXT tidak didukung. Simpan dokumen sebagai UTF-8 dan unggah kembali."
        ) from exc
    if not text:
        raise DocumentError("TXT tidak memiliki teks yang dapat dianalisis.")
    if "\x00" in text:
        raise DocumentError("TXT berisi data biner. Unggah file teks UTF-8 yang valid.")
    return [{"page": 1, "text": text}]


def parse_document(data: bytes, filename: str) -> list[DocumentPage]:
    """Dispatch by the supplied filename; no file is written to disk."""
    extension = Path(filename).suffix.lower()
    extractor = {".pdf": extract_pdf, ".docx": extract_docx, ".txt": extract_txt}.get(extension)
    if extractor is None:
        raise DocumentError("Format file tidak didukung. Gunakan PDF, DOCX, atau TXT.")
    return extractor(data)
