"""Reception visibility, scope boundaries and append-only targeted recovery."""

import asyncio
import uuid

import pytest
from pydantic import ValidationError

from app.core.database import session_factory
from app.features.ingestion.tests.conftest import pdf_bytes
from app.features.ingestion.tests.conftest import settings as settings
from app.features.mail_ingestion.config import MailSettings
from app.features.mail_ingestion.documents import RejectedDocument
from app.features.mail_ingestion.model import MailMessage
from app.features.users.model import User
from tests.support import rows
from tests.support.mailbox import synthetic_mail

from .test_pipeline import overview
from .test_pipeline import pipeline as pipeline
from .test_protocol import local_mail as local_mail


def test_concurrency_environment_accepts_only_one(monkeypatch):
    monkeypatch.setenv("MAIL_WORKER_CONCURRENCY", "1")
    assert MailSettings().worker_concurrency == 1
    monkeypatch.setenv("MAIL_WORKER_CONCURRENCY", "2")
    with pytest.raises(ValidationError):
        MailSettings()


async def test_partial_retry_preserves_good_decisions_cursor_and_failure_audit(
    pipeline, monkeypatch
):
    from app.features.mail_ingestion import service

    server, worker, human = pipeline
    pid = worker.settings.process_id
    await worker.initialize()
    bad = pdf_bytes("Holder: review")
    server.deliver(
        synthetic_mail([("good.pdf", pdf_bytes("Holder: open"), "pdf"), ("retry.pdf", bad, "pdf")])
    )
    original = service.validate_pdf

    def reject_once(content, limit):
        if content == bad:
            raise RejectedDocument("invalid_pdf")
        return original(content, limit)

    monkeypatch.setattr(service, "validate_pdf", reject_once)
    await worker.cycle()
    before = await overview(worker, human)
    message = before["messages"][0]
    good, failed = message["attachments"]
    assert message["state"] == "partial" and failed["can_retry"]
    assert good["reading_at"] and good["completed_at"] and not good["requires_review"]
    url = f"/processes/{pid}/mail-ingestion/attachments/{failed['id']}/retry"
    body = {"expected_attempts": message["attempts"]}
    assert (await human.post(url, json={"expected_attempts": 0})).status_code == 409
    async with session_factory() as session:
        previous = await session.get(MailMessage, message["id"])
        old_token = previous.lease_token
        other = await rows.process(session, "Other " + uuid.uuid4().hex)
        operator = User(name="Reader", email=uuid.uuid4().hex + "@test", role="operator")
        session.add(operator)
        await session.commit()
    assert (
        await human.post(url, json=body, headers={"X-User-Id": str(operator.id)})
    ).status_code == 403
    assert (
        await human.post(url.replace(f"/{pid}/", f"/{other.id}/"), json=body)
    ).status_code == 404
    assert (await worker.api.post(url, json=body)).status_code in (401, 403)
    # Two managers clicking the same retry must enqueue it only once.
    responses = await asyncio.gather(human.post(url, json=body), human.post(url, json=body))
    assert sorted(r.status_code for r in responses) == [200, 409]
    stale = await worker.api.post(
        worker.root + f"/messages/{message['id']}/failure",
        headers={"X-Mail-Lease": old_token},
        json={"error": "infrastructure_error"},
    )
    assert stale.status_code == 409
    monkeypatch.setattr(service, "validate_pdf", original)
    await worker.cycle()
    after = await overview(worker, human)
    completed = after["messages"][0]
    assert completed["state"] == "completed"
    assert completed["attachments"][0] == good
    recovered = completed["attachments"][1]
    assert recovered["requires_review"] and recovered["decision"] == "ESCALAR"
    assert recovered["execution_id"] != good["execution_id"]
    assert not recovered["can_retry"]
    assert all(
        after["account"][k] == before["account"][k]
        for k in ("next_uid", "initial_uid", "uidvalidity")
    )
    detail = (await human.get(f"/instances/{good['instance_id']}")).json()
    assert len(detail["decisions"]) == 1
    history_url = f"/processes/{pid}/mail-ingestion/messages/{message['id']}/history"
    history = (await human.get(history_url)).json()
    retries = [e for e in history["activities"] if e["kind"] == "retry_requested"]
    assert len(retries) == 1 and retries[0]["data"]["previous_error"] == "invalid_pdf"
    assert any(e["kind"] == "attachment_failed" for e in history["activities"])
    assert any(e["data"].get("action") == "retry_attachment" for e in history["operator_audit"])
    assert (await human.get(history_url.replace(f"/{pid}/", f"/{other.id}/"))).status_code == 404
    assert (
        await human.post(url, json={"expected_attempts": completed["attempts"]})
    ).status_code == 409


