from fastapi.testclient import TestClient

from app.features.ingestion.service import ExtractionService
from app.main import app

from .conftest import NoOCR, NoVLM


def test_main_application_keeps_dev_routes_and_protects_ingestion(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    prior = getattr(app.state, "ingestion_service", None)
    app.state.ingestion_service = service
    try:
        with TestClient(app) as client:
            assert client.get("/health").json() == {"status": "ok"}
            schema = client.get("/openapi.json").json()
            assert schema["info"]["title"] == "trace-it"
            assert {
                "/processes",
                "/login",
                "/v1/extractions",
                "/v1/batches",
                "/processes/{process_id}/files",
                "/instances/{instance_id}/document",
                "/processes/{process_id}/sources/{name}/sync",
                "/processes/{process_id}/sources/{name}/diff",
            } <= set(schema["paths"])
            assert client.get("/v1/extractions/missing").status_code == 401
            assert client.get("/instances/1/document").status_code == 401
            operation = schema["paths"]["/processes/{process_id}/files"]["post"]
            assert operation["operationId"] == "uploadProcessDocument"
            assert any(p["name"] == "x-user-id" for p in operation["parameters"])
        assert service.stop.is_set()
    finally:
        app.state.ingestion_service = prior
