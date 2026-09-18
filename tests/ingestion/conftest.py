from pathlib import Path

import pymupdf
import pytest
from tracepay.ingestion.config import Settings
from tracepay.ingestion.models import TextLine
from tracepay.ingestion.normalize import clean_text

MATERIAL = Path(__file__).resolve().parents[2] / ".context/500-sombras-de-alberto"


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models", workers=1)


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
