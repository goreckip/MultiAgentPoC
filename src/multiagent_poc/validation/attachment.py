"""End-to-end attachment handling: scan -> parse -> plain text.

Text-layer PDFs only — no OCR for scanned/image-only PDFs on purpose, see
requirements.md (5.7). Order matters: scan_file() runs before any byte of
the file is parsed by pypdf, so a malicious PDF exploiting a parser bug never
reaches pypdf in the first place.
"""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from multiagent_poc.validation.attachment_scan import AttachmentRejected, scan_file


def parse_pdf_text(path: Path) -> str:
    """Extracts text from a PDF that has *already* passed scan_file().
    Does not scan itself — callers who haven't scanned yet should use
    process_attachment() instead.
    """
    try:
        reader = PdfReader(str(path))
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as e:
        raise AttachmentRejected(f"could not parse PDF: {e}") from e

    text = "\n".join(pages_text).strip()
    if not text:
        raise AttachmentRejected("PDF has no extractable text layer (scanned/image-only PDFs are not supported)")

    return text


def process_attachment(path: Path) -> str:
    """Scans then extracts text from a PDF attachment. Raises
    AttachmentRejected if the scan fails or the file isn't a readable PDF.
    """
    scan_file(path)
    return parse_pdf_text(path)
