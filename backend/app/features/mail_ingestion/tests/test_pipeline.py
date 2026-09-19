import asyncio
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select, update

from app.core.database import engine, session_factory
from app.features.ingestion.model import Instance
from app.features.ingestion.runtime import current_service
from app.features.ingestion.service import ExtractionService
from app.features.ingestion.tests.conftest import NoOCR, NoVLM, pdf_bytes
from app.features.ingestion.tests.conftest import settings as settings
from app.features.mail_ingestion.model import MailAccount, MailMessage
from app.features.mail_ingestion.worker import Worker
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.rules.model import Rule
from app.main import app
from tests.support import rows
from tests.support.mailbox import synthetic_mail
from tests.support.users import manager

from .test_protocol import local_mail as local_mail


async def seed_process(session):
    process = await rows.process(session, "Mail test " + uuid.uuid4().hex)
    process.gathering_email = "migration-test@j-aautomation.com"
    for name, priority in (("PAGAR", 1), ("NO_PAGAR", 2), ("ESCALAR", 3)):
        session.add(
            DecisionType(
                process_id=process.id,
                name=name,
                priority=priority,
                is_default=name == "PAGAR",
                requires_human=name == "ESCALAR",
            )
        )
    session.add(Symbol(process_id=process.id, name="holder", type="text", required=True))
    for name, code in (
        ("NO_PAGAR", "instance['holder'] == 'paid'"),
        ("ESCALAR", "instance['holder'] == 'review'"),
    ):
        session.add(
            Rule(
                process_id=process.id,
                text=name,
                type="prohibition",
                decision=name,
                code="def evaluate(instance, sources, others):\n"
                f"    return {{'fires': {code}, 'reason': 'TEST_RULE'}}",
                hash=name,
                status="active",
                report={"valid": True},
            )
        )
    await rows.publish_fixture(session, process.id)
    return process.id


@pytest.fixture
async def pipeline(local_mail, settings):
    server, cfg = local_mail
    token = uuid.uuid4().hex + uuid.uuid4().hex
    async with session_factory() as session:
        cfg.process_id = await seed_process(session)
        account = MailAccount(
            process_id=cfg.process_id,
            host=cfg.imap_host,
            username=cfg.imap_username,
            folder=cfg.imap_folder,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
        )
        session.add(account)
        await session.commit()
    extraction = ExtractionService(settings, NoOCR(), NoVLM())
    app.dependency_overrides[current_service] = lambda: extraction
    async with (
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + token},
        ) as api,
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as human,
    ):
        await manager(human)
        worker = Worker(cfg, api)
        try:
            yield server, worker, human
        finally:
            app.dependency_overrides.pop(current_service)
            async with session_factory() as session:
                await session.execute(
                    update(Process).where(Process.id == cfg.process_id).values(gathering_email=None)
                )
                await session.commit()
            extraction.close()
            await engine.dispose()


async def overview(worker, human):
    response = await human.get(f"/processes/{worker.settings.process_id}/mail-ingestion")
    assert response.status_code == 200, response.text
    return response.json()


