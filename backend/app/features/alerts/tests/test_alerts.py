"""Stale decision alerts (ADR 0026): a source change or a new rule that would flip a past
decision flags it to the manager; the decision itself is never touched.

Same setup as `decisions/tests/test_api.py`: FA-1016 is NO_PAGAR (its order PO-2026-0474 is
PAGADA in the ERP), factura_1217 PAGAR, FA-5044 ESCALAR (IBAN mismatch). Sandbox faked.
"""

import pytest
from sqlalchemy import select

from app.core.database import session_factory
from app.core.events import Event
from app.features.agents import sandbox
from app.features.alerts import service as alerts
from app.features.decisions.tests.test_api import ENTRIES, RULES_V3, client, create_process
from app.features.rules.model import Rule
from app.features.sources.model import Source
from tests.support.fakes import dataset_runner
from tests.support.rows import publish_fixture
from tests.support.users import anonymous

RULES = {
    **{name: fn for name, (_, fn) in RULES_V3.items()},
    # A norm v4 stand-in: every invoice of this supplier goes to a person.
    "supplier_under_review": lambda i, s, o: i["nif"] == "B96233419",
}


@pytest.fixture(autouse=True)
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(RULES))


def erp(**status: str) -> list[dict]:
    """The ERP entries with the status of some orders changed."""
    return [{**e, "status": status.get(e["purchase_order"], e["status"])} for e in ENTRIES]


async def load_erp(process_id: int, rows: list[dict]) -> list[int]:
    """A new ERP snapshot, then what a sync does after committing it."""
    async with session_factory() as session:
        session.add(Source(process_id=process_id, name="erp", origin="erp:t2", rows=rows))
        await session.commit()
    return await alerts.after_source_load(process_id, ["erp"])


async def decided(api, process_id: int) -> dict[str, int]:
    await api.post(f"/processes/{process_id}/run")
    return {
        i["name"]: i["id"] for i in (await api.get(f"/processes/{process_id}/instances")).json()
    }


async def test_an_erp_change_behind_a_no_pagar_raises_one_alert() -> None:
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        ids = await decided(api, process_id)

        # PO-0474 is unpaid after all (FA-1016 NO_PAGAR -> PAGAR); PO-0008 is now paid, by
        # us: factura_1217's PAGAR was right, so no alert for it.
        created = await load_erp(
            process_id, erp(**{"PO-2026-0474": "PENDIENTE", "PO-2026-0008": "PAGADA"})
        )
        assert len(created) == 1

        [alert] = (await api.get(f"/processes/{process_id}/alerts?status=open")).json()
        assert (alert["name"], alert["before"], alert["after"], alert["status"]) == (
            "FA-1016_papelería.pdf",
            "NO_PAGAR",
            "PAGAR",
            "open",
        )
        assert alert["evidence"] == {
            "before": {"author": "engine", "reason": "order_already_paid"},
            "after": {"author": "engine", "reason": ""},
        }
        trigger = alert["trigger"]
        assert trigger["kind"] == "source_sync"
        assert [(s["name"], s["rows_removed"], s["rows_added"]) for s in trigger["sources"]] == [
            ("erp", 2, 2)
        ]
        assert trigger["rows"] == {
            "before": [{"purchase_order": "PO-2026-0474", "status": "PAGADA"}],
            "after": [{"purchase_order": "PO-2026-0474", "status": "PENDIENTE"}],
        }

        # The decision itself is exactly as it was.
        detail = (await api.get(f"/instances/{ids['FA-1016_papelería.pdf']}")).json()
        assert [(d["author"], d["decision"]) for d in detail["decisions"]] == [
            ("engine", "NO_PAGAR")
        ]
        assert detail["decisions"][0]["id"] == alert["decision_id"]

        metrics = (await api.get(f"/processes/{process_id}/metrics/execution")).json()
        assert metrics["open_alerts"] == 1

    async with session_factory() as session:
        span = await session.scalar(
            select(Event).where(
                Event.process_id == process_id, Event.step == "detect_stale_decisions"
            )
        )
    assert span.data["trigger"]["kind"] == "source_sync"
    assert (span.data["instances"], span.data["alerts_created"]) == (3, 1)


