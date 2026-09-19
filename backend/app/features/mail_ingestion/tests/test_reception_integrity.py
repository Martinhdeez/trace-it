"""Reception receipts and retries preserve ownership, history and completed decisions."""

from app.features.ingestion.tests.conftest import pdf_bytes
from app.features.ingestion.tests.conftest import settings as settings
from tests.support.mailbox import synthetic_mail
from tests.support.users import manager

from .test_pipeline import overview
from .test_pipeline import pipeline as pipeline
from .test_protocol import local_mail as local_mail


async def test_activity_receipts_are_per_user_monotonic_and_not_future(pipeline):
    server, worker, human = pipeline
    root = f"/processes/{worker.settings.process_id}/mail-ingestion"
    await worker.initialize()
    first_user = dict(human.headers)
    response = await human.post(root + "/activity/read", json={"through_id": 0})
    assert response.status_code == 200
    server.deliver(synthetic_mail([("open.pdf", pdf_bytes("Holder: open"), "pdf")]))
    await worker.cycle()
    feed = (await human.get(root + "/activity")).json()
    assert feed["initialized"] and feed["unread"] > 0
    latest = feed["latest_id"]
    assert latest > 0
    future = await human.post(root + "/activity/read", json={"through_id": latest + 1})
    assert future.status_code == 409
    await manager(human, "Second reception reader")
    second = (await human.get(root + "/activity")).json()
    assert not second["initialized"] and second["unread"] == 0
    await human.post(root + "/activity/read", json={"through_id": latest})
    human.headers.update(first_user)
    assert (await human.get(root + "/activity")).json()["unread"] == feed["unread"]
    await human.post(root + "/activity/read", json={"through_id": latest})
    older = await human.post(root + "/activity/read", json={"through_id": 0})
    assert older.json()["through_id"] == latest
    assert older.json()["unread"] == 0


async def test_partial_retry_preserves_completed_part_and_rejects_stale_request(pipeline):
    server, worker, human = pipeline
    root = f"/processes/{worker.settings.process_id}/mail-ingestion"
    await worker.initialize()
    server.deliver(
        synthetic_mail(
            [("good.pdf", pdf_bytes("Holder: open"), "pdf"), ("bad.pdf", b"broken", "pdf")]
        )
    )
    await worker.cycle()
    result = await overview(worker, human)
    account = result["account"]
    message = result["messages"][0]
    good, bad = message["attachments"]
    assert good["decision_id"] and bad["can_retry"]
    payload = {"expected_attempts": message["attempts"]}
    denied = await human.post(root + f"/attachments/{good['id']}/retry", json=payload)
    assert denied.status_code == 409
    url = root + f"/attachments/{bad['id']}/retry"
    retry = await human.post(url, json=payload)
    assert retry.status_code == 200, retry.text
    assert (await human.post(url, json=payload)).status_code == 409
    await worker.cycle()
    after = await overview(worker, human)
    next_message = after["messages"][0]
    assert next_message["attachments"][0] == good
    assert next_message["attempts"] == message["attempts"] + 1
    for key in ("initial_uid", "next_uid", "uidvalidity"):
        assert after["account"][key] == account[key]
    history = (await human.get(root + f"/messages/{message['id']}/history")).json()
    retries = [item for item in history["activities"] if item["kind"] == "retry_requested"]
    assert len(retries) == 1
    assert retries[0]["data"]["previous_error"] == "invalid_pdf"


async def test_heartbeat_requires_worker_identity_and_reports_stop(pipeline):
    _, worker, human = pipeline
    await worker.initialize()
    denied = await human.post(worker.root + "/heartbeat", json={"phase": "waiting"})
    assert denied.status_code in (401, 403)
    live = await worker.request("POST", "/heartbeat", json={"phase": "processing"})
    assert live["heartbeat_at"] and live["worker_phase"] == "processing"
    stopped = await worker.request("POST", "/heartbeat", json={"phase": "stopped"})
    assert stopped["worker_phase"] == "stopped"
