"""Read-only geometry for persisted readings; never changes accepted field values.

Rectangles use normalized coordinates on the displayed (rotated) PDF page.
Native characters and OCR words determine their width, never field-name templates.
"""

import logging
import math
import re
import unicodedata
from typing import Literal

import pymupdf
from pydantic import BaseModel, Field

from app.common.exceptions import NotFoundError
from app.common.extraction import TextLine

from .native import PDF_LOCK, render

logger = logging.getLogger(__name__)


class ReadingLocation(BaseModel):
    candidate: int
    page: int | None
    raw: str
    value: str | None
    method: str
    locator: str
    precision: Literal["text", "ocr", "region", "page", "unavailable"] = "unavailable"
    boxes: list[list[float]] = Field(default_factory=list)


class DocumentLocations(BaseModel):
    extraction_id: str
    sha256: str
    pages: list[dict]
    fields: dict[str, list[ReadingLocation]]
    symbol_fields: dict[str, str] = Field(default_factory=dict)


def compact(text):
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def valid_rect(box):
    if not box or len(box) != 4 or not all(math.isfinite(v) for v in box):
        return None
    rect = pymupdf.Rect(box)
    return rect if not rect.is_empty and not rect.is_infinite else None


def native_units(page):
    units = []
    data = page.get_text("rawdict", flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
    line_id = 0
    for block in data["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                for char in span["chars"]:
                    box = pymupdf.Rect(char["bbox"]) * page.rotation_matrix
                    units.append((char["c"], list(box), line_id))
            line_id += 1
    return units


def ocr_units(lines):
    units = []
    for index, line in enumerate(lines):
        # Focused / dewarped readings do not retain a reversible word transform.
        if any(part.startswith("focus") for part in line.id.split(":")) or any(
            op.startswith("focused_") or op == "periodic_band_dewarp" for op in line.preprocessing
        ):
            continue
        cursor, located = 0, []
        for span in line.spans:
            start = line.raw.find(span.text, cursor)
            if start < 0 or line.raw[cursor:start].strip():
                break
            # Preserve real whitespace, not inferred character widths or pixel gaps.
            located.append((line.raw[cursor:start] + span.text, span.bbox, index))
            cursor = start + len(span.text)
        else:
            if not line.raw[cursor:].strip():
                units.extend(located)
    return units


def matches(units, raw, anchor=None):
    """Keep every glyph/word touched by a literal match, splitting at line breaks."""
    needle = compact(raw)
    if not needle:
        return []
    numeric = re.fullmatch(r"[+-]?\d[\d.,]*", needle) is not None

    def continues_token(char):
        # OCR can omit spaces between an amount, its label and its currency.
        # Still reject substrings of longer numbers, words and mixed identifiers.
        if numeric:
            return char.isdigit() or char in ".,"
        if needle.isalpha():
            return char.isalpha()
        return char.isalnum()

    original, unit_indices = "", []
    previous = None
    for index, (word, box, line) in enumerate(units):
        rect = valid_rect(box)
        center = (rect.tl + rect.br) / 2 if rect is not None else None
        if rect is None or (anchor is not None and center not in anchor):
            continue
        if previous is not None and previous != line:
            original += " "
            unit_indices.append(index)
        part = unicodedata.normalize("NFKC", word).casefold()
        original += part
        unit_indices.extend([index] * len(part))
        previous = line
    offsets = [i for i, char in enumerate(original) if not char.isspace()]
    text = "".join(original[i] for i in offsets)
    found, start = [], 0
    while (start := text.find(needle, start)) >= 0:
        end = start + len(needle)
        left, right = offsets[start], offsets[end - 1] + 1
        # A short value must not resolve to a substring of a different identifier/amount.
        if (left > 0 and needle[0].isalnum() and continues_token(original[left - 1])) or (
            right < len(original) and needle[-1].isalnum() and continues_token(original[right])
        ):
            start = end
            continue
        selected = sorted({unit_indices[i] for i in offsets[start:end]})
        grouped = {}
        for index in selected:
            _, box, line = units[index]
            if line not in grouped:
                grouped[line] = pymupdf.Rect(box)
            else:
                grouped[line] |= pymupdf.Rect(box)
        found.append([list(box) for box in grouped.values()])
        start = end
    return found


def normalized(boxes, page_rect, *, ocr_padding=False):
    output = []
    for box in boxes:
        rect = valid_rect(box)
        if rect is None:
            continue
        if ocr_padding:
            # Recognition boxes can end inside the last glyph. Leave a small,
            # height-relative gutter so the viewer's border does not cover ink.
            margin = min(2.0, max(0.8, rect.height * 0.18))
            rect += (-margin, -margin, margin, margin)
        rect &= page_rect
        if not rect.is_empty:
            output.append(
                [
                    rect.x0 / page_rect.width,
                    rect.y0 / page_rect.height,
                    rect.x1 / page_rect.width,
                    rect.y1 / page_rect.height,
                ]
            )
    return output


def locate_document(content, result, ocr=None, settings=None):
    """Ground saved quotes. Optional local OCR only supplies geometry, never new values."""
    lines = [TextLine.model_validate(line) for line in result.data.get("lines", [])]
    with PDF_LOCK, pymupdf.open(stream=content, filetype="pdf") as document:
        page_info = [
            {"number": i + 1, "width": p.rect.width, "height": p.rect.height}
            for i, p in enumerate(document)
        ]
        pages = {
            i + 1: (p.rect, p.rotation_matrix, native_units(p)) for i, p in enumerate(document)
        }
    output = DocumentLocations(
        extraction_id=result.id, sha256=result.sha256, pages=page_info, fields={}
    )
    # Read each scanned page at most once; LocalOCR additionally caches by image/model.
    supplemental = {}
    for name, field in result.fields.items():
        output.fields[name] = []
        for index, candidate in enumerate(field.candidates):
            evidence = candidate.evidence
            location = ReadingLocation(
                candidate=index,
                page=evidence.page,
                raw=candidate.raw,
                value=candidate.value,
                method=evidence.method,
                locator=evidence.locator,
            )
            output.fields[name].append(location)
            if evidence.page not in pages:
                location.page = None
                continue
            rect, rotation, units = pages[evidence.page]
            anchor = valid_rect(evidence.bbox)
            if anchor is not None and evidence.method == "native":
                anchor *= rotation
            located = matches(units, candidate.raw, anchor)
            if len(located) == 1:
                location.boxes = normalized(located[0], rect)
                location.precision = "text"
                continue
            page_lines = [line for line in lines if line.page == evidence.page]
            source_lines = [line for line in page_lines if line.id == evidence.locator]
            located = matches(ocr_units(source_lines or page_lines), candidate.raw, anchor)
            if not located and evidence.method != "native" and ocr is not None and settings:
                if evidence.page not in supplemental:
                    try:
                        supplemental[evidence.page] = ocr.recognize(
                            render(content, evidence.page, settings),
                            evidence.page,
                            (rect.width, rect.height),
                        )
                    except Exception:
                        logger.info("Geometry OCR unavailable for page %s", evidence.page)
                        supplemental[evidence.page] = []
                located = matches(ocr_units(supplemental[evidence.page]), candidate.raw, anchor)
            if len(located) == 1:
                location.boxes = normalized(located[0], rect, ocr_padding=True)
                location.precision = "ocr"
            elif anchor is not None and (anchor & rect).get_area() < rect.get_area() * 0.8:
                location.boxes = normalized([list(anchor)], rect)
                location.precision = "region" if location.boxes else "page"
            else:
                location.precision = "page"
    return output


def render_page(content, page_number):
    with PDF_LOCK, pymupdf.open(stream=content, filetype="pdf") as document:
        if page_number < 1 or page_number > len(document):
            raise NotFoundError("Document page not found")
        page = document[page_number - 1]
        scale = min(2, (4_000_000 / max(1, page.rect.get_area())) ** 0.5)
        return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")
