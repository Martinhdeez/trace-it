"""Database-backed hot reload through the existing process definition API."""

import os
import uuid

import pytest

from app.core.database import session_factory
from app.features.ingestion.model import Instance
from app.features.processes.model import Symbol

from .conftest import VALID, pdf_bytes
from .test_payment_api import payment_api as payment_api
from .test_process_api import process_api as process_api

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TRACEPAY_TEST_POSTGRES") != "1", reason="Requires test PostgreSQL"
    ),
]


async def test_new_definition_fields_are_used_without_restarting_and_history_is_preserved(
    process_api,
):
    client, _, service = process_api
    definition = {
        "name": "Certificates " + uuid.uuid4().hex,
        "description": "Certificate checks",
        "decision_types": [
            {"name": "ACCEPT", "priority": 0, "is_default": True},
            {"name": "REVIEW", "priority": 1, "requires_human": True},
        ],
        "symbols": [{"name": "holder", "type": "text", "required": True}],
    }
    loaded = await client.post("/processes/definition", json=definition)
    assert loaded.status_code == 200, loaded.text
    process_id = loaded.json()["process"]["id"]
    endpoint = f"/processes/{process_id}/files"
    content = pdf_bytes("Holder: Ana\nExpiry: 21/04/2027\nRenewed: false")
    first = await client.post(endpoint, files={"file": ("certificate.pdf", content)})
    assert first.status_code == 201, first.text
    original = first.json()
    assert original["symbols"]["holder"]["value"] == "Ana"
    before = (await client.get(f"/processes/{process_id}/extraction-plan")).json()
    definition["symbols"].extend(
        [
            {
                "name": "expires_on",
                "type": "date",
                "required": True,
                "extraction": {"labels": ["Expiry"]},
            },
            {"name": "renewed", "type": "boolean"},
        ]
    )
    loaded = await client.post("/processes/definition", json=definition)
    assert loaded.status_code == 200, loaded.text
    after = (await client.get(f"/processes/{process_id}/extraction-plan")).json()
    assert after["fingerprint"] != before["fingerprint"]
    assert any(field["labels"] == ["Expiry"] for field in after["fields"])
    instance_id = original["instance_id"]
    # A duplicate upload is audited, but its new readings cannot overwrite the instance.
    duplicate = (await client.post(endpoint, files={"file": ("certificate.pdf", content)})).json()
    assert not duplicate["created"]
    assert "expires_on" not in duplicate["symbols"]
    refreshed = await client.post(f"/instances/{instance_id}/extract", json={"vlm": False})
    assert refreshed.status_code == 200, refreshed.text
    fresh = refreshed.json()
    assert fresh["symbols"]["expires_on"]["value"] == "2027-04-21"
    assert fresh["symbols"]["renewed"]["value"] is False
    assert fresh["extraction"]["data"]["extraction_plan"]["fingerprint"] == after["fingerprint"]
    assert service.get_result(original["extraction"]["id"])["fields"].keys() == {"holder"}
    async with session_factory() as session:
        instance = await session.get(Instance, instance_id)
        instance.status = "DECIDED"
        await session.commit()
    rejected = await client.post(f"/instances/{instance_id}/extract", json={})
    assert rejected.status_code == 409


async def test_invoice_extension_preserves_default_fields_and_adds_new_symbol(payment_api):
    client, process_id, _, _ = payment_api
    content = pdf_bytes(VALID + "\nExpiry: 21/04/2027")
    endpoint = f"/processes/{process_id}/files"
    initial = (await client.post(endpoint, files={"file": ("invoice.pdf", content)})).json()
    async with session_factory() as session:
        session.add(
            Symbol(
                process_id=process_id,
                name="expires_on",
                type="date",
                required=True,
                extraction={"labels": ["Expiry"], "source": "document"},
            )
        )
        await session.commit()
    response = await client.post(f"/instances/{initial['instance_id']}/extract", json={})
    assert response.status_code == 200, response.text
    extended = response.json()
    assert extended["symbols"]["expires_on"]["value"] == "2027-04-21"
    for name, symbol in initial["symbols"].items():
        assert extended["symbols"][name]["value"] == symbol["value"]
    for name, field in initial["extraction"]["fields"].items():
        assert extended["extraction"]["fields"][name] == field
