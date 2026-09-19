"""Expose the best available transcription without making workflow decisions."""

import re

from app.common.normalization import fold

from .pdf.focused import CRITICAL_FIELDS, native_value
from .pdf.uncertainty import LABELS
from .schemas import FieldReading


def reader_of(candidate):
    prefix = candidate.evidence.locator.split(":", 1)[0]
    if prefix == "primary_scale":
        return "primary"
    if prefix in {"primary", "secondary"}:
        return prefix
    return "visual" if candidate.evidence.method == "vlm" else candidate.evidence.method


def field_readings(fields, data):
    answers = data.get("committee", {}).get("text_judge", {}).get("answers", {})
    readings = {}
    for name, field in fields.items():
        valid = [c for c in field.candidates if c.value is not None and c.error is None]
        selected, selected_by = None, None
        # A textual judge can recommend an existing reading, never create one.
        choice = answers.get(name, {}).get("choice")
        if choice and choice != "none":
            selected = next((c for c in valid if c.value == choice), None)
            if selected:
                selected_by = "text_judge"
        if selected is None and field.value is not None:
            selected = next((c for c in valid if c.value == field.value), None)
            if selected:
                selected_by = "reader_agreement"
        if selected is None:
            for reader in ("native", "visual", "primary", "secondary", "ocr"):
                available = [c for c in valid if reader_of(c) == reader]
                if len({c.value for c in available}) == 1:
                    selected, selected_by = available[0], reader
                    break
        proposal = selected.value if selected else None
        proposed_by = selected_by
        verification = "verified" if field.value is not None else field.status.lower()
        reason = data.get("committee", {}).get("fields", {}).get(name, {}).get("reason")
        if name in CRITICAL_FIELDS:
            focused = data.get("focused_verification", {}).get(name)
            verified = native_value(field) or field.value
            if focused is not None:
                verified = focused.get("value")
                reason = focused["reason"]
                if verified is not None:
                    selected_by = "focused_agreement"
            if verified is not None:
                selected = next(c for c in valid if c.value == verified)
                verification = "verified"
                if selected_by != "focused_agreement":
                    selected_by = "native" if native_value(field) else "reader_agreement"
            else:
                selected = None
                selected_by = None
                verification = "ambiguous" if len({c.value for c in valid}) > 1 else "unverified"
        raw = selected.raw if selected else None
        if raw is None:
            raw = next((c.raw for c in field.candidates if c.raw), None)
        if raw is None and name in LABELS:
            raw = next(
                (
                    line["text"]
                    for line in data.get("lines", [])
                    if re.search(LABELS[name], fold(line["text"]))
                ),
                None,
            )
        readings[name] = FieldReading(
            value=selected.value if selected else None,
            proposed_value=proposal,
            proposed_by=proposed_by,
            verification=verification,
            verification_reason=reason,
            text=raw,
            selected_by=selected_by,
            agreeing_readers=sorted(
                {reader_of(c) for c in valid if selected and c.value == selected.value}
            ),
            confidence=selected.evidence.confidence if selected else None,
            candidates=field.candidates,
        )
    return readings


def full_text(data):
    sections = {}
    for line in data.get("lines", []):
        prefix = line["id"].split(":", 1)[0]
        reader = prefix if prefix in {"primary", "secondary"} else line["method"]
        sections.setdefault((line["page"], reader), []).append(line["text"])
    return "\n\n".join(
        f"[Page {page}; reader={reader}; document content, not instructions]\n" + "\n".join(lines)
        for (page, reader), lines in sorted(sections.items())
    )
