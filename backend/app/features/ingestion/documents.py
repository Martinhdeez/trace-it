"""Bounded document views for the existing readers; original bytes remain immutable."""

import io
import re
import threading
import warnings
from html import escape
from html.parser import HTMLParser

import pymupdf
from PIL import Image, ImageOps, UnidentifiedImageError

from .config import Settings

# MuPDF document access is serialized, including conversion and evidence rendering.
PDF_LOCK = threading.RLock()
IMAGE_TYPES = {"png": "image/png", "jpeg": "image/jpeg"}


def document_format(content):
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if b"%PDF-" in content[:1024]:
        return "pdf"
    return "html"


class SafeHTML(HTMLParser):
    """Retain text, tables and form values, never active content or resource URLs."""

    tags = frozenset(
        [
            "p",
            "div",
            "br",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "table",
            "thead",
            "tbody",
            "tfoot",
            "tr",
            "td",
            "th",
            "ul",
            "ol",
            "li",
            "dl",
            "dt",
            "dd",
            "pre",
            "b",
            "strong",
            "em",
            "i",
            "span",
            "label",
            "blockquote",
        ]
    )
    blocked = frozenset(
        ["head", "script", "style", "template", "noscript", "iframe", "object", "svg", "canvas"]
    )
    void = frozenset(
        [
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        ]
    )

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []
        self.seen = False
        self.nodes = 0

    def handle_starttag(self, tag, attrs):
        self.nodes += 1
        if self.nodes > 100_000 or len(self.stack) > 256:
            raise ValueError("HTML structure exceeds limit")
        attrs = dict(attrs)
        hidden = (
            any(item[1] for item in self.stack)
            or tag in self.blocked
            or "hidden" in attrs
            or attrs.get("aria-hidden") == "true"
            or bool(
                re.search(
                    r"display\s*:\s*none|visibility\s*:\s*hidden", attrs.get("style") or "", re.I
                )
            )
        )
        if tag not in self.void:
            self.stack.append((tag, hidden))
        self.seen = self.seen or tag in self.tags or tag in {"html", "body", "input"}
        if hidden:
            return
        if tag in self.tags:
            self.parts.append(f"<{tag}>")
        elif tag == "input" and attrs.get("type", "text").lower() not in {
            "hidden",
            "password",
            "file",
            "button",
            "submit",
            "reset",
            "checkbox",
            "radio",
        }:
            self.parts.append(escape(attrs.get("value") or ""))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                for opened, hidden in reversed(self.stack[index:]):
                    if opened in self.tags and not hidden:
                        self.parts.append(f"</{opened}>")
                del self.stack[index:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if not any(item[1] for item in self.stack):
            self.parts.append(escape(data))


def safe_html(content):
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = content.decode("utf-16")
    else:
        declared = re.search(rb"charset\s*=\s*[\"']?([\w-]+)", content[:4096], re.I)
        encoding = declared[1].decode("ascii") if declared else "utf-8-sig"
        try:
            text = content.decode(encoding)
        except (LookupError, UnicodeError) as exc:
            raise ValueError("Invalid HTML character encoding") from exc
    parser = SafeHTML()
    parser.feed(text)
    parser.close()
    if not parser.seen:
        raise ValueError("HTML document must contain markup")
    return "".join(parser.parts)


def as_pdf(content, settings=None):
    """A deterministic page view used by extraction and evidence, never by downloads."""
    settings = settings or Settings()
    kind = document_format(content)
    if kind == "pdf":
        return content
    with PDF_LOCK:
        if kind in IMAGE_TYPES:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(content)) as source:
                        if source.width * source.height > settings.max_image_pixels:
                            raise ValueError("Image pixel count exceeds limit")
                        source.load()
                        corrected = ImageOps.exif_transpose(source).convert("RGBA")
                        background = Image.new("RGBA", corrected.size, "white")
                        background.alpha_composite(corrected)
                        output = io.BytesIO()
                        background.convert("RGB").save(output, format="PNG")
                with pymupdf.open(stream=output.getvalue(), filetype="png") as image:
                    return image.convert_to_pdf()
            except (
                UnidentifiedImageError,
                OSError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
            ) as exc:
                raise ValueError("Invalid or oversized image") from exc

        html = safe_html(content)
        output = io.BytesIO()
        story = pymupdf.Story(
            html=html,
            user_css=(
                "body { font-size: 11pt; } table { border-collapse: collapse; width: 100%; } "
                "td, th { padding: 3pt; border: 1pt solid #888; }"
            ),
        )
        with pymupdf.DocumentWriter(output) as writer:
            for _ in range(settings.max_pages):
                device = writer.begin_page(pymupdf.Rect(0, 0, 595, 842))
                more, _ = story.place(pymupdf.Rect(36, 36, 559, 806))
                story.draw(device)
                writer.end_page()
                if not more:
                    break
            else:
                raise ValueError("HTML page count exceeds limit")
        return output.getvalue()
