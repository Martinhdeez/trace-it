import threading

import pymupdf

from app.common.extraction import TextLine
from app.common.normalization import clean_text
from app.features.ingestion.config import Settings

from .layout import reading_order, suspect_spacing, table_membership
from .visual_risk import inspect_page

# MuPDF is not thread-safe. Keep document access/rendering short and serialized;
# OCR runs outside this lock and has its own bounded session.
PDF_LOCK = threading.Lock()


def native_pages(content: bytes, settings: Settings):
    pages = []
    with PDF_LOCK, pymupdf.open(stream=content, filetype="pdf") as document:
        if document.needs_pass:
            raise ValueError("Password-protected PDF is unsupported")
        if not 1 <= len(document) <= settings.max_pages:
            raise ValueError("PDF page count exceeds limit or document is empty")
        for index, page in enumerate(document):
            lines = []
            spans = []
            for block in page.get_text(
                "dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
            )["blocks"]:
                for line in block.get("lines", []):
                    spans.extend(line["spans"])
                    raw = "".join(span["text"] for span in line["spans"])
                    if raw.strip():
                        lines.append(
                            TextLine(
                                id=f"p{index + 1}:native:{len(lines)}",
                                page=index + 1,
                                raw=raw,
                                text=clean_text(raw),
                                bbox=list(line["bbox"]),
                            )
                        )
            lines.sort(key=lambda line: (round(line.bbox[1], 1), line.bbox[0]))
            lines, layout_warnings = table_membership(page, lines)
            # Text coordinates are unrotated, even when the displayed page is rotated.
            lines = reading_order(lines, page.cropbox.width)
            spacing = suspect_spacing(lines)
            if spacing:
                layout_warnings.append("NATIVE_SUSPECT_SPACING")
            image_area = sum(
                abs((r[2] - r[0]) * (r[3] - r[1]))
                for image in page.get_image_info()
                for r in [image["bbox"]]
            )
            pages.append(
                {
                    "number": index + 1,
                    "size": (page.rect.width, page.rect.height),
                    "lines": lines,
                    "image_ratio": min(1, image_area / max(1, page.rect.get_area())),
                    "suspect_spacing": spacing,
                    "warnings": layout_warnings,
                    "visual_risk": inspect_page(page, lines, spans),
                }
            )
    return pages


def render(content: bytes, page_number: int, settings: Settings):
    with PDF_LOCK, pymupdf.open(stream=content, filetype="pdf") as document:
        page = document[page_number - 1]
        scale = settings.ocr_dpi / 72
        area = max(1, page.rect.width * page.rect.height)
        scale = min(scale, (settings.max_image_pixels / area) ** 0.5)
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(scale, scale), alpha=False, colorspace=pymupdf.csRGB
        )
        return pixmap.tobytes("png")