async def reset_retry():
    async with session_factory() as session:
        await session.execute(
            update(MailMessage).values(
                retry_at=None,
                lease_until=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        await session.commit()


async def test_local_imap_worker_api_postgres_all_outcomes_and_manual_intact(pipeline):
    server, worker, human = pipeline
    pid = worker.settings.process_id
    # A human's pending document must not be included in the automatic run.
    manual = await human.post(
        f"/processes/{pid}/files", files={"file": ("manual.pdf", pdf_bytes("Holder: manual"))}
    )
    assert manual.status_code == 201, manual.text
    old = server.deliver(synthetic_mail([("old.pdf", pdf_bytes("Holder: old"), "pdf")]))
    await worker.initialize()
    new = server.deliver(
        synthetic_mail(
            [
                ("pay.pdf", pdf_bytes("Holder: open"), "pdf"),
                ("deny.pdf", pdf_bytes("Holder: paid"), "octet-stream"),
                ("review.pdf", pdf_bytes("Holder: review"), "pdf"),
            ]
        ),
        seen=True,
    )
    before = dict(server.messages), dict(server.flags)
    await worker.cycle()
    result = await overview(worker, human)
    assert [m["uid"] for m in result["messages"]] == [new]
    assert result["messages"][0]["state"] == "completed", result
    parts = result["messages"][0]["attachments"]
    assert len(parts) == 3 and all(p["decision_id"] for p in parts)
    instances = (await human.get(f"/processes/{pid}/instances")).json()
    assert {i["decision"] for i in instances if i["id"] != manual.json()["instance_id"]} == {
        "PAGAR",
        "NO_PAGAR",
        "ESCALAR",
    }
    assert (
        next(i for i in instances if i["id"] == manual.json()["instance_id"])["status"] == "PENDING"
    )
    assert len({p["execution_id"] for p in parts}) == 1
    assert result["account"]["initial_uid"] == old + 1 and result["account"]["last_poll_at"]
    assert before == (server.messages, server.flags) and not server.forbidden
    await worker.cycle()
    assert (await overview(worker, human))["messages"] == result["messages"]


async def test_arrival_during_initialization_and_no_pdf_recorded(pipeline):
    server, worker, human = pipeline
    server.on_examine = lambda: server.deliver(synthetic_mail())
    await worker.initialize()
    await worker.cycle()
    result = await overview(worker, human)
    assert result["messages"][0]["state"] == "ignored"
    assert result["messages"][0]["uid"] == result["account"]["initial_uid"]


async def test_partial_invalid_pdf_and_content_duplicate(pipeline):
    server, worker, human = pipeline
    pdf = pdf_bytes("Holder: open")
    await worker.initialize()
    server.deliver(synthetic_mail([("good.pdf", pdf, "pdf"), ("fake.pdf", b"not pdf", "pdf")]))
    await worker.cycle()
    result = await overview(worker, human)
    assert result["messages"][0]["state"] == "partial"
    original = result["messages"][0]["attachments"][0]
    server.deliver(synthetic_mail([("renamed.pdf", pdf, "pdf")]))
    await worker.cycle()
    result = await overview(worker, human)
    duplicate = result["messages"][0]["attachments"][0]
    assert duplicate["state"] == "duplicate"
    assert duplicate["instance_id"] == original["instance_id"]
    assert duplicate["decision_id"] == original["decision_id"]


@pytest.mark.parametrize("lost_path", ["/manifest", "/attachments/", "/finish"])
async def test_server_committed_but_client_lost_response(pipeline, lost_path):
    server, worker, human = pipeline
    await worker.initialize()
    server.deliver(synthetic_mail([("a.pdf", pdf_bytes("Holder: open"), "pdf")]))
    request = worker.request
    lost = False

    async def lose_once(method, path="", **kwargs):
        nonlocal lost
        result = await request(method, path, **kwargs)
        if not lost and lost_path in path:
            lost = True
            raise httpx.ReadTimeout("Synthetic lost response")
        return result

    worker.request = lose_once
    await worker.cycle()
    await reset_retry()
    await worker.cycle()
    result = await overview(worker, human)
    assert lost and result["messages"][0]["state"] == "completed", result
    part = result["messages"][0]["attachments"][0]
    instance = (await human.get(f"/instances/{part['instance_id']}")).json()
    assert len(instance["decisions"]) == 1
    async with session_factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Instance)
                .where(Instance.process_id == worker.settings.process_id)
            )
            == 1
        )


async def test_crash_after_discovery_and_competing_claims(pipeline):
    server, worker, human = pipeline
    await worker.initialize()
    server.deliver(synthetic_mail([("a.pdf", pdf_bytes("Holder: open"), "pdf")]))
    state = await worker.state()
    await worker.request(
        "POST",
        "/discover",
        json={
            "uidvalidity": server.uidvalidity,
            "expected_cursor": state["next_uid"],
            "through_uid": 1,
            "uids": [1],
        },
    )
    first, second = await asyncio.gather(
        worker.request("POST", "/claim"),
        worker.request("POST", "/claim"),
    )
    assert sum(v is not None for v in (first, second)) == 1
    await reset_retry()
    await Worker(worker.settings, worker.api).cycle()
    result = await overview(worker, human)
    assert result["messages"][0]["state"] == "completed"


