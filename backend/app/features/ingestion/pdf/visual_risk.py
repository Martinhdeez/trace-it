"""Bounded geometry signals for mixed documents; signals never decide payment."""

import pymupdf

from app.common.normalization import fold

FINANCIAL = ("BASE", "SUBTOTAL", "TOTAL", "IMPORTE", "IVA", "VAT", "TVA", "GESAMT")


def inspect_page(page, lines, spans):
    short = sum(0 < len(s["text"].strip()) <= 2 for s in spans)
    fragmented = len(spans) >= 20 and short / max(1, len(spans)) >= 0.5
    regions = []
    paths = page.get_drawings()
    if len(paths) > 2000 or sum(len(p["items"]) for p in paths) > 10000:
        return {"fragmented": fragmented, "regions": [], "inspection_incomplete": True}
    for path in paths:
        segments = []
        for item in path["items"]:
            if item[0] == "l":
                segments.append(item[1:])
            elif item[0] == "c":
                p0, p1, p2, p3 = item[1:]
                points = [
                    p0 * ((1 - t) ** 3)
                    + p1 * (3 * (1 - t) ** 2 * t)
                    + p2 * (3 * (1 - t) * t * t)
                    + p3 * (t**3)
                    for t in (i / 8 for i in range(9))
                ]
                segments.extend(zip(points, points[1:], strict=False))
        for line in lines:
            if not fold(line.text).startswith(FINANCIAL):
                continue
            x0, y0, x1, y1 = line.bbox
            for a, b in segments:
                if abs(b.x - a.x) < 8:
                    continue
                left, right = max(min(a.x, b.x), x0), min(max(a.x, b.x), x1)
                if right - left < 8:
                    continue
                x = (left + right) / 2
                y = a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x)
                if y0 + 0.2 * (y1 - y0) < y < y1 - 0.2 * (y1 - y0):
                    regions.append({"locator": line.id, "bbox": line.bbox, "code": "CROSSED_VALUE"})
                    break
    for annotation in page.annots() or ():
        if annotation.type[0] in {pymupdf.PDF_ANNOT_STRIKE_OUT, pymupdf.PDF_ANNOT_INK}:
            for line in lines:
                if fold(line.text).startswith(FINANCIAL) and annotation.rect.intersects(
                    pymupdf.Rect(line.bbox)
                ):
                    regions.append(
                        {"locator": line.id, "bbox": line.bbox, "code": "ANNOTATED_VALUE"}
                    )
    # Small raster overlays may obscure/amend native values. Full-page scan images
    # are handled by the OCR path and must not flag every hidden text-layer line.
    for image in page.get_image_info():
        area = pymupdf.Rect(image["bbox"])
        if area.get_area() > 0.25 * page.rect.get_area():
            continue
        for line in lines:
            box = pymupdf.Rect(line.bbox)
            if (
                fold(line.text).startswith(FINANCIAL)
                and (area & box).get_area() > 0.1 * box.get_area()
            ):
                regions.append({"locator": line.id, "bbox": line.bbox, "code": "RASTER_OVERLAY"})
    return {
        "fragmented": fragmented,
        "regions": list({r["locator"]: r for r in regions}.values()),
        "inspection_incomplete": False,
    }


def block_conflicts(fields, pages):
    blocked = {}
    for page in pages:
        risk = page.get("visual_risk", {})
        locators = {r["locator"] for r in risk.get("regions", [])}
        for name, field in fields.items():
            if any(c.evidence.locator in locators for c in field.candidates):
                field.value, field.status = None, "AMBIGUOUS"
                blocked[name] = "visible_amendment"
            elif risk.get("inspection_incomplete") and any(
                c.evidence.page == page["number"] for c in field.candidates
            ):
                field.value, field.status = None, "UNVERIFIED"
                blocked[name] = "visual_inspection_incomplete"
    return blocked