async def test_activity_receipts_are_per_user_monotonic_and_paginated(pipeline):
    server, worker, human = pipeline
    pid = worker.settings.process_id
    root = f"/processes/{pid}/mail-ingestion"
    await worker.initialize()
    server.deliver(synthetic_mail([("a.pdf", pdf_bytes("Holder: open"), "pdf")]))
    await worker.cycle()
    feed = (await human.get(root + "/activity")).json()
    assert not feed["initialized"] and feed["unread"] == 0
    assert {e["kind"] for e in feed["items"]} >= {
        "received",
        "reading",
        "imported",
        "evaluating",
        "completed",
    }
    baseline = feed["latest_id"]
    assert (
        await human.post(root + "/activity/read", json={"through_id": baseline})
    ).status_code == 200
    server.deliver(synthetic_mail([("b.pdf", pdf_bytes("Holder: paid"), "pdf")]))
    await worker.cycle()
    feed = (await human.get(root + "/activity")).json()
    assert feed["unread"] == 2 and feed["initialized"]
    page = (await human.get(root + f"/activity?after_id={baseline}&limit=2")).json()
    assert page["has_more"] and len(page["items"]) == 2
    assert [e["kind"] for e in page["items"]] == ["received", "reading"]
    assert (
        await human.post(root + "/activity/read", json={"through_id": feed["latest_id"] + 1})
    ).status_code == 409
    await human.post(root + "/activity/read", json={"through_id": feed["latest_id"]})
    older = (await human.post(root + "/activity/read", json={"through_id": baseline})).json()
    assert older["through_id"] == feed["latest_id"] and older["unread"] == 0
    async with session_factory() as session:
        user = User(name="Other reader", email=uuid.uuid4().hex + "@test", role="operator")
        session.add(user)
        other = await rows.process(session, "Empty " + uuid.uuid4().hex)
        await session.commit()
    unseen = (await human.get(root + "/activity", headers={"X-User-Id": str(user.id)})).json()
    assert not unseen["initialized"] and unseen["unread"] == 0
    empty = (await human.get(f"/processes/{other.id}/mail-ingestion/activity")).json()
    assert empty["items"] == [] and empty["latest_id"] == 0
    assert (
        await human.post(
            f"/processes/{other.id}/mail-ingestion/activity/read", json={"through_id": baseline}
        )
    ).status_code == 409
    first = (await human.get(root + "?limit=1")).json()
    second = (await human.get(root + f"?limit=1&before_id={first['next_before_id']}")).json()
    assert (
        first["messages"][0]["id"] > second["messages"][0]["id"]
        and second["next_before_id"] is None
    )


async def test_worker_heartbeat_is_independent_and_scoped(pipeline):
    _, worker, human = pipeline
    await worker.initialize()
    state = await worker.request("POST", "/heartbeat", json={"phase": "processing"})
    assert state["heartbeat_at"] and state["worker_phase"] == "processing"
    assert state["last_poll_at"] is None and state["protocol_version"] == 2
    assert (
        await human.post(worker.root + "/heartbeat", json={"phase": "waiting"})
    ).status_code in (401, 403)
    state = await worker.request("POST", "/heartbeat", json={"phase": "stopped"})
    assert state["worker_phase"] == "stopped"


async def test_retry_budget_cannot_be_reset(pipeline):
    server, worker, human = pipeline
    await worker.initialize()
    server.deliver(synthetic_mail([("broken.pdf", b"%PDF-broken", "pdf")]))
    await worker.cycle()
    message = (await overview(worker, human))["messages"][0]
    async with session_factory() as session:
        row = await session.get(MailMessage, message["id"])
        row.attempts = 6
        await session.commit()
    message = (await overview(worker, human))["messages"][0]
    assert not message["attachments"][0]["can_retry"]
    response = await human.post(
        f"/processes/{worker.settings.process_id}/mail-ingestion/attachments/{message['attachments'][0]['id']}/retry",
        json={"expected_attempts": 6},
    )
    assert response.status_code == 409


async def test_resolved_review_and_no_pdf_do_not_leave_actionable_notices(pipeline):
    server, worker, human = pipeline
    pid = worker.settings.process_id
    root = f"/processes/{pid}/mail-ingestion"
    await worker.initialize()
    await human.post(root + "/activity/read", json={"through_id": 0})
    server.deliver(synthetic_mail())
    await worker.cycle()
    assert (await human.get(root + "/activity")).json()["unread"] == 0
    server.deliver(synthetic_mail([("review.pdf", pdf_bytes("Holder: review"), "pdf")]))
    await worker.cycle()
    part = (await overview(worker, human))["messages"][0]["attachments"][0]
    assert part["requires_review"]
    response = await human.post(
        f"/instances/{part['instance_id']}/resolve",
        json={"decision": "PAGAR", "reason": "Reviewed by a manager"},
    )
    assert response.status_code == 200, response.text
    resolved = (await overview(worker, human))["messages"][0]["attachments"][0]
    assert resolved["decision_id"] == part["decision_id"] and resolved["decision"] == "ESCALAR"
    assert not resolved["requires_review"]
