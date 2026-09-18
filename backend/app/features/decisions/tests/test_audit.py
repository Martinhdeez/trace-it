"""A rule change is checked against every decision already taken, before it is adopted.

Same setup as `test_api.py`: instances, sources and compiled rules inserted directly, the
sandbox faked.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import session_factory
from app.features.agents import sandbox
from app.features.decisions.tests.test_api import RULES_V3, create_process
from app.features.rules.model import Rule
from app.main import app

# A rule nobody has activated yet: it escalates any invoice from this supplier. It stays
# out of RULES_V3 so `seed` does not seed it as active.
NEW_RULE = "watched_supplier"
EXTRA = {NEW_RULE: ("ESCALAR", lambda i, s, o: i["nif"] == "B96233419")}


def fake_sandbox(code: str, instance: dict, sources: dict, others: list) -> dict:
    fires = {**RULES_V3, **EXTRA}[code][1](instance, sources, others)
    return {"fires": fires, "reason": code if fires else ""}


def fake_batch(code: str, cases: list) -> list:
    return [fake_sandbox(code, *case) for case in cases]


async def create_draft(process_id: int) -> int:
    async with session_factory() as session:
        rule = Rule(
            process_id=process_id,
            text=NEW_RULE,
            type="prohibition",
            decision="ESCALAR",
            code_a=NEW_RULE,
            code_b=NEW_RULE,
            hash=f"hash-{NEW_RULE}",
            status="draft",
            report={"valid": True},
        )
        session.add(rule)
        await session.commit()
        return rule.id


async def prepare(api: AsyncClient) -> tuple[int, dict[str, str]]:
    """A process with its invoices already decided by the engine."""
    process_id, headers = await create_process(api, uuid.uuid4().hex[:8], "manager")
    await api.post(f"/processes/{process_id}/run")
    return process_id, headers


async def test_impact_is_visible_before_activating(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, _ = await prepare(api)
        rule_id = await create_draft(process_id)

        r = await api.get(f"/rules/{rule_id}/impact")
        assert r.status_code == 200, r.text
        impact = r.json()

        # Both invoices from that supplier move: ESCALAR outranks what they concluded
        # before. FA-5044 is another supplier and was escalated by the IBAN rule anyway.
        assert [(c["name"], c["before"], c["after"]) for c in impact["changes"]] == [
            ("factura_1217.pdf", "PAGAR", "ESCALAR"),
            ("FA-1016_papelería.pdf", "NO_PAGAR", "ESCALAR"),
        ]
        assert impact["conflicts"] == []
        assert impact["unchanged"] == 1

        # Looking does not change anything.
        assert (await api.get(f"/rules/{rule_id}")).json()["status"] == "draft"
        assert (await api.get(f"/processes/{process_id}/findings")).json() == []


async def test_activating_records_findings_and_leaves_the_past_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, headers = await prepare(api)
        rule_id = await create_draft(process_id)

        r = await api.post(f"/rules/{rule_id}/activate", headers=headers)
        assert r.status_code == 200, r.text

        findings = (await api.get(f"/processes/{process_id}/findings")).json()
        assert [f["detail"].split(":")[0] for f in findings] == [
            "PAGAR -> ESCALAR",
            "NO_PAGAR -> ESCALAR",
        ]
        assert {f["rule_id"] for f in findings} == {rule_id}

        # The decision itself is untouched: the finding is a notice, not a correction.
        instances = (await api.get(f"/processes/{process_id}/instances")).json()
        affected = next(i for i in instances if i["name"] == "factura_1217.pdf")
        assert affected["decision"] == "PAGAR"
        detail = (await api.get(f"/instances/{affected['id']}")).json()
        assert len(detail["decisions"]) == 1


async def test_a_human_decision_blocks_the_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rules do not overrule a person, and a person does not silently veto a rule."""
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, headers = await prepare(api)
        instances = (await api.get(f"/processes/{process_id}/instances")).json()
        affected = next(i for i in instances if i["name"] == "factura_1217.pdf")
        await api.post(
            f"/instances/{affected['id']}/resolve",
            json={"decision": "PAGAR", "reason": "Checked with the supplier by phone"},
            headers=headers,
        )
        rule_id = await create_draft(process_id)

        r = await api.get(f"/rules/{rule_id}/impact")
        assert [c["name"] for c in r.json()["conflicts"]] == ["factura_1217.pdf"]
        # The other invoice would still change; the conflict is what blocks the rule.
        assert [c["name"] for c in r.json()["changes"]] == ["FA-1016_papelería.pdf"]

        r = await api.post(f"/rules/{rule_id}/activate", headers=headers)
        assert r.status_code == 409, r.text
        assert "factura_1217.pdf" in r.json()["message"]
        assert (await api.get(f"/rules/{rule_id}")).json()["status"] == "draft"
        assert (await api.get(f"/processes/{process_id}/findings")).json() == []


async def test_retiring_is_checked_like_activating(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, headers = await prepare(api)
        rules = (await api.get(f"/processes/{process_id}/rules")).json()
        already_paid = next(r for r in rules if r["text"] == "order_already_paid")

        # Without it, the invoice the ERP already paid would be paid again.
        r = await api.get(f"/rules/{already_paid['id']}/impact")
        assert [(c["name"], c["before"], c["after"]) for c in r.json()["changes"]] == [
            ("FA-1016_papelería.pdf", "NO_PAGAR", "PAGAR")
        ]

        r = await api.post(f"/rules/{already_paid['id']}/retire", headers=headers)
        assert r.status_code == 200, r.text
        findings = (await api.get(f"/processes/{process_id}/findings")).json()
        assert findings[0]["detail"].startswith("NO_PAGAR -> PAGAR")


async def test_an_escalated_case_gives_no_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    """An instance sitting in the human queue was never acted on, so nothing went wrong."""
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, headers = await prepare(api)
        rules = (await api.get(f"/processes/{process_id}/rules")).json()
        iban = next(r for r in rules if r["text"] == "iban_mismatch")

        # Retiring it turns the escalated invoice into PAGAR: a change, but not a finding.
        r = await api.get(f"/rules/{iban['id']}/impact")
        assert [(c["name"], c["before"]) for c in r.json()["changes"]] == [
            ("FA-5044_mensajería2.pdf", "ESCALAR")
        ]

        await api.post(f"/rules/{iban['id']}/retire", headers=headers)
        assert (await api.get(f"/processes/{process_id}/findings")).json() == []
