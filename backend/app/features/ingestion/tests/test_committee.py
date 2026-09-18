import io
from dataclasses import replace

import pytest

from app.features.ingestion.ocr.journal import recorded_call
from app.features.ingestion.pdf.committee import reconcile
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import VALID, NoOCR, NoVLM, lines, pdf_bytes


def test_incomplete_first_reading_still_gets_second_reader(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("NIF: B98120774", "ocr", 0.99)

        def verify(self, *args):
            return lines("NIF: B98120774\nTOTAL: 100,00 EUR", "ocr", 0.99)

    service = ExtractionService(settings, OCR(), NoVLM())
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf"), ExtractOptions()
    )
    assert result.metrics["ocr_verification_calls"] == 1
    assert result.fields["supplier_tax_id"].value == "B98120774"
    assert result.fields["gross_amount"].value is None
    assert result.fields["gross_amount"].candidates[0].value == "100.00"


def test_visual_auto_escalation_recovers_corroborated_fields_and_jev_cannot_vote(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("NIF: B98120774", "ocr", 0.99)

        def verify(self, *args):
            return lines("TOTAL: 1.802,90 EUR", "ocr", 0.99)

    class Visual:
        configured = True

        def transcribe(self, *args):
            return lines(VALID, "vlm")

    class Judge:
        configured = True

        def select(self, readers, fields):
            assert "visual" in readers
            return {
                "answers": {"payment_iban": {"choice": "ES4414650100951704302211"}},
                "visual_vote": False,
            }

    service = ExtractionService(settings, OCR(), Visual(), Judge())
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf"), ExtractOptions()
    )
    assert result.metrics["vlm_calls"] == result.metrics["jev_calls"] == 1
    assert result.fields["supplier_tax_id"].value == "B98120774"
    assert result.fields["gross_amount"].value == "1802.90"
    assert result.fields["payment_iban"].value is None
    assert result.data["committee"]["text_judge"]["visual_vote"] is False


def test_explicit_provider_opt_out(settings):
    class ConfiguredVisual(NoVLM):
        configured = True

    class Judge:
        configured = True

        def select(self, *args):
            pytest.fail("Text judge must not run")

    service = ExtractionService(settings, NoOCR(), ConfiguredVisual(), Judge())
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf"),
        ExtractOptions(ocr=False, vlm=False, jev=False),
    )
    assert result.metrics["vlm_calls"] == result.metrics["jev_calls"] == 0


def test_agreeing_local_errors_do_not_pass_partial_arithmetic_check():
    text = "Base: 1.165,90\nIVA 21%: 24484"
    fields, _, _ = reconcile(
        {"primary": lines(text, "ocr", 0.99), "secondary": lines(text, "ocr", 0.99)}, 0.9
    )
    assert fields["vat_amount"].value is None
    assert fields["vat_amount"].candidates[0].value == "24484.00"


def test_visual_minority_and_illegibility_are_not_outvoted():
    readers = {
        "primary": lines(VALID, "ocr", 0.99),
        "secondary": lines(VALID, "ocr", 0.99),
        "visual": lines(VALID.replace("9517", "[ILLEGIBLE]"), "vlm"),
    }
    fields, _, _ = reconcile(readers, 0.9)
    assert fields["payment_iban"].value is None
    readers["visual"] = lines(VALID.replace("9517", "8517"), "vlm")
    fields, _, _ = reconcile(readers, 0.9)
    assert fields["payment_iban"].status == "AMBIGUOUS"
    assert len({c.value for c in fields["payment_iban"].candidates}) == 2


def test_provider_activation_changes_extraction_cache(settings):
    item = {"sha256": "a", "kind": "invoice"}
    before = ExtractionService(settings, NoOCR()).cache_key(item, ExtractOptions())
    after = ExtractionService(replace(settings, gemini_api_key="test-key"), NoOCR()).cache_key(
        item, ExtractOptions()
    )
    assert before != after


def test_uncertain_remote_delivery_is_not_automatically_retried(tmp_path):
    calls = []

    def timeout():
        calls.append(True)
        raise TimeoutError("delivery uncertain")

    with pytest.raises(TimeoutError):
        recorded_call(tmp_path, {"request": 1}, timeout)
    with pytest.raises(RuntimeError, match="delivery uncertain"):
        recorded_call(tmp_path, {"request": 1}, timeout)
    assert len(calls) == 1
