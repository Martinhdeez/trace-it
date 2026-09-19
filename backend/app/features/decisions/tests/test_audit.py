"""A rule change is checked against every decision already taken, before it is adopted.

Same setup as `test_api.py`: instances, sources and compiled rules inserted directly, the
sandbox faked.
"""

import asyncio
import uuid
from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.core.database import session_factory
from app.features.agents import compiler, llm, sandbox
from app.features.decisions.tests.test_api import (
    INVOICES,
    RULES_V3,
    assert_flat,
    client,
    create_process,
    stored,
)
from app.features.ingestion.model import File, Instance
from app.features.rules import service as rules
from app.features.rules.model import Rule
from tests.support.fakes import dataset_runner
from tests.support.models import per_role

# A rule nobody has activated yet: it escalates any invoice from this supplier. It stays
# out of RULES_V3 so `seed` does not seed it as active.
NEW_RULE = "watched_supplier"
RULES = {
    **{n: fn for n, (_, fn) in RULES_V3.items()},
    NEW_RULE: lambda i, s, o: i["nif"] == "B96233419",
}


@pytest.fixture(autouse=True)
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(RULES))


async def create_draft(process_id: int) -> int:
    async with session_factory() as session:
        rule = Rule(
            process_id=process_id,
            text=NEW_RULE,
            type="prohibition",
            decision="ESCALAR",
            code=NEW_RULE,
            hash=f"hash-{NEW_RULE}",
            status="draft",
            report={"valid": True},
        )
        session.add(rule)
        await session.commit()
        return rule.id


async def prepare(api: AsyncClient) -> tuple[int, dict[str, str]]:
    """A process with its invoices already decided by the engine."""
    process_id, headers = await create_process(api, "manager")
    await api.post(f"/processes/{process_id}/run")
    return process_id, headers


async def test_impact_is_visible_before_activating() -> None:
    async with client() as api:
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


async def test_activating_records_findings_and_leaves_the_past_alone() -> None:
    async with client() as api:
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


async def test_a_human_decision_blocks_the_rule() -> None:
    """The rules do not overrule a person, and a person does not silently veto a rule."""
    async with client() as api:
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


async def test_retiring_is_checked_like_activating() -> None:
    async with client() as api:
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


async def test_an_escalated_case_gives_no_finding() -> None:
    """An instance sitting in the human queue was never acted on, so nothing went wrong."""
    async with client() as api:
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


async def test_impact_gives_rule_code_flat_values(monkeypatch: pytest.MonkeyPatch) -> None:
    async with client() as api:
        process_id, _ = await prepare(api)
        rule_id = await create_draft(process_id)
        seen: list = []
        monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(RULES, seen))
        assert (await api.get(f"/rules/{rule_id}/impact")).status_code == 200
    assert_flat(seen[0])


QUIET_RULE = "never_fires"
QUIET = {**RULES, QUIET_RULE: lambda i, s, o: False}


def compiled(code: str | None, valid: bool = True) -> Callable:
    """`compiler.compile_rule` answering with `code`, as if the loop had ended so."""

    async def compile_rule(session, rule, symbols):
        return compiler.Compilation(code, [], {"valid": valid and code is not None})

    return compile_rule


async def compile_draft(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch, code: str | None
) -> dict:
    process_id, _ = await prepare(api)
    rule_id = await create_draft(process_id)
    monkeypatch.setattr(compiler, "compile_rule", compiled(code))
    r = await api.post(f"/rules/{rule_id}/compile")
    assert r.status_code == 200, r.text
    return r.json()


async def test_a_valid_rule_that_changes_nothing_activates_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(QUIET))
    async with client() as api:
        rule = await compile_draft(api, monkeypatch, QUIET_RULE)
    assert rule["status"] == "active"
    assert rule["report"]["activation"] == {
        "auto": True,
        "why": "changes 0/3 past decisions (limit 5%)",
        "changed": 0,
        "decided": 3,
    }


