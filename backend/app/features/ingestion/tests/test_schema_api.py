"""Database-backed hot reload through the existing process definition API."""

import os
import uuid

import pytest

from app.core.database import session_factory
from app.features.agents import llm
from app.features.ingestion.model import Instance
from app.features.processes.model import Symbol
from app.features.processes.tests.test_drafts import (
    accept,
    plan,
    post,
    prepare_new,
    scripted_pinned_models,
    scripts,
)
from app.features.users.model import User
from tests.support import rows
from tests.support.models import per_role

from .conftest import VALID, pdf_bytes
from .test_payment_api import payment_api as payment_api
from .test_process_api import process_api as process_api

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TRACEPAY_TEST_POSTGRES") != "1", reason="Requires test PostgreSQL"
    ),
]


async def publish_draft(client, process_id, examples=None):
    if examples is not None:
        staged = (await client.get(f"/processes/{process_id}/draft")).json()
        updated = await client.put(
            f"/processes/{process_id}/draft",
            json={"expected_revision": staged["revision"], "acceptance_examples": examples},
        )
        assert updated.status_code == 200, updated.text
    validated = await client.post(f"/processes/{process_id}/draft/validate")
    assert validated.status_code == 200, validated.text
    draft = validated.json()
    assert draft["validation"]["valid"], draft
    published = await client.post(
        f"/processes/{process_id}/draft/publish",
        json={
            "revision": draft["revision"],
            "validation_hash": draft["validation"]["hash"],
            "reason": "Approve extraction contract",
        },
    )
    assert published.status_code == 201, published.text
    return published.json()


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
    async with session_factory() as session:
        user = await session.get(User, int(client.headers["X-User-Id"]))
        user.role = "manager"
        await session.commit()
    loaded = await client.post("/processes/definition", json=definition)
    assert loaded.status_code == 200, loaded.text
    process_id = loaded.json()["process"]["id"]
    await publish_draft(client, process_id)
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
    staged = (await client.get(f"/processes/{process_id}/extraction-plan")).json()
    assert staged["fingerprint"] == before["fingerprint"]
    await publish_draft(
        client,
        process_id,
        [
            {
                "name": "complete certificate",
                "instance": {"holder": "Ana", "expires_on": "2027-04-21"},
                "decision": "ACCEPT",
                "explanation": "Both required fields are present",
            },
            {
                "name": "expiry missing",
                "instance": {"holder": "Ana"},
                "decision": "REVIEW",
                "explanation": "The newly required expiry is absent",
            },
        ],
    )
    after = (await client.get(f"/processes/{process_id}/extraction-plan")).json()
    assert after["fingerprint"] != before["fingerprint"]
    assert any(field["labels"] == ["Expiry"] for field in after["fields"])
    instance_id = original["instance_id"]
    # A pending duplicate refreshes its symbols under the newly published contract.
    duplicate = (await client.post(endpoint, files={"file": ("certificate.pdf", content)})).json()
    assert not duplicate["created"]
    assert duplicate["symbols"]["expires_on"]["value"] == "2027-04-21"
    assert duplicate["symbols"]["renewed"]["value"] is False
    assert duplicate["extraction"]["id"] != original["extraction"]["id"]
    refreshed = await client.post(f"/instances/{instance_id}/extract", json={"vlm": False})
    assert refreshed.status_code == 200, refreshed.text
    fresh = refreshed.json()
    assert fresh["extraction"]["id"] == duplicate["extraction"]["id"]
    assert fresh["extraction"]["cache_hit"] is True
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
    inert = await client.post(f"/instances/{initial['instance_id']}/extract", json={})
    assert inert.status_code == 200, inert.text
    assert "expires_on" not in inert.json()["symbols"]
    assert inert.json()["extraction"]["id"] == initial["extraction"]["id"]
    async with session_factory() as session:
        await rows.publish_fixture(session, process_id)
    response = await client.post(f"/instances/{initial['instance_id']}/extract", json={})
    assert response.status_code == 200, response.text
    extended = response.json()
    assert extended["symbols"]["expires_on"]["value"] == "2027-04-21"
    for name, symbol in initial["symbols"].items():
        assert extended["symbols"][name]["value"] == symbol["value"]
    for name, field in initial["extraction"]["fields"].items():
        assert extended["extraction"]["fields"][name] == field


