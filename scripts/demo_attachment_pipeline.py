"""Week 4 demo: a vague question that the classifier alone can't confidently
route, resolved by attaching a PDF with an order number. Run after
scripts/evaluate_classifier.py has built the exemplar index at least once.
"""

from pathlib import Path
import tempfile

from multiagent_poc.classification.pipeline import handle_question

VAGUE_QUESTION = "Lodówka z nabiałem pokazuje 8 stopni, co robię z towarem i co robię z lodówką?"

PDF_TEXT = "Termometr w lodowce pokazuje wyzsza temperature niz powinien, kontrola sanepidu, temperatury produktow"


def _make_minimal_pdf_with_text(text: str) -> bytes:
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


def run():
    print(f"Question: {VAGUE_QUESTION}\n")

    print("--- without attachment ---")
    result_no_attachment = handle_question(VAGUE_QUESTION)
    print(f"intent={result_no_attachment.decision.effective_intent.value} "
          f"escalate={result_no_attachment.decision.should_escalate} "
          f"confidence={result_no_attachment.decision.raw_classification.confidence:.2f}")

    print("\n--- with attached PDF (order number) ---")
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "zamowienie.pdf"
        pdf_path.write_bytes(_make_minimal_pdf_with_text(PDF_TEXT))
        result_with_attachment = handle_question(VAGUE_QUESTION, attachment_path=pdf_path)

    print(f"intent={result_with_attachment.decision.effective_intent.value} "
          f"escalate={result_with_attachment.decision.should_escalate} "
          f"confidence={result_with_attachment.decision.raw_classification.confidence:.2f} "
          f"used_attachment={result_with_attachment.used_attachment}")


if __name__ == "__main__":
    run()