async def test_uidvalidity_change_halts_without_importing(pipeline):
    server, worker, human = pipeline
    await worker.initialize()
    server.uidvalidity += 1
    server.deliver(synthetic_mail([("a.pdf", pdf_bytes("Holder: open"), "pdf")]))
    with pytest.raises(RuntimeError, match="UIDVALIDITY"):
        await worker.cycle()
    result = await overview(worker, human)
    assert result["account"]["state"] == "halted" and result["messages"] == []
    with pytest.raises(RuntimeError):
        await worker.initialize()


async def test_manual_content_conflict_and_scoped_credential(pipeline):
    server, worker, human = pipeline
    pid = worker.settings.process_id
    pdf = pdf_bytes("Holder: open")
    manual = await human.post(f"/processes/{pid}/files", files={"file": ("manual.pdf", pdf)})
    await worker.initialize()
    server.deliver(synthetic_mail([("a.pdf", pdf, "pdf")]))
    await worker.cycle()
    result = await overview(worker, human)
    part = result["messages"][0]["attachments"][0]
    assert part["state"] == "duplicate" and part["error"] == "manual_pending_conflict"
    assert (await human.get(f"/instances/{manual.json()['instance_id']}")).json()[
        "status"
    ] == "PENDING"
    assert (await worker.api.get(f"/mail-ingestion/{pid + 100000}")).status_code == 403
    assert (
        await worker.api.post(f"/processes/{pid}/run", headers=dict(human.headers))
    ).status_code == 401
    assert (await human.get(f"/mail-ingestion/{pid}")).status_code == 401