async def test_a_sync_with_no_relevant_change_raises_nothing() -> None:
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        await decided(api, process_id)

        assert await load_erp(process_id, ENTRIES) == []  # nothing changed
        other = {"purchase_order": "PO-2026-0999", "status": "PAGADA"}
        assert await load_erp(process_id, [*ENTRIES, other]) == []  # nobody's order
        assert (await api.get(f"/processes/{process_id}/alerts")).json() == []


async def test_a_new_rule_that_flips_past_decisions_raises_alerts() -> None:
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        await decided(api, process_id)

        async with session_factory() as session:
            rule = Rule(
                process_id=process_id,
                text="supplier_under_review",
                type="prohibition",
                decision="ESCALAR",
                code="supplier_under_review",
                hash="hash-v4",
                status="active",
                report={"valid": True},
            )
            session.add(rule)
            await session.flush()
            version = await publish_fixture(session, process_id)
        created = await alerts.after_publish(process_id, version.id)

        listed = (await api.get(f"/processes/{process_id}/alerts")).json()
        assert sorted(a["id"] for a in listed) == sorted(created)
        # A new rule can also say a payment was wrong: PAGAR is flagged here.
        assert sorted((a["name"], a["before"], a["after"]) for a in listed) == [
            ("FA-1016_papelería.pdf", "NO_PAGAR", "ESCALAR"),
            ("factura_1217.pdf", "PAGAR", "ESCALAR"),
        ]
        assert {a["trigger"]["kind"] for a in listed} == {"rule_change"}
        assert listed[0]["trigger"]["added_rule_ids"] == [rule.id]
        assert listed[0]["evidence"]["after"]["reason"] == "supplier_under_review"


async def test_ack_records_who_and_the_manager_then_acts() -> None:
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        ids = await decided(api, process_id)
        [alert_id] = await load_erp(process_id, erp(**{"PO-2026-0474": "PENDIENTE"}))

        assert (await anonymous("POST", f"/alerts/{alert_id}/ack")).status_code == 401  # who?
        r = await api.post(
            f"/alerts/{alert_id}/ack", json={"note": "calling the supplier"}, headers=headers
        )
        assert r.status_code == 200, r.text
        acked = r.json()
        assert (acked["status"], acked["acknowledged_by"], acked["note"]) == (
            "acknowledged",
            "Ana",
            "calling the supplier",
        )
        assert acked["acknowledged_at"] is not None
        assert (await api.post(f"/alerts/{alert_id}/ack", headers=headers)).status_code == 409
        assert (await api.get(f"/processes/{process_id}/alerts?status=open")).json() == []

        # She acts through the existing endpoint: the later decision resolves the alert.
        await api.post(
            f"/instances/{ids['FA-1016_papelería.pdf']}/resolve",
            json={"decision": "PAGAR", "reason": "ERP corrected: order unpaid"},
            headers=headers,
        )
        [alert] = (await api.get(f"/processes/{process_id}/alerts?status=resolved")).json()
        assert alert["resolved_by_decision_id"] > alert["decision_id"]

    async with session_factory() as session:
        span = await session.scalar(
            select(Event).where(Event.process_id == process_id, Event.step == "ack_alert")
        )
    assert span.data["author"] == "Ana" and span.instance_id == ids["FA-1016_papelería.pdf"]


async def test_an_alert_is_never_duplicated() -> None:
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        await decided(api, process_id)
        changed = erp(**{"PO-2026-0474": "PENDIENTE"})

        assert len(await load_erp(process_id, changed)) == 1
        # The same change arrives again (an ERP flapping back and forth), and nothing new.
        assert await load_erp(process_id, ENTRIES) == []
        assert await load_erp(process_id, changed) == []
        assert len((await api.get(f"/processes/{process_id}/alerts")).json()) == 1
