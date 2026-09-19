"""Blind, bounded re-reading of critical identifiers, retaining original evidence."""

import io
import re

import cv2
import numpy as np
import pymupdf
from PIL import Image

from app.common.normalization import fold
from app.core import events
from app.features.ingestion.ocr.bands import flatten_periodic_bands

from .invoice import parse_invoice
from .native import PDF_LOCK
from .uncertainty import LABELS

CRITICAL_FIELDS = frozenset({"supplier_tax_id", "payment_iban", "purchase_order_ref"})


def native_value(field):
    candidates = [c for c in field.candidates if c.evidence.method == "native"]
    values = {c.value for c in candidates if c.value is not None and not c.error}
    return next(iter(values)) if len(values) == 1 and not any(c.error for c in candidates) else None


def region_for(name, field, readers, page_size):
    # Local coordinates are useful; visual transcripts currently use whole-page boxes.
    boxes = [
        (c.evidence.page, c.evidence.bbox)
        for c in field.candidates
        if c.evidence.method != "vlm" and c.evidence.bbox
    ]
    if not boxes:
        boxes = [
            (line.page, line.bbox)
            for lines in readers.values()
            for line in lines
            if line.method != "vlm" and re.match(LABELS[name], fold(line.text))
        ]
    if not boxes:
        visual_pages = {c.evidence.page for c in field.candidates if c.evidence.method == "vlm"}
        if len(visual_pages) == 1:
            page = next(iter(visual_pages))
            width, height = page_size[page]
            return page, (0, 0, width, height * 0.6)
        return None
    if len({page for page, _ in boxes}) != 1:
        return None
    page = boxes[0][0]
    # Do not combine spatially separate identifiers into a fabricated observation.
    if max(b[1] for _, b in boxes) - min(b[1] for _, b in boxes) > 36:
        return None
    width, height = page_size[page]
    left = max(0, min(b[0] for _, b in boxes) - 24)
    top = max(0, min(b[1] for _, b in boxes) - 8)
    right = min(width, max(b[2] for _, b in boxes) + 48)
    bottom = min(height, max(b[3] for _, b in boxes) + 8)
    return page, (left, top, right, bottom)


def render_region(content, page, box, settings, dpi=600):
    with PDF_LOCK, pymupdf.open(stream=content, filetype="pdf") as document:
        rect = pymupdf.Rect(box)
        scale = min(
            dpi / 72,
            (settings.max_image_pixels / max(1, rect.get_area())) ** 0.5,
        )
        return (
            document[page - 1]
            .get_pixmap(
                matrix=pymupdf.Matrix(scale, scale),
                clip=rect,
                alpha=False,
                colorspace=pymupdf.csRGB,
            )
            .tobytes("png")
        )


def upright(png):
    """Correct only a measurable small line tilt; preserve unknown/large rotations."""
    with Image.open(io.BytesIO(png)) as source:
        gray = np.array(source.convert("L"))
    coords = cv2.findNonZero((gray < 180).astype(np.uint8))
    if coords is None or len(coords) < 10:
        return png, 0.0
    angle = cv2.minAreaRect(coords)[2]
    angle = angle - 90 if angle > 45 else angle
    if not 0.3 <= abs(angle) <= 5:
        return png, 0.0
    height, width = gray.shape
    result = cv2.warpAffine(
        gray,
        cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1),
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderValue=255,
    )
    stream = io.BytesIO()
    Image.fromarray(result).convert("RGB").save(stream, format="PNG")
    return stream.getvalue(), float(angle)