async def test_a_rule_that_changes_too_much_waits_for_a_person(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with client() as api:
        rule = await compile_draft(api, monkeypatch, NEW_RULE)
    assert rule["status"] == "draft"
    assert rule["report"]["valid"] is True
    assert rule["report"]["activation"]["auto"] is False
    assert rule["report"]["activation"]["changed"] == 2


async def save(api: AsyncClient, process_id: int, text: str) -> dict:
    """Save a rule as a manager does: it is compiled in the background."""
    r = await api.post(
        f"/processes/{process_id}/rules",
        json={"text": text, "type": "prohibition", "decision": "ESCALAR"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "compiling"
    return (await api.get(f"/rules/{r.json()['id']}")).json()


async def test_a_saved_rule_compiles_itself_and_activates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(QUIET))
    monkeypatch.setattr(compiler, "compile_rule", compiled(QUIET_RULE))
    async with client() as api:
        process_id, _ = await prepare(api)
        rule = await save(api, process_id, QUIET_RULE)
    assert rule["status"] == "active" and rule["code"] == QUIET_RULE


@pytest.mark.parametrize("person_decided", [False, True])
async def test_a_rule_that_needs_data_escalates_every_instance(
    monkeypatch: pytest.MonkeyPatch, person_decided: bool
) -> None:
    needs_data = {
        "_output": "NeedsData",
        "missing": ["symbol: delivery_date"],
        "explanation": "The rule compares with the delivery date",
    }
    monkeypatch.setattr(llm, "model_for", per_role({"tester": [needs_data]}))
    async with client() as api:
        process_id, headers = await prepare(api)
        rule = await save(api, process_id, "Escalate late deliveries")

        # Enforced although it would change every past decision: failing closed needs no
        # person's approval.
        assert rule["status"] == "blocked" and rule["code"] is None
        assert rule["report"]["needs_data"]["missing"] == ["symbol: delivery_date"]

        async with session_factory() as session:
            digest = uuid.uuid4().hex
            session.add(File(hash=digest, name="late.pdf", content=b"%PDF", text=""))
            symbols = stored(INVOICES["factura_1217.pdf"])  # a clean invoice
            session.add(
                Instance(process_id=process_id, file_hash=digest, name="late.pdf", symbols=symbols)
            )
            await session.commit()
        r = await api.post(f"/processes/{process_id}/run")
        assert r.json() == {"decided": 1, "by_decision": {"ESCALAR": 1}}
        instances = (await api.get(f"/processes/{process_id}/instances")).json()
        late = next(i for i in instances if i["name"] == "late.pdf")
        [decision] = (await api.get(f"/instances/{late['id']}")).json()["decisions"]
        assert decision["reason"] == f"RULE_NEEDS_DATA {rule['id']}: missing symbol: delivery_date"

        if person_decided:
            r = await api.post(
                f"/instances/{late['id']}/resolve",
                json={"decision": "NO_PAGAR", "reason": "Delivered late, checked by hand"},
                headers=headers,
            )
            assert r.status_code == 200, r.text

        # Once the process has the data, a recompile makes it an ordinary rule. Undoing its
        # own escalations does not count as impact; contradicting a person still blocks.
        monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(QUIET))
        monkeypatch.setattr(compiler, "compile_rule", compiled(QUIET_RULE))
        r = await api.post(f"/rules/{rule['id']}/compile")
        assert r.status_code == 200, r.text
        rule = r.json()
        assert rule["code"] == QUIET_RULE and rule["report"]["valid"] is True
        activation = rule["report"]["activation"]
        if person_decided:
            assert rule["status"] == "draft"
            assert activation["why"] == "1 decisions taken by a person would change"
        else:
            assert rule["status"] == "active"
            assert activation["unblocked"] == 1 and activation["changed"] == 0


async def test_startup_resumes_rules_left_compiling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(QUIET))
    monkeypatch.setattr(compiler, "compile_rule", compiled(QUIET_RULE))
    async with client() as api:
        process_id, _ = await prepare(api)
        async with session_factory() as session:
            rule = Rule(
                process_id=process_id,
                text=QUIET_RULE,
                type="prohibition",
                decision="ESCALAR",
                status="compiling",  # the server stopped mid-compilation
            )
            session.add(rule)
            await session.commit()

        await asyncio.gather(*await rules.resume_compilations())

        assert (await api.get(f"/rules/{rule.id}")).json()["status"] == "active"
