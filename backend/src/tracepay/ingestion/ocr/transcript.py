"""Adapt untrusted remote OCR transcripts; reconstructed headings are not observations."""

import re
from collections import Counter

from tracepay.ingestion.models import TextLine
from tracepay.ingestion.normalize import clean_text


def remote_lines(transcript: str, page: int, point_size):
    # Rebuild only headings, never identifier digits. All resulting fields stay
    # UNVERIFIED because a generative transcript has no calibrated confidence.
    labels = [
        (r"N\s*I\s*F", "NIF"),
        (r"I\s*B\s*A\s*N", "IBAN"),
        (r"F\s*E\s*C\s*H\s*A", "FECHA"),
        (r"P\s*E\s*D\s*I\s*D\s*O", "PEDIDO"),
        (r"F\s*A\s*C\s*T\s*U\s*R\s*A(?:\s*N[º°O]?)?", "FACTURA"),
        (r"B\s*A\s*S\s*E(?:\s+I\s*M\s*P?\s*O\s*N\s*I\s*B\s*L\s*E)?", "BASE"),
        (r"I\s*V\s*A", "IVA"),
        (r"T\s*O\s*T\s*A\s*L", "TOTAL"),
        (r"C\s*L\s*I\s*E\s*N\s*T\s*E", "CLIENTE"),
    ]
    lines = []
    for original in transcript.splitlines():
        text = clean_text(original)
        for pattern, label in labels:
            text = re.sub(r"\b" + pattern + r"(?=\W|\d|$)", "\n" + label, text, flags=re.I)
        for part in text.splitlines():
            if part.strip():
                lines.append(
                    TextLine(
                        id=f"p{page}:remote:{len(lines)}",
                        page=page,
                        raw=original,
                        text=part.strip(),
                        bbox=[0, 0, *point_size],
                        method="vlm",
                    )
                )
    return lines


def transcript_warnings(text: str):
    lines = [clean_text(line) for line in text.splitlines() if line.strip()]
    repeated = bool(re.search(r"(.)\1{29,}", text))
    if len(lines) >= 8:
        repeated |= Counter(lines).most_common(1)[0][1] / len(lines) > 0.4
    return (
        [
            {
                "code": "REMOTE_OCR_REPETITION",
                "message": "Repetitive model output; do not treat it as verified evidence",
            }
        ]
        if repeated
        else []
    )
