"""The reviewer agent's demo invoices (docs/reviewer-agent.md, "Demo pair"): the fallback
pair at 10 % VAT, A (P005, PO-2026-0726) and B (P001, PO-2026-0717), whose totals equal
their order and ERP entry, plus one invoice without a purchase order (MISSING_DATA, the
case no rule can learn). Text-layer PDFs in the layout of factura_41082.pdf.

Usage: make reviewer-demo-pdfs [OUT=output/reviewer-demo]"""

import sys
from pathlib import Path

import pymupdf

BILL_TO = ["Facturar a: Banco Miralmar S.A. - CIF A58231074", "Paseo de la Castellana 214, Madrid"]
PICO = ["Catering Hermanos Pico S.L.", "Valencia · NIF B96233419"]
LEVANTE = ["Suministros Levante S.L.", "Valencia · NIF B46102331"]
PICO_IBAN = "Cuenta de abono (IBAN): ES18 0081 5290 0700 0123 4567"
LEVANTE_IBAN = "Cuenta de abono (IBAN): ES21 0049 1500 0512 3456 7890"

INVOICES = {
    # A: base 2,255.00, VAT 10 % 225.50, total 2,480.50 (= order = ERP, PENDIENTE)
    "hosteleria_A_F26-0726.pdf": [
        *PICO,
        PICO_IBAN,
        "",
        "Nº de factura: F26-0726",
        "Fecha de emisión: 12 de mayo de 2026",
        "Su pedido: PO-2026-0726",
        "",
        *BILL_TO,
        "",
        "  Servicio de catering jornada (1) - 1.500,00 EUR",
        "  Coffee break (1) - 755,00 EUR",
        "",
        "Importe base: 2.255,00 EUR",
        "Cuota IVA (10%): 225,50 EUR",
        "Total factura: 2.480,50 EUR",
    ],
    # B: base 1,804.00, VAT 10 % 180.40, total 1,984.40 (= order = ERP, PENDIENTE)
    "hosteleria_B_F26-0717.pdf": [
        *LEVANTE,
        LEVANTE_IBAN,
        "",
        "Nº de factura: F26-0717",
        "Fecha de emisión: 20 de marzo de 2026",
        "Su pedido: PO-2026-0717",
        "",
        *BILL_TO,
        "",
        "  Menú de empresa (1) - 1.200,00 EUR",
        "  Servicio de sala (1) - 604,00 EUR",
        "",
        "Importe base: 1.804,00 EUR",
        "Cuota IVA (10%): 180,40 EUR",
        "Total factura: 1.984,40 EUR",
    ],
    # No purchase order printed: the engine escalates MISSING_DATA, never learnable (409).
    "sin_pedido_F26-0999.pdf": [
        *LEVANTE,
        LEVANTE_IBAN,
        "",
        "Nº de factura: F26-0999",
        "Fecha de emisión: 2 de abril de 2026",
        "",
        *BILL_TO,
        "",
        "  Material de oficina (1) - 500,00 EUR",
        "",
        "Importe base: 500,00 EUR",
        "Cuota IVA (21%): 105,00 EUR",
        "Total factura: 605,00 EUR",
    ],
}
FOOTER = "Documento generado por el sistema de facturacion del proveedor."


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, lines in INVOICES.items():
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((60, 70), "\n".join(lines), fontname="helv", fontsize=11)
        page.insert_text((60, 780), FOOTER, fontname="helv", fontsize=8)
        doc.save(out / name)
        print(out / name)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "output/reviewer-demo"))