async def test_target_selection_validation_idempotency_and_others(pipeline):
    _, worker, human = pipeline
    pid = worker.settings.process_id
    first = (
        await human.post(
            f"/processes/{pid}/files", files={"file": ("one.pdf", pdf_bytes("Holder: open"))}
        )
    ).json()
    second = (
        await human.post(
            f"/processes/{pid}/files", files={"file": ("two.pdf", pdf_bytes("Holder: other"))}
        )
    ).json()
    async with session_factory() as session:
        rule = Rule(
            process_id=pid,
            text="Population context",
            type="prohibition",
            decision="NO_PAGAR",
            code="def evaluate(instance, sources, others):\n"
            "    found = any(i['holder'] == 'other' for i in others)\n"
            "    return {'fires': found, 'reason': 'OTHER_FOUND'}",
            hash="others",
            status="active",
            report={"valid": True},
        )
        session.add(rule)
        await rows.publish_fixture(session, pid)
    endpoint = f"/processes/{pid}/run"
    assert (await human.post(endpoint, json={"instance_ids": []})).status_code == 422
    assert (
        await human.post(endpoint, json={"instance_ids": [first["instance_id"], 999999]})
    ).status_code == 409
    body = {"instance_ids": [first["instance_id"]], "idempotency_key": "selection"}
    response = await human.post(endpoint, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["by_decision"] == {"NO_PAGAR": 1}
    assert (await human.post(endpoint, json=body)).json() == response.json()
    body["instance_ids"] = [second["instance_id"]]
    assert (await human.post(endpoint, json=body)).status_code == 409
    assert (await human.get(f"/instances/{second['instance_id']}")).json()["status"] == "PENDING"


async def test_gathering_assignment_exclusive_and_validated(pipeline):
    _, worker, human = pipeline
    pid = worker.settings.process_id
    endpoint = f"/processes/{pid}/gathering"
    assert (await human.get(endpoint)).json() == {"email": "migration-test@j-aautomation.com"}
    assert (await human.put(endpoint, json={"email": "other@example.invalid"})).status_code == 422
    async with session_factory() as session:
        other = await rows.process(session, "Other mail process " + uuid.uuid4().hex)
        await session.commit()
    response = await human.put(
        f"/processes/{other.id}/gathering", json={"email": "migration-test@j-aautomation.com"}
    )
    assert response.status_code == 409
    await worker.initialize()
    assert (await human.put(endpoint, json={"email": None})).status_code == 409


async def test_missing_persisted_cursor_never_connects_or_reinitializes(pipeline):
    server, worker, _ = pipeline
    await worker.initialize()
    async with session_factory() as session:
        await session.execute(
            update(MailAccount)
            .where(MailAccount.process_id == worker.settings.process_id)
            .values(next_uid=None)
        )
        await session.commit()
    count = len(server.commands)
    with pytest.raises(RuntimeError, match="cursor"):
        await worker.cycle()
    assert len(server.commands) == count


async def test_invalid_credentials_halt_without_authentication_loop(pipeline):
    server, worker, human = pipeline
    await worker.initialize()
    server.refuse_login = True
    with pytest.raises(RuntimeError, match="authentication"):
        await worker.cycle()
    count = server.commands.count("LOGIN")
    with pytest.raises(RuntimeError):
        await worker.cycle()
    assert server.commands.count("LOGIN") == count
    assert (await overview(worker, human))["account"]["error"] == "invalid_credentials"


async def test_missing_erp_uses_normal_engine_and_is_never_automatically_redecided(pipeline):
    server, worker, human = pipeline
    pid = worker.settings.process_id
    async with session_factory() as session:
        session.add(
            Rule(
                process_id=pid,
                text="ERP check",
                type="prohibition",
                decision="NO_PAGAR",
                code="def evaluate(instance, sources, others):\n"
                "    return {'fires': bool(sources['erp']), 'reason': 'ERP_CHECK'}",
                hash="erp",
                status="active",
                report={"valid": True},
            )
        )
        await rows.publish_fixture(session, pid)
    await worker.initialize()
    server.deliver(synthetic_mail([("erp.pdf", pdf_bytes("Holder: open"), "pdf")]))
    await worker.cycle()
    message = (await overview(worker, human))["messages"][0]
    assert message["state"] == "completed"
    part = message["attachments"][0]
    detail = (await human.get(f"/instances/{part['instance_id']}")).json()
    assert detail["decision"] == "ESCALAR" and "SOURCE_UNAVAILABLE" in detail["reason"]
    from app.features.sources.model import Source

    async with session_factory() as session:
        session.add(Source(process_id=pid, name="erp", origin="local-test", rows=[]))
        await session.commit()
    await worker.cycle()
    assert (await human.get(f"/instances/{part['instance_id']}")).json()["decisions"] == detail[
        "decisions"
    ]


async def test_infrastructure_failure_creates_no_fake_decision_and_recovers(pipeline, monkeypatch):
    from app.features.versions import execution

    server, worker, human = pipeline
    await worker.initialize()
    server.deliver(synthetic_mail([("a.pdf", pdf_bytes("Holder: open"), "pdf")]))
    real = execution.evaluate

    async def unavailable(*args, **kwargs):
        raise OSError("Synthetic infrastructure failure")

    monkeypatch.setattr(execution, "evaluate", unavailable)
    await worker.cycle()
    message = (await overview(worker, human))["messages"][0]
    assert message["state"] == "retry_wait"
    part = message["attachments"][0]
    assert part["decision_id"] is None
    detail = (await human.get(f"/instances/{part['instance_id']}")).json()
    assert detail["status"] == "PENDING" and detail["decisions"] == []
    monkeypatch.setattr(execution, "evaluate", real)
    await reset_retry()
    await worker.cycle()
    assert (await overview(worker, human))["messages"][0]["state"] == "completed"


async def test_two_workers_and_foreign_process_id_have_no_extra_effects(pipeline):
    server, worker, human = pipeline
    pid = worker.settings.process_id
    await worker.initialize()
    server.deliver(synthetic_mail([("a.pdf", pdf_bytes("Holder: open"), "pdf")]))
    results = await asyncio.gather(
        worker.cycle(), Worker(worker.settings, worker.api).cycle(), return_exceptions=True
    )
    assert all(result is None or isinstance(result, httpx.HTTPStatusError) for result in results)
    message = (await overview(worker, human))["messages"][0]
    assert message["state"] == "completed"
    part = message["attachments"][0]
    detail = (await human.get(f"/instances/{part['instance_id']}")).json()
    assert len(detail["decisions"]) == 1
    async with session_factory() as session:
        other = await rows.process(session, "Foreign " + uuid.uuid4().hex)
        session.add(Instance(process_id=other.id, name="foreign", file_hash=part["file_hash"]))
        await session.commit()
        foreign = await session.scalar(select(Instance.id).where(Instance.process_id == other.id))
    response = await human.post(f"/processes/{pid}/run", json={"instance_ids": [foreign]})
    assert response.status_code == 409


async def test_same_content_twice_in_one_batch_retains_both_result_links(pipeline):
    server, worker, human = pipeline
    pdf = pdf_bytes("Holder: open")
    await worker.initialize()
    server.deliver(synthetic_mail([("one.pdf", pdf, "pdf"), ("two.pdf", pdf, "pdf")]))
    await worker.cycle()
    parts = (await overview(worker, human))["messages"][0]["attachments"]
    assert [part["state"] for part in parts] == ["completed", "duplicate"]
    assert parts[0]["decision_id"] == parts[1]["decision_id"] is not None
    assert parts[0]["execution_id"] == parts[1]["execution_id"] is not None


async def test_committed_import_finishes_independently_of_mailbox_availability(pipeline):
    server, worker, human = pipeline
    await worker.initialize()
    server.deliver(synthetic_mail([("a.pdf", pdf_bytes("Holder: open"), "pdf")]))
    request = worker.request
    lost = False

    async def lose_import_response(method, path="", **kwargs):
        nonlocal lost
        result = await request(method, path, **kwargs)
        if "/attachments/" in path and not lost:
            lost = True
            raise httpx.ReadTimeout("Synthetic lost import response")
        return result

    worker.request = lose_import_response
    await worker.cycle()
    assert (await overview(worker, human))["messages"][0]["attachments"][0]["state"] == "imported"
    await reset_retry()
    server.refuse_login = True
    with pytest.raises(RuntimeError, match="authentication"):
        await worker.cycle()
    assert (await overview(worker, human))["messages"][0]["state"] == "completed"


async def test_administrative_bearer_and_mail_bearer_keep_separate_scopes(pipeline, monkeypatch):
    from pydantic import SecretStr

    from app.core.config import settings as core_settings

    _, worker, human = pipeline
    monkeypatch.setattr(core_settings, "api_token", SecretStr("synthetic-admin-test-token"))
    administrative = {"Authorization": "Bearer synthetic-admin-test-token"}
    assert (await human.get("/health", headers=administrative)).status_code == 200
    assert (await worker.api.get("/db/tables")).status_code == 401
    assert (await human.get(worker.root, headers=administrative)).status_code == 401
    assert (await worker.api.get(worker.root)).status_code == 200


async def test_imap_disconnect_persists_bounded_retry_and_recovers(pipeline, monkeypatch):
    import imaplib

    from app.features.mail_ingestion.imap import ReadOnlyIMAP

    _, worker, human = pipeline
    await worker.initialize()
    original = ReadOnlyIMAP.login

    def disconnected(*args):
        raise imaplib.IMAP4.abort("Synthetic dropped connection")

    monkeypatch.setattr(ReadOnlyIMAP, "login", disconnected)
    await worker.cycle()
    state = (await overview(worker, human))["account"]
    assert state["state"] == "active" and state["error"] == "imap_unavailable"
    retry_at = state["retry_at"]
    assert retry_at
    await worker.cycle()
    assert (await overview(worker, human))["account"]["retry_at"] == retry_at
    async with session_factory() as session:
        assert (
            await session.scalar(
                select(MailAccount.failures).where(
                    MailAccount.process_id == worker.settings.process_id
                )
            )
            == 1
        )
    monkeypatch.setattr(ReadOnlyIMAP, "login", original)
    async with session_factory() as session:
        await session.execute(update(MailAccount).values(retry_at=None))
        await session.commit()
    await worker.cycle()
    state = (await overview(worker, human))["account"]
    assert state["retry_at"] is None and state["error"] is None
