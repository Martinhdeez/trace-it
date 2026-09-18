from app.features.ingesta.ocr.transcript import remote_lines, transcript_warnings
from app.features.ingesta.pdf.invoice import parse_invoice


def test_remote_fragmented_headings_keep_raw_and_remain_unverified():
    text = (
        "N IF: B 98120774 I BAN: ES 44 1465 0100 9517 0430 2211 Fec "
        "ha: 22/03/2026 Base im poni ble 640,00 IV A 21% 134,40 "
        "TOTAL 774,40 EUR"
    )
    fields, _ = parse_invoice(remote_lines(text, 1, (595, 842)))
    assert fields["supplier_tax_id"].value == "B98120774"
    assert fields["payment_iban"].value == "ES4414650100951704302211"
    assert fields["issued_on"].value == "2026-03-22"
    assert fields["net_amount"].value == "640.00"
    assert fields["gross_amount"].value == "774.40"
    assert all(
        fields[k].status == "UNVERIFIED"
        for k in ("supplier_tax_id", "payment_iban", "gross_amount")
    )
    assert fields["gross_amount"].candidates[0].evidence.text == text


def test_remote_repetition_detection_does_not_reject_normal_identifiers():
    assert transcript_warnings("Factura\n" + "1" * 100)[0]["code"] == "REMOTE_OCR_REPETITION"
    assert transcript_warnings("645,00\n" * 20)
    assert transcript_warnings("IBAN ES4414650100951704302211\nTOTAL 121,00 EUR") == []
