import re

import pymupdf


class RejectedDocument(ValueError):
    pass


def safe_name(name: str, identity: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_.-]", "_", name.replace("\\", "/").rsplit("/", 1)[-1])
    return f"mail-{identity}-{stem[:120] or 'attachment.pdf'}"


def validate_pdf(content: bytes, maximum: int) -> None:
    if len(content) > maximum:
        raise RejectedDocument("size_limit")
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
        raise RejectedDocument("invalid_pdf")
    try:
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            # Recoverable cross-reference damage also occurs in readable invoices.
            # Let the normal process extraction/OCR pipeline read their original bytes;
            # opening with repair is not itself evidence that the document is unreadable.
            if pdf.needs_pass or not 0 < len(pdf) <= 500:
                raise RejectedDocument("invalid_pdf")
            for page in pdf:
                page.get_contents()
    except (pymupdf.FileDataError, RuntimeError) as exc:
        raise RejectedDocument("invalid_pdf") from exc
