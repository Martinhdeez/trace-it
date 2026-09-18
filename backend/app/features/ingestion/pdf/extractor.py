from app.features.ingestion.config import Settings
from app.features.ingestion.ocr.local import LocalOCR
from app.features.ingestion.ocr.vision import VisionFallback
from app.features.ingestion.schemas import REQUIRED_INVOICE_FIELDS, ExtractOptions

from .invoice import parse_invoice, unresolved
from .native import native_pages, render
from .uncertainty import preserve_unreadable, withhold_uncertain_values


def extract_pdf(
    content: bytes, options: ExtractOptions, settings: Settings, ocr: LocalOCR, vlm: VisionFallback
):
    pages = native_pages(content, settings)
    all_lines = [line for page in pages for line in page["lines"]]
    fields, _ = parse_invoice(all_lines, settings.ocr_min_confidence)
    stage_warnings, page_reports = [], []
    metrics = {"native_pages": 0, "ocr_calls": 0, "vlm_calls": 0}
    for page in pages:
        number, lines = page["number"], page["lines"]
        text = "\n".join(line.text for line in lines)
        chars = len(text.strip())
        # A native cover sheet does not excuse skipping another scanned page.
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
        if chars:
            metrics["native_pages"] += 1
        png = None
        if needs_ocr and options.ocr:
            try:
                png = render(content, number, settings)
                metrics["ocr_calls"] += 1
                recognized = ocr.recognize(png, number, page["size"])
                if recognized:
                    # Keep native observations. Duplicate corroboration is not a conflict;
                    # different observations remain ambiguous rather than overwriting each other.
                    all_lines.extend(recognized)
                    report["method"] = "native+ocr" if chars else "ocr"
                else:
                    stage_warnings.append({"code": "OCR_EMPTY", "page": number})
            except Exception as exc:
                stage_warnings.append(
                    {
                        "code": "OCR_ERROR",
                        "page": number,
                        "error_type": type(exc).__name__,
                        "message": (
                            "OCR unavailable or failed; retry after checking provider configuration"
                        ),
                    }
                )
        elif needs_ocr:
            stage_warnings.append({"code": "OCR_DISABLED", "page": number})
        fields, _ = parse_invoice(all_lines, settings.ocr_min_confidence)
        page_reports.append(report)

    fields, warnings = parse_invoice(all_lines, settings.ocr_min_confidence)
    metrics["ocr_verification_calls"] = 0
    verification = {}
    # A high recognition score did not protect against wrong digits in this
    # corpus. Independently transcribe otherwise-complete scanned invoices;
    # do not spend a second OCR pass on pages already requiring review.
    targets = [
        key
        for key in REQUIRED_INVOICE_FIELDS
        if fields[key].candidates
        and all(c.evidence.method == "ocr" for c in fields[key].candidates)
    ]
    if (
        targets
        and hasattr(ocr, "verify")
        and all(
            fields[key].status == "OBSERVED" for key in REQUIRED_INVOICE_FIELDS if key != "currency"
        )
    ):
        confirmed_lines = []
        try:
            target_pages = {c.evidence.page for key in targets for c in fields[key].candidates}
            for page in pages:
                if page["number"] not in target_pages:
                    continue
                metrics["ocr_calls"] += 1
                metrics["ocr_verification_calls"] += 1
                confirmed_lines.extend(
                    ocr.verify(
                        render(content, page["number"], settings), page["number"], page["size"]
                    )
                )
            check_fields, _ = parse_invoice(confirmed_lines, settings.ocr_min_confidence)
            all_lines.extend(confirmed_lines)
            for key in targets:
                original, check = fields[key], check_fields[key]
                agrees = check.value == original.value and check.status == "OBSERVED"
                verification[key] = {
                    "agrees": agrees,
                    "candidates": [c.model_dump() for c in check.candidates],
                }
                if not agrees:
                    if check.value is not None and check.value != original.value:
                        original.candidates.extend(check.candidates)
                        original.value, original.status = None, "AMBIGUOUS"
                    else:
                        original.status = "UNVERIFIED"
                    warnings.append({"code": "OCR_NOT_CORROBORATED", "field": key})
        except Exception as exc:
            for key in targets:
                fields[key].status = "UNVERIFIED"
            stage_warnings.append(
                {
                    "code": "OCR_ERROR",
                    "stage": "verification",
                    "error_type": type(exc).__name__,
                    "message": "OCR verification unavailable; primary evidence preserved",
                }
            )
    # VLM can transcribe only after deterministic extraction/OCR has been exhausted.
    vision_targets = set(unresolved(fields)) - {"currency"}
    vision_targets.update(
        key
        for key, value in fields.items()
        if value.status == "INVALID"
        and value.candidates
        and all(c.evidence.method == "ocr" for c in value.candidates)
    )
    vision_proposals = {}
    if options.vlm and vision_targets:
        for page in pages:
            try:
                metrics["vlm_calls"] += 1
                generated = vlm.transcribe(
                    render(content, page["number"], settings), page["number"], page["size"]
                )
                generated_fields, generated_warnings = parse_invoice(
                    generated, settings.ocr_min_confidence
                )
                stage_warnings.extend(generated_warnings)
                all_lines.extend(generated)
                for key, original in fields.items():
                    proposed = generated_fields[key]
                    if (
                        original.value is not None
                        and proposed.value is not None
                        and original.value != proposed.value
                    ):
                        original.candidates.extend(proposed.candidates)
                        original.value, original.status = None, "AMBIGUOUS"
                        stage_warnings.append({"code": "MODEL_DISAGREEMENT", "field": key})
                for key in vision_targets:
                    if generated_fields[key].candidates:
                        vision_proposals.setdefault(key, []).extend(
                            c.model_dump() for c in generated_fields[key].candidates
                        )
                    if fields[key].status == "MISSING" and generated_fields[key].candidates:
                        fields[key] = generated_fields[key]
                        fields[key].status = "UNVERIFIED"
                stage_warnings.append({"code": "VLM_REQUIRES_VERIFICATION", "page": page["number"]})
            except Exception as exc:
                stage_warnings.append(
                    {
                        "code": "VLM_ERROR",
                        "page": page["number"],
                        "error_type": type(exc).__name__,
                        "message": "Vision fallback failed; original evidence preserved",
                    }
                )
    # A later reading reporting illegibility must not be hidden by an earlier plausible guess.
    warnings.extend(preserve_unreadable(fields, all_lines))
    warnings.extend(withhold_uncertain_values(fields, verification))
    for key, field in fields.items():
        if field.status != "OBSERVED":
            warnings.append({"code": "FIELD_" + field.status, "field": key})
    return (
        fields,
        {
            "lines": [line.model_dump() for line in all_lines],
            "vision_proposals": vision_proposals,
            "ocr_verification": verification,
        },
        warnings + stage_warnings,
        page_reports,
        metrics,
    )
