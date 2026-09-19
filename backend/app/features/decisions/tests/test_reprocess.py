"""Re-deciding what was already decided (a source resync, a Sunday datum change), and the
delivery of one batch: its export and the check of the file.

Same setup as `test_api.py`: instances, sources and rules inserted directly, sandbox faked.
"""

import json
import unicodedata

import pytest

from app.core.database import session_factory
from app.features.agents import sandbox
from app.features.decisions import outcomes_file
from app.features.decisions import service as decisions
from app.features.decisions.tests.test_api import ENTRIES, FAKE_SANDBOX, client, create_process
from app.features.sources.model import Source


@pytest.fixture(autouse=True)
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)


async def resync_erp(process_id: int) -> None:
    """A new ERP snapshot: the order of factura_1217 has been paid since."""
    rows = [
        {**e, "status": "PAGADA"} if e["purchase_order"] == "PO-2026-0008" else e for e in ENTRIES
    ]
    async with session_factory() as session:
        session.add(Source(process_id=process_id, name="erp", origin="erp:t2", rows=rows))
        await session.commit()


async def test_reprocess_appends_what_changed_and_leaves_people_alone() -> None:
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        await api.post(f"/processes/{process_id}/run")
        listed = (await api.get(f"/processes/{process_id}/instances")).json()
        instances = {i["name"]: i["id"] for i in listed}
        # A person paid the escalated one; the engine will still say ESCALAR.
        await api.post(
            f"/instances/{instances['FA-5044_mensajería2.pdf']}/resolve",
            json={"decision": "PAGAR", "reason": "IBAN confirmed by phone"},
            headers=headers,
        )
        await resync_erp(process_id)

        # A dry run tells the same and writes nothing.
        preview = (await api.post(f"/processes/{process_id}/reprocess?dry_run=true")).json()
        r = await api.post(f"/processes/{process_id}/reprocess")
        assert r.status_code == 200, r.text
        out = r.json()
        assert preview == out
        assert out["unchanged"] == 1  # FA-1016, its order was already paid
        assert [(c["name"], c["before"], c["after"]) for c in out["changes"]] == [
            ("factura_1217.pdf", "PAGAR", "NO_PAGAR")
        ]
        [conflict] = out["conflicts"]
        assert (conflict["name"], conflict["before"], conflict["after"]) == (
            "FA-5044_mensajería2.pdf",
            "PAGAR",
            "ESCALAR",
        )
        assert conflict["previous_author"] == "Ana"

        # The old decision stays; the new one is appended and is what gets exported.
        detail = (await api.get(f"/instances/{instances['factura_1217.pdf']}")).json()
        assert [(d["author"], d["decision"]) for d in detail["decisions"]] == [
            ("engine", "PAGAR"),
            ("engine", "NO_PAGAR"),
        ]
        assert [e["data"].get("reprocess") for e in detail["events"]] == [None, True]
        # The person's decision is still the last word on hers.
        detail = (await api.get(f"/instances/{instances['FA-5044_mensajería2.pdf']}")).json()
        assert [d["author"] for d in detail["decisions"]] == ["engine", "Ana"]
        # The unread one was never decided, so it is not re-decided either.
        detail = (await api.get(f"/instances/{instances['FA-9999_sin_leer.pdf']}")).json()
        assert detail["status"] == "PENDING" and detail["decisions"] == []

        # Nothing changed since: a second reprocess writes nothing.
        r = await api.post(f"/processes/{process_id}/reprocess")
        assert r.json()["changes"] == [] and r.json()["unchanged"] == 2


async def test_reprocess_and_export_a_named_batch() -> None:
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        await api.post(f"/processes/{process_id}/run")
        await resync_erp(process_id)

        r = await api.post(
            f"/processes/{process_id}/reprocess", json={"names": ["FA-1016_papelería.pdf"]}
        )
        assert r.json() == {"unchanged": 1, "changes": [], "conflicts": []}

    # FA-9999 is still PENDING: the whole process cannot be exported, one batch can.
    batch = {"factura_1217.pdf", "FA-1016_papelería.pdf"}
    async with session_factory() as session:
        body, duplicates = await decisions.export(session, process_id, batch)
    assert duplicates == []
    assert [
        {k: v for k, v in json.loads(line).items() if k != "reason"} for line in body.splitlines()
    ] == [
        {"file_id": "factura_1217.pdf", "result": "PAGAR"},  # not reprocessed
        {"file_id": "FA-1016_papelería.pdf", "result": "NO_PAGAR"},
    ]
    assert outcomes_file.problems(body, batch) == []


def test_the_delivery_check() -> None:
    files = {"a.pdf", "FA-1016_papelería.pdf", "c.pdf"}
    nfd = unicodedata.normalize("NFD", "FA-1016_papelería.pdf")  # as macOS may spell it
    text = "\n".join(
        [
            '{"file_id": "a.pdf", "result": "PAGAR"}',
            '{"file_id": "a.pdf", "result": "PAGAR"}',
            '{"file_id": "x.pdf", "result": "REVIEW"}',
            json.dumps({"file_id": nfd, "result": "ESCALAR"}),
            "not json",
        ]
    )
    assert outcomes_file.problems(text, files) == [
        "line 3: result 'REVIEW' is not one of ['ESCALAR', 'NO_PAGAR', 'PAGAR']",
        "line 5: not JSON (Expecting value)",
        "a.pdf: 2 lines",
        f"{nfd}: not a file of the batch (same as 'FA-1016_papelería.pdf' once normalised)",
        "x.pdf: not a file of the batch",
        "FA-1016_papelería.pdf: missing",
        "c.pdf: missing",
    ]
    ok = "\n".join(json.dumps({"file_id": f, "result": "PAGAR"}) for f in sorted(files))
    assert outcomes_file.problems(ok, files) == []
