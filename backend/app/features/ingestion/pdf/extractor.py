"""Route incomplete document readings through local, visual and textual experts."""

from app.features.ingestion.config import Settings
from app.features.ingestion.ocr.judge import TextJudge
from app.features.ingestion.ocr.local import LocalOCR
from app.features.ingestion.ocr.vision import VisionFallback
from app.features.ingestion.schemas import ExtractOptions

from .committee import POLICY_VERSION, reconcile
from .invoice import parse_invoice, unresolved
from .native import native_pages, render


def extract_pdf(
    content: bytes,
    options: ExtractOptions,
    settings: Settings,
    ocr: LocalOCR,
    vlm: VisionFallback,
    judge=None,
):
    pages = native_pages(content, settings)
    readers = {"native": [line for page in pages for line in page["lines"]]}
    fields, _ = parse_invoice(readers["native"], settings.ocr_min_confidence)
    warnings, page_reports, images = [], [], {}
    metrics = {
        "native_pages": 0,
        "ocr_calls": 0,
        "ocr_verification_calls": 0,
        "vlm_calls": 0,
        "jev_calls": 0,
    }

    def image(page):
        number = page["number"]
        if number not in images:
            images[number] = render(content, number, settings)
        return images[number]

    def failure(code, stage, exc, page=None):
        warnings.append(
            {
                "code": code,
                "stage": stage,
                "page": page,
                "error_type": type(exc).__name__,
                "message": "Reader unavailable; existing evidence preserved",
            }
        )

    for page in pages:
        number, lines = page["number"], page["lines"]
        text = "\n".join(line.text for line in lines)
        chars = len(text.strip())
        needs_ocr = (
            chars < 40
            or text.count("\ufffd") / max(1, chars) > 0.02
            or (page["image_ratio"] > 0.5 and bool(set(unresolved(fields)) - {"currency"}))
        )
        report = {
            "page": number,
            "native_chars": chars,
            "method": "native",
            "ocr_needed": needs_ocr,
        }
        metrics["native_pages"] += int(bool(chars))
        if needs_ocr and options.ocr:
            for reader, method in (("primary", "recognize"), ("secondary", "verify")):
                if not hasattr(ocr, method):
                    continue
                try:
                    metrics["ocr_calls"] += 1
                    metrics["ocr_verification_calls"] += int(reader == "secondary")
                    recognized = getattr(ocr, method)(image(page), number, page["size"])
                    # Reader-prefixed locators keep identical region IDs distinguishable.
                    recognized = [
                        line.model_copy(update={"id": reader + ":" + line.id})
                        for line in recognized
                    ]
                    readers.setdefault(reader, []).extend(recognized)
                    if recognized:
                        report["method"] = "native+ocr" if chars else "ocr"
                    else:
                        warnings.append({"code": "OCR_EMPTY", "page": number, "stage": reader})
                except Exception as exc:
                    failure("OCR_ERROR", reader, exc, number)
        elif needs_ocr:
            warnings.append({"code": "OCR_DISABLED", "page": number})
        page_reports.append(report)

    fields, decisions, _ = reconcile(readers, settings.ocr_min_confidence)
    vision_enabled = options.vlm is True or (
        options.vlm is None and getattr(vlm, "configured", False)
    )
    # Native missing currency does not justify guessing with a model. On scanned
    # pages any unresolved field, including currency, can trigger image inspection.
    needs_vision = bool(set(unresolved(fields)) - {"currency"}) or (
        any(report["ocr_needed"] for report in page_reports)
        and any(field.status != "OBSERVED" for field in fields.values())
    )
    if vision_enabled and needs_vision:
        for page in pages:
            try:
                metrics["vlm_calls"] += 1
                generated = vlm.transcribe(image(page), page["number"], page["size"])
                readers.setdefault("visual", []).extend(generated)
            except Exception as exc:
                failure("VLM_ERROR", "visual", exc, page["number"])
        fields, decisions, _ = reconcile(readers, settings.ocr_min_confidence)

    judge = judge or TextJudge(settings)
    judge_enabled = options.jev is True or (
        options.jev is None and getattr(judge, "configured", False)
    )
    judgment = {}
    if judge_enabled and ("primary" in readers or "visual" in readers) and unresolved(fields):
        try:
            metrics["jev_calls"] += 1
            judgment = judge.select(readers, fields)
        except Exception as exc:
            failure("JEV_ERROR", "text_judge", exc)
    # Jev recommendations never overwrite image evidence or become another vote.
    fields, decisions, final_warnings = reconcile(readers, settings.ocr_min_confidence)
    warnings.extend(final_warnings)
    for lines in readers.values():
        warnings.extend(parse_invoice(lines, settings.ocr_min_confidence)[1])
    for name, field in fields.items():
        if field.status not in {"OBSERVED", "MISSING"}:
            warnings.append({"code": "FIELD_" + field.status, "field": name})
    warnings = list({str(sorted(w.items())): w for w in warnings}.values())
    verification = {
        name: {
            "agrees": field.status == "OBSERVED",
            "candidates": [
                c.model_dump()
                for c in field.candidates
                if c.evidence.locator.startswith("secondary:")
            ],
        }
        for name, field in fields.items()
    }
    return (
        fields,
        {
            "lines": [line.model_dump() for lines in readers.values() for line in lines],
            "vision_proposals": {
                name: [c.model_dump() for c in field.candidates if c.evidence.method == "vlm"]
                for name, field in fields.items()
                if any(c.evidence.method == "vlm" for c in field.candidates)
            },
            "ocr_verification": verification,
            "committee": {
                "policy": POLICY_VERSION,
                "readers": list(readers),
                "fields": decisions,
                "text_judge": judgment,
            },
        },
        warnings,
        page_reports,
        metrics,
    )