def verify_identifiers(
    content, fields, readers, pages, settings, ocr, vlm, options, vision_enabled, metrics
):
    reports = {}
    if not options.ocr or not vision_enabled:
        return reports
    sizes = {page["number"]: page["size"] for page in pages}
    for name in sorted(CRITICAL_FIELDS):
        field = fields[name]
        forced = name in options.verify_fields
        if not forced and (field.value is not None or native_value(field) is not None):
            continue
        region = region_for(name, field, readers, sizes)
        if region is None:
            continue
        page, box = region
        png, angle = upright(render_region(content, page, box, settings, dpi=150))
        size = (box[2] - box[0], box[3] - box[1])
        original = list(field.candidates)
        original_visual = {
            c.value
            for c in original
            if c.evidence.method == "vlm" and c.value is not None and not c.error
        }
        report = {
            "page": page,
            "bbox": list(box),
            "forced": forced,
            "readers": {},
            "errors": [],
            "value": None,
            "reason": "insufficient_independent_support",
            "deskew_degrees": angle,
        }
        for family, method, enabled, reader in (
            ("primary", "recognize", options.ocr, ocr),
            ("secondary", "verify", options.ocr, ocr),
            ("visual", "transcribe", vision_enabled, vlm),
            ("primary_scale", "recognize", options.ocr, ocr),
        ):
            if not enabled or not hasattr(reader, method):
                continue
            try:
                metric = "vlm_calls" if family == "visual" else "ocr_calls"
                metrics[metric] += 1
                metrics["focused_calls"] = metrics.get("focused_calls", 0) + 1
                input_png = (
                    render_region(content, page, box, settings, dpi=600)
                    if family == "primary_scale"
                    else png
                )
                with events.span("focused_read", field=name, reader=family, page=page) as span:
                    generated = getattr(reader, method)(input_png, page, size)
                    span.set(lines=len(generated))
                # Coordinates always refer back to the original PDF, not the crop.
                generated = [
                    line.model_copy(
                        update={
                            "id": f"{family}:focus:{name}:" + line.id,
                            # A conservative original-page region also covers the
                            # inverse rotation; never report rotated crop coordinates.
                            "bbox": list(box),
                            "preprocessing": [
                                *line.preprocessing,
                                "focused_600dpi" if family == "primary_scale" else "focused_150dpi",
                                f"deskew:{angle:.3f}"
                                if family != "primary_scale"
                                else "original_angle",
                            ],
                        }
                    )
                    for line in generated
                ]
                parsed = parse_invoice(generated, settings.ocr_min_confidence)[0][name]
                field.candidates.extend(parsed.candidates)
                valid = {c.value for c in parsed.candidates if c.value is not None and not c.error}
                eligible = parsed.status in {"OBSERVED", "LOW_CONFIDENCE"} or (
                    family == "visual" and parsed.status == "UNVERIFIED"
                )
                value = (
                    next(iter(valid))
                    if eligible and len(valid) == 1 and not any(c.error for c in parsed.candidates)
                    else None
                )
                report["readers"][family] = {
                    "value": value,
                    "candidates": [c.model_dump() for c in parsed.candidates],
                }
            except Exception as exc:
                report["errors"].append({"reader": family, "type": type(exc).__name__})
        readings = report["readers"]
        visual = readings.get("visual", {}).get("value")
        local = {readings.get(f, {}).get("value") for f in ("primary", "secondary")} - {None}
        scale = readings.get("primary_scale", {}).get("value")
        unreadable = any(c.get("error") for r in readings.values() for c in r["candidates"])
        # Original evidence is not a vote from a new model. A focused reading
        # must corroborate a different reader family, never the text judge.
        possible = (local | ({scale} if scale else set())) & original_visual
        if visual is not None and visual in local and scale in {None, visual}:
            possible.add(visual)
        # Two incompatible corroborated readings remain ambiguous. We retain
        # high-resolution alternatives but do not let interpolation overrule
        # a deskewed observation near the source image's sampling resolution.
        if len(possible) == 1 and not unreadable:
            report.update(value=next(iter(possible)), reason="focused_visual_and_local_agreement")
        elif len(possible) > 1 or len(local | ({visual} if visual else set())) > 1:
            report["reason"] = "focused_conflict"
        report["scale_disagreement"] = scale is not None and scale not in local
        # One final image view is useful only when local readings are stable
        # across scale but the visual reader disagrees. It is not an extra vote.
        if report["value"] is None and scale is not None and local == {scale}:
            try:
                metrics["vlm_calls"] += 1
                metrics["focused_calls"] += 1
                high = {"field": name, "reader": "visual_high", "page": page}
                with events.span("focused_read", **high) as span:
                    generated = vlm.transcribe(
                        render_region(content, page, box, settings), page, size
                    )
                    span.set(lines=len(generated))
                generated = [
                    line.model_copy(
                        update={
                            "id": f"visual:focus_high:{name}:" + line.id,
                            "bbox": list(box),
                            "preprocessing": ["focused_600dpi"],
                        }
                    )
                    for line in generated
                ]
                parsed = parse_invoice(generated, settings.ocr_min_confidence)[0][name]
                field.candidates.extend(parsed.candidates)
                values = {c.value for c in parsed.candidates if c.value is not None and not c.error}
                report["high_visual_candidates"] = [c.model_dump() for c in parsed.candidates]
                if values == {scale} and not any(c.error for c in parsed.candidates):
                    report.update(value=scale, reason="scale_stable_local_and_visual_agreement")
            except Exception as exc:
                report["errors"].append({"reader": "visual_high", "type": type(exc).__name__})
        reports[name] = report
    # If the detector could not locate the identifier, a coherent scanner-band
    # pattern can itself supply a geometric correction. At most once per page.
    corrected_pages = {}
    for name, report in reports.items():
        if report["value"] is not None or any(
            r["value"] for family, r in report["readers"].items() if family != "visual"
        ):
            continue
        page = report["page"]
        if page not in corrected_pages:
            width, height = sizes[page]
            transformed = flatten_periodic_bands(
                render_region(content, page, (0, 0, width, height), settings, dpi=216)
            )
            recovered = {}
            if transformed is not None:
                png, transform = transformed
                for family, method in (("primary", "recognize"), ("secondary", "verify")):
                    if not hasattr(ocr, method):
                        continue
                    try:
                        metrics["ocr_calls"] += 1
                        metrics["focused_calls"] += 1
                        dewarp = {"field": name, "reader": family + "_band_dewarp", "page": page}
                        with events.span("focused_read", **dewarp) as span:
                            generated = getattr(ocr, method)(png, page, sizes[page])
                            span.set(lines=len(generated))
                        generated = [
                            line.model_copy(
                                update={
                                    "id": family + ":band_dewarp:" + line.id,
                                    "bbox": [0, 0, width, height],
                                    "preprocessing": [*line.preprocessing, "periodic_band_dewarp"],
                                }
                            )
                            for line in generated
                        ]
                        recovered[family] = parse_invoice(generated, settings.ocr_min_confidence)[0]
                    except Exception as exc:
                        report["errors"].append(
                            {"reader": family + "_band_dewarp", "type": type(exc).__name__}
                        )
                report["geometric_correction"] = transform
            corrected_pages[page] = recovered
        recovered = corrected_pages[page]
        candidates = [c for values in recovered.values() for c in values[name].candidates]
        fields[name].candidates.extend(candidates)
        local = {
            c.value
            for c in candidates
            if c.value is not None
            and not c.error
            and c.evidence.confidence is not None
            and c.evidence.confidence >= settings.ocr_min_confidence
        }
        visual = {
            c.value
            for c in fields[name].candidates
            if c.evidence.method == "vlm" and c.value is not None and not c.error
        }
        report["dewarped_candidates"] = [c.model_dump() for c in candidates]
        if len(local) == 1 and local <= visual and not any(c.error for c in candidates):
            report.update(value=next(iter(local)), reason="dewarped_local_and_visual_agreement")
    return reports
