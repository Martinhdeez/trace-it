from pathlib import Path

import pymupdf
import pytest

from app.common.extraction import TextLine
from app.common.normalization import clean_text
from app.features.ingestion.config import Settings

MATERIAL = Path(__file__).resolve().parents[5] / ".context/500-sombras-de-alberto"


@pytest.fixture
def settings(tmp_path):
    # General application imports may load .env; unit tests must remain offline.
    return Settings(
        data_dir=tmp_path / "data",
        model_dir=tmp_path / "models",
        workers=1,
        ocr_profile="experimental",
        vlm_url=None,
        vlm_model=None,
        vlm_api_key=None,
        helmcode_api_key=None,
        ocr_mode="hybrid",
        vision_providers=("compatible", "gemini", "helmcode"),
        text_providers=("jev", "helmcode"),
        gemini_api_key=None,
        jev_api_key=None,
    )


def pdf_bytes(text):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=10)
    content = doc.tobytes()
    doc.close()
    return content


def lines(text, method="native", confidence=None):
    return [
        TextLine(
            id=f"p1:{method}:{i}",
            page=1,
            raw=t,
            text=clean_text(t),
            bbox=[0, i * 12, 400, i * 12 + 10],
            method=method,
            confidence=confidence,
        )
        for i, t in enumerate(text.splitlines())
    ]


VALID = """FACTURA
Factura: F26-1234 Fecha: 21/04/2026
Pedido: PO-2026-0703
Limpiezas Turia S.L.
NIF: B98120774
IBAN: ES44 1465 0100 9517 0430 2211
Cliente: Banco Miralmar CIF A58231074
Base: 1.490,00
IVA (21%): 312,90
TOTAL: 1.802,90 EUR"""


class NoOCR:
    def signature(self):
        return {"fake": True}

    def recognize(self, *args):
        raise AssertionError("OCR should not be called")


class NoVLM:
    def transcribe(self, *args):
        raise AssertionError("VLM should not be called")
