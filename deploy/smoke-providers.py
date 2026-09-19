"""Explicit paid smoke test: one synthetic scanned invoice, never run by CI."""

import io
import json

import pymupdf
from app.features.ingestion.config import Settings
from app.features.ingestion.quality import validate_quality_profile
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

settings = Settings()
profile = validate_quality_profile(settings)
assert profile["verified"], "Run this check with the production OCR profile"
source = pymupdf.open()
page = source.new_page()
page.insert_text(
    (50, 50),
    "FACTURA\nFactura: F26-1234 Fecha: 21/04/2026\nPedido: PO-2026-0703\n"
    "Limpiezas Turia S.L.\nNIF: B98120774\nIBAN: ES44 1465 0100 9517 0430 2211\n"
    "Cliente: Banco Miralmar CIF A58231074\nBase: 1.490,00\n"
    "IVA (21%): 312,90\nTOTAL: 1.802,90 EUR",
    fontsize=12,
)
scan = pymupdf.open()
scan.new_page().insert_image(page.rect, stream=page.get_pixmap(dpi=180).tobytes("png"))
service = ExtractionService(settings)
try:
    item = service.ingest(io.BytesIO(scan.tobytes()), "provider-smoke.pdf")
    # API mode forces the image-provider path even when local OCR could agree alone.
    result = service.extract(item, ExtractOptions(mode="api", vlm=True, jev=True))
    report = {
        "profile": profile["profile"],
        "metrics": result.metrics,
        "warning_codes": [warning["code"] for warning in result.warnings],
        "critical_fields": {
            name: {"value": field.value, "verification": field.verification}
            for name, field in result.fields.items()
            if name in ("supplier_tax_id", "payment_iban", "purchase_order_ref")
        },
    }
    print(json.dumps(report, indent=2))
    assert result.metrics.get("native_pages", 0) == 0
    assert result.metrics.get("vlm_calls", 0) > 0, (
        "A real visual provider must be called"
    )
    assert not any(code.endswith("_ERROR") for code in report["warning_codes"]), report
    assert result.fields["supplier_tax_id"].value == "B98120774"
    assert result.fields["payment_iban"].value == "ES4414650100951704302211"
finally:
    service.close()
    scan.close()
    source.close()
