"""Tests for the attachment validation layer (malware scan + PDF parsing).

The malware-detection branch is tested by mocking subprocess.run rather than
trying to trigger a real detection: writing an EICAR test file on this
machine gets it quarantined by Windows Defender before ClamAV can even open
it (verified manually — see decision_log.md), so a live "infected file"
integration test isn't reliable in this environment. The clean-file path is
still exercised for real against the local ClamAV install (skipped if it's
not present, since .clamav/ is a gitignored, machine-local install).
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from pypdf import PdfWriter

from multiagent_poc.config import settings
from multiagent_poc.validation.attachment import parse_pdf_text
from multiagent_poc.validation.attachment_scan import AttachmentRejected, scan_file


def _make_minimal_pdf_with_text(text: str) -> bytes:
    """Hand-built minimal single-page PDF with a real text-drawing content
    stream — pypdf can only write blank pages, not draw text, so a genuine
    "does extraction actually return the right text" test needs this instead
    of relying on an external PDF-generation library just for test fixtures.
    """
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 300 144] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 24 Tf 20 80 Td ({text}) Tj ET".encode("latin-1")
    objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(out)


def _fake_completed_process(returncode: int, stdout: str = "", stderr: str = ""):
    class _Result:
        pass

    r = _Result()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = stderr
    return r


def test_scan_missing_file_raises():
    with pytest.raises(AttachmentRejected, match="not found"):
        scan_file(Path("does_not_exist.pdf"))


def test_scan_oversized_file_raises(tmp_path):
    big_file = tmp_path / "big.pdf"
    big_file.write_bytes(b"0" * (settings.max_attachment_size_bytes + 1))
    with pytest.raises(AttachmentRejected, match="exceeds max size"):
        scan_file(big_file)


def test_scan_clean_result_on_exit_code_0(tmp_path):
    f = tmp_path / "clean.pdf"
    f.write_bytes(b"%PDF-1.4 minimal")
    with patch("subprocess.run", return_value=_fake_completed_process(0)):
        result = scan_file(f)
    assert result.clean is True


def test_scan_raises_on_infected_exit_code_1(tmp_path):
    f = tmp_path / "infected.pdf"
    f.write_bytes(b"%PDF-1.4 minimal")
    with patch("subprocess.run", return_value=_fake_completed_process(1, stdout="infected.pdf: Eicar-Test-Signature FOUND")):
        with pytest.raises(AttachmentRejected, match="flagged"):
            scan_file(f)


def test_scan_raises_on_scan_error_exit_code_2(tmp_path):
    f = tmp_path / "broken.pdf"
    f.write_bytes(b"%PDF-1.4 minimal")
    with patch("subprocess.run", return_value=_fake_completed_process(2, stderr="engine error")):
        with pytest.raises(AttachmentRejected, match="could not complete"):
            scan_file(f)


@pytest.mark.skipif(not Path(settings.clamscan_path).exists(), reason="local ClamAV install not present")
def test_scan_clean_file_against_real_clamav(tmp_path):
    f = tmp_path / "clean.txt"
    f.write_text("to jest zwykla tresc zamowienia, nic zlosliwego")
    result = scan_file(f, timeout_seconds=120)
    assert result.clean is True


def test_parse_pdf_text_rejects_blank_pdf(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    pdf_path = tmp_path / "blank.pdf"
    with pdf_path.open("wb") as f:
        writer.write(f)

    with pytest.raises(AttachmentRejected, match="no extractable text"):
        parse_pdf_text(pdf_path)


def test_parse_pdf_text_extracts_real_text(tmp_path):
    pdf_path = tmp_path / "order.pdf"
    pdf_path.write_bytes(_make_minimal_pdf_with_text("Zamowienie ZM-2024-00981 towar niedostarczony"))

    text = parse_pdf_text(pdf_path)

    assert "ZM-2024-00981" in text


def test_parse_pdf_text_rejects_non_pdf(tmp_path):
    fake_pdf = tmp_path / "not_a_pdf.pdf"
    fake_pdf.write_text("this is just plain text, not a real PDF")

    with pytest.raises(AttachmentRejected, match="could not parse PDF"):
        parse_pdf_text(fake_pdf)
