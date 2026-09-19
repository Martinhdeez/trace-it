"""The evaluated default must not silently start with another OCR committee."""

import hashlib
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.features.ingestion import quality
from app.features.ingestion.application import create_app
from app.features.ingestion.runtime import ingestion_lifespan
from app.features.ingestion.service import ExtractionService

from .conftest import NoOCR, NoVLM


@pytest.fixture
def verified_settings(settings, monkeypatch):
    expected = {}
    for name in quality.MODEL_FILES:
        content = name.encode()
        path = settings.model_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        expected[name] = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(quality, "MODEL_FILES", expected)
    return replace(settings, ocr_profile="verified", gemini_api_key="test", jev_api_key="test")


def test_profile_validates_bytes_not_just_a_manifest(verified_settings):
    assert quality.validate_quality_profile(verified_settings)["verified"]
    (verified_settings.model_dir / "verify/rec/inference.onnx").write_bytes(b"other-model")
    with pytest.raises(RuntimeError, match="verify/rec/inference.onnx"):
        quality.validate_quality_profile(verified_settings)


def test_dictionary_newlines_are_portable_but_content_is_pinned(verified_settings, monkeypatch):
    expected = {**quality.MODEL_FILES, "rec/keys.txt": hashlib.sha256(b"a\nb\n").hexdigest()}
    monkeypatch.setattr(quality, "MODEL_FILES", expected)
    path = verified_settings.model_dir / "rec/keys.txt"
    for content in (b"a\nb\n", b"a\r\nb\r\n"):
        path.write_bytes(content)
        result = quality.validate_quality_profile(verified_settings)
        assert result["model_sha256"]["rec/keys.txt"] == hashlib.sha256(content).hexdigest()
    path.write_bytes(b"a\nc\n")
    with pytest.raises(RuntimeError, match="rec/keys.txt"):
        quality.validate_quality_profile(verified_settings)


@pytest.mark.parametrize(
    "change",
    [
        {"gemini_api_key": None},
        {"jev_api_key": None},
        {"gemini_model": "different"},
        {"jev_model": "different"},
        {"vlm_url": "http://localhost/v1", "vlm_model": "different"},
    ],
)
def test_profile_rejects_missing_or_different_remote_readers(verified_settings, change):
    with pytest.raises(RuntimeError, match="Verified OCR profile is unavailable"):
        quality.validate_quality_profile(replace(verified_settings, **change))


def test_default_is_verified(settings, monkeypatch):
    monkeypatch.delenv("TRACEPAY_OCR_PROFILE", raising=False)
    from app.features.ingestion.config import Settings

    assert Settings().ocr_profile == "verified"
    assert not quality.validate_quality_profile(settings)["verified"]


def test_server_refuses_to_start_with_an_incomplete_verified_profile(settings):
    settings = replace(settings, ocr_profile="verified")
    service = ExtractionService(settings, NoOCR(), NoVLM())
    with (
        pytest.raises(RuntimeError, match="Verified OCR profile is unavailable"),
        TestClient(create_app(settings, service)),
    ):
        pytest.fail("The application must fail before accepting requests")
    assert not service.threads


async def test_production_server_also_checks_the_profile(settings):
    settings = replace(settings, ocr_profile="verified")
    service = ExtractionService(settings, NoOCR(), NoVLM())
    app = SimpleNamespace(state=SimpleNamespace(ingestion_service=service))
    with pytest.raises(RuntimeError, match="Verified OCR profile is unavailable"):
        async with ingestion_lifespan(app):
            pytest.fail("The production application must reject the incomplete profile")
    assert not service.threads