async def test_agent_published_field_reaches_extraction_and_rules_without_restart(
    process_api, monkeypatch
):
    client, _, service = process_api
    scripted_pinned_models(monkeypatch)
    async with session_factory() as session:
        manager = await session.get(User, int(client.headers["X-User-Id"]))
        manager.role = "manager"
        await session.commit()

    initial = await post(client, await prepare_new(client, monkeypatch), "publish")
    process_id = initial["published_process_id"]
    endpoint = f"/processes/{process_id}/files"
    content = pdf_bytes(
        "Monitoring certificate for the reviewed operating period\nAmount: 20\nExposure: 250"
    )
    first = await client.post(endpoint, files={"file": ("decided.pdf", content)})
    assert first.status_code == 201, first.text
    historical_id = first.json()["instance_id"]
    run = await client.post(f"/processes/{process_id}/run")
    assert run.status_code == 200 and run.json()["decided"] == 1, run.text
    history = (await client.get(f"/instances/{historical_id}")).json()["decisions"]
    assert history[0]["decision"] == "PAY"
    pending = await client.post(endpoint, files={"file": ("pending.pdf", content)})
    assert pending.status_code == 201, pending.text
    original = pending.json()
    before = (await client.get(f"/processes/{process_id}/extraction-plan")).json()

    proposal = plan(initial["plan"]["name"], field="exposure_hours")
    proposal["symbols"][0]["extraction"] = {"labels": ["Exposure"]}
    # The field stays required. Old evidence cannot validate this new requirement;
    # new missing-field cases must still escalate through the engine's required gate.
    assert proposal["symbols"][0]["required"]
    proposal["rules"][0]["text"] = "If exposure_hours is present and greater than 100, review."
    proposal["symbols"].extend(initial["plan"]["symbols"])
    for example in proposal["examples"]:
        example["instance"]["amount"] = 20
    responses = scripts(proposal, field="exposure_hours")
    responses["compiler"][0]["code"] = responses["compiler"][0]["code"].replace(
        "Decimal(str(instance['exposure_hours'])) > 100",
        "instance.get('exposure_hours') is not None "
        "and Decimal(str(instance['exposure_hours'])) > 100",
    )
    responses["tester"][0]["tests"].append(
        {
            "name": "absent exposure is handled by the required-symbol engine gate",
            "instance_json": '{"amount":20}',
            "sources_json": "{}",
            "others_json": "[]",
            "fires": False,
        }
    )
    monkeypatch.setattr(llm, "model_for", per_role(responses))
    started = await client.post("/process-drafts", json={"process_id": process_id})
    assert started.status_code == 201, started.text
    draft = await post(
        client,
        started.json(),
        "messages",
        message="Review documents with exposure above 100 hours.",
    )
    prepared = await post(client, await accept(client, draft), "prepare")
    assert prepared["preview"]["valid"], prepared["preview"]
    impact = prepared["preview"]["impact"]
    assert impact["coverage"]["evaluated"] == 0
    assert impact["coverage"]["not_evaluable"] == 1
    assert impact["coverage"]["none"]
    assert impact["unchanged"] == 0 and impact["changes"] == [] and impact["errors"] == []
    assert impact["not_evaluable"][0]["missing_symbols"] == ["exposure_hours"]
    assert (await client.get(f"/processes/{process_id}/extraction-plan")).json() == before
    unchanged = await client.post(endpoint, files={"file": ("pending.pdf", content)})
    assert unchanged.json()["extraction"]["id"] == original["extraction"]["id"]

    await post(client, prepared, "publish")
    after = (await client.get(f"/processes/{process_id}/extraction-plan")).json()
    assert after["fingerprint"] != before["fingerprint"]
    assert any(rule["instance_keys"] == ["exposure_hours"] for rule in after["rules"])
    updated = await client.post(endpoint, files={"file": ("pending.pdf", content)})
    assert updated.status_code == 201, updated.text
    refreshed = updated.json()
    assert refreshed["instance_id"] == original["instance_id"]
    assert refreshed["symbols"]["amount"]["value"] == "20"
    assert refreshed["symbols"]["exposure_hours"]["value"] == "250"
    assert refreshed["extraction"]["data"]["extraction_plan"]["fingerprint"] == after["fingerprint"]
    repeated = await client.post(endpoint, files={"file": ("pending.pdf", content)})
    assert repeated.json()["extraction"]["id"] == refreshed["extraction"]["id"]
    assert repeated.json()["extraction"]["cache_hit"]
    assert repeated.json()["extraction"]["metrics"]["schema_calls_this_request"] == 0

    newly_uploaded = await client.post(endpoint, files={"file": ("new.pdf", content)})
    assert newly_uploaded.status_code == 201, newly_uploaded.text
    assert newly_uploaded.json()["symbols"]["exposure_hours"]["value"] == "250"
    missing_content = pdf_bytes(
        "Monitoring certificate with the exposure measurement intentionally absent\nAmount: 20"
    )
    missing = await client.post(endpoint, files={"file": ("missing.pdf", missing_content)})
    assert missing.status_code == 201, missing.text
    assert missing.json()["symbols"]["exposure_hours"]["value"] is None

    run = await client.post(f"/processes/{process_id}/run")
    assert run.status_code == 200 and run.json()["decided"] == 3, run.text
    decided = (await client.get(f"/instances/{original['instance_id']}")).json()
    assert decided["decisions"][0]["decision"] == "REVIEW"
    assert "LIMIT" in decided["decisions"][0]["reason"]
    new_decision = (await client.get(f"/instances/{newly_uploaded.json()['instance_id']}")).json()[
        "decisions"
    ][0]
    assert new_decision["decision"] == "REVIEW" and "LIMIT" in new_decision["reason"]
    missing_decision = (await client.get(f"/instances/{missing.json()['instance_id']}")).json()[
        "decisions"
    ][0]
    assert missing_decision["decision"] == "REVIEW"
    assert missing_decision["reason"] == "MISSING_DATA: exposure_hours"
    assert (await client.get(f"/instances/{historical_id}")).json()["decisions"] == history
    assert set(service.get_result(original["extraction"]["id"])["fields"]) == {"amount"}
