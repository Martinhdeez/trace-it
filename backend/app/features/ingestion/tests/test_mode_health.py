from dataclasses import replace

from fastapi.testclient import TestClient

from app.features.ingestion.application import create_app
from app.features.ingestion.service import ExtractionService


def test_api_only_health_does_not_inspect_local_weights(settings):
    class ForbiddenLocal:
        def signature(self):
            raise AssertionError("API-only health must not inspect local models")

    settings = replace(settings, ocr_mode="api")
    service = ExtractionService(settings, ocr=ForbiddenLocal())
    with TestClient(create_app(settings, service)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ocr_models"] is None
