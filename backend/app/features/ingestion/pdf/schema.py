"""Read a PDF against a request's process contract, without invoice heuristics."""

from app.common.extraction import TextLine
from app.core import events
from app.features.ingestion.schema_fields import read_schema_fields

from .native import native_pages, render


def extract_schema_pdf(content, options, settings, ocr, vlm, field_reader, fields, base=None):
    with events.span("native_text") as span:
        pages = native_pages(content, settings)
        span.set(pages=len(pages))
    lines = (
        [
            TextLine.model_validate(line)
            for line in base.data.get("lines", [])
            if options.secondary_ocr or not line["id"].startswith("secondary:")
        ]
        if base is not None
        else [line for page in pages for line in page["lines"]]
    )
    reports, warnings, images = [], [], {}
    metrics = {"native_pages": 0, "ocr_calls": 0, "vlm_calls": 0, "jev_calls": 0}
    targets = [field for field in fields if field.source == "document"]
    wants_transcript = any(field.source == "text" for field in fields)
    vision_enabled = options.vlm is True or (
        options.vlm is None and getattr(vlm, "configured", False)
    )

    def image(page):
        number = page["number"]
        if number not in images:
            with events.span("render_page", page=number, dpi=settings.ocr_dpi) as span:
                images[number] = render(content, number, settings)
                span.set(image_bytes=len(images[number]))
        return images[number]

    def failure(code, page, exc):
        warnings.append({"code": code, "page": page, "error_type": type(exc).__name__})

    for page in pages:
        number = page["number"]
        text = "\n".join(line.text for line in page["lines"])
        chars = len(text.strip())
        warnings.extend(
            {"code": code, "page": number, "stage": "native"} for code in page.get("warnings", [])
        )
        metrics["native_pages"] += int(bool(chars))
        observed, _ = read_schema_fields(lines, targets, settings.ocr_min_confidence)
        missing = any(reading.value is None for reading in observed.values())
        needs_ocr = (
            page.get("source_format", "pdf") != "html"
            and (bool(targets) or wants_transcript)
            and (
                chars < 40
                or text.count("\ufffd") / max(1, chars) > 0.02
                or (page["image_ratio"] > 0.5 and (missing or wants_transcript))
                or (page.get("suspect_spacing", False) and (missing or wants_transcript))
            )
        )
        report = {
            "page": number,
            "native_chars": chars,
            "method": "native",
            "ocr_needed": needs_ocr,
        }
        if needs_ocr and options.ocr:
            for reader, method in (("primary", "recognize"), ("secondary", "verify")):
                if (reader == "secondary" and not options.secondary_ocr) or not hasattr(
                    ocr, method
                ):
                    continue
                # An invoice extension can reuse the observations from its initial reading.
                if any(line.page == number and line.id.startswith(reader + ":") for line in lines):
                    report["method"] = "native+ocr" if chars else "ocr"
                    continue
                try:
                    metrics["ocr_calls"] += 1
                    with events.span("ocr", page=number, reader=reader) as span:
                        recognized = getattr(ocr, method)(image(page), number, page["size"])
                        span.set(lines=len(recognized))
                    lines.extend(
                        line.model_copy(update={"id": reader + ":" + line.id})
                        for line in recognized
                    )
                    if recognized:
                        report["method"] = "native+ocr" if chars else "ocr"
                    else:
                        warnings.append({"code": "OCR_EMPTY", "page": number, "stage": reader})
                except Exception as exc:
                    failure("OCR_ERROR", number, exc)
        elif needs_ocr and options.mode != "api":
            warnings.append({"code": "OCR_DISABLED", "page": number})
        reports.append(report)

    readings, _ = read_schema_fields(lines, targets, settings.ocr_min_confidence)
    # A complete text layer needs semantic mapping, not a second image transcription.
    if vision_enabled:
        for page, report in zip(pages, reports, strict=True):
            needs_visual_text = wants_transcript and not any(
                line.page == page["number"] and line.method != "native" for line in lines
            )
            # A visual proposal is enough to stop searching later pages for that field;
            # it remains unverified and never becomes a rule input by itself.
            unresolved = any(
                reading.value is None and reading.proposed_value is None
                for reading in readings.values()
            )
            if not report["ocr_needed"] or not (unresolved or needs_visual_text):
                continue
            try:
                params = {
                    "fields": [field.model_dump(mode="json") for field in targets],
                }
                with events.span("vision", page=page["number"], adapter="schema") as span:
                    if options.mode == "api":
                        generated_readers = vlm.transcribe_readers(
                            image(page), page["number"], page["size"], **params
                        )
                        if len(generated_readers) < min(2, getattr(vlm, "independent_readers", 1)):
                            warnings.append(
                                {
                                    "code": "VLM_ERROR",
                                    "stage": "verification",
                                    "page": page["number"],
                                }
                            )
                    else:
                        generated_readers = {
                            "schema_visual": vlm.transcribe(
                                image(page), page["number"], page["size"], **params
                            )
                        }
                    span.set(readers=len(generated_readers))
                metrics["vlm_calls"] += len(generated_readers)
                for reader, generated in generated_readers.items():
                    lines.extend(
                        line.model_copy(update={"id": reader + ":" + line.id}) for line in generated
                    )
                readings, _ = read_schema_fields(lines, targets, settings.ocr_min_confidence)
                if any(generated_readers.values()):
                    report["method"] += "+vlm"
            except Exception as exc:
                failure("VLM_ERROR", page["number"], exc)
            finally:
                if options.mode == "api":
                    images.pop(page["number"], None)

    if targets and vision_enabled and getattr(field_reader, "configured", False):
        with events.span("schema_fields", fields=[field.name for field in targets]):
            readings, field_warnings = field_reader.read(lines, targets)
    else:
        readings, field_warnings = read_schema_fields(lines, targets, settings.ocr_min_confidence)
    warnings.extend(field_warnings)
    return readings, {"lines": [line.model_dump() for line in lines]}, warnings, reports, metrics
