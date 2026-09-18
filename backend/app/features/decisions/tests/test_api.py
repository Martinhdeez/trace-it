"""End-to-end against the local database: `docker compose up db -d` and migrations applied.

Ingestion and extraction do not exist yet, so the instances, sources and compiled rules are
inserted directly. The sandbox is replaced by a fake, as agreed with Martín.
"""

import json
import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import session_factory
from app.features.agents import sandbox
from app.features.ingestion.model import File, Instance
from app.features.processes.model import DecisionType
from app.features.rules.model import Rule
from app.features.sources.model import Source
from app.main import app

SUPPLIERS = [
    {"nif": "B96233419", "iban": "ES2100752345670600123456"},
    {"nif": "B78451236", "iban": "ES9368884400123588900142"},
]
ENTRIES = [
    {"purchase_order": "PO-2026-0008", "status": "PENDIENTE"},
    {"purchase_order": "PO-2026-0474", "status": "PAGADA"},
    {"purchase_order": "PO-2026-0813", "status": "PENDIENTE"},
]

# Two rules of the v3 norm, as the compiler will eventually produce them.
RULES_V3 = {
    "iban_mismatch": (
        "ESCALAR",
        lambda i, s, o: (
            i["iban"] != next(p for p in s["suppliers"] if p["nif"] == i["nif"])["iban"]
        ),
    ),
    "order_already_paid": (
        "NO_PAGAR",
        lambda i, s, o: (
            next(e for e in s["erp"] if e["purchase_order"] == i["purchase_order"])["status"]
            == "PAGADA"
        ),
    ),
}

INVOICES = {
    "factura_1217.pdf": {
        "nif": "B96233419",
        "iban": "ES2100752345670600123456",
        "purchase_order": "PO-2026-0008",
    },
    "FA-1016_papelería.pdf": {
        "nif": "B96233419",
        "iban": "ES2100752345670600123456",
        "purchase_order": "PO-2026-0474",
    },
    "FA-5044_mensajería2.pdf": {
        "nif": "B78451236",
        "iban": "ES3900815290070012345678",
        "purchase_order": "PO-2026-0813",
    },
    "FA-9999_sin_leer.pdf": None,  # the two extractions disagreed: REVIEW
}


def fake_sandbox(code: str, instance: dict, sources: dict, others: list) -> dict:
    fires = RULES_V3[code][1](instance, sources, others)
    return {"fires": fires, "reason": code if fires else ""}


def stored(values: dict[str, Any] | None) -> dict[str, Any] | None:
    """Flat test values in the stored format, as extraction writes them."""
    if values is None:
        return None
    return {k: {"value": v, "origin": "text"} for k, v in values.items()}


def fake_batch(code: str, cases: list) -> list:
    return [fake_sandbox(code, *case) for case in cases]


async def seed(process_id: int) -> None:
    """Everything Álvaro's ingestion and Martín's compiler will produce later."""
    async with session_factory() as session:
        for name, symbols in INVOICES.items():
            digest = uuid.uuid4().hex
            session.add(File(hash=digest, name=name, content=b"%PDF", text=""))
            session.add(
                Instance(
                    process_id=process_id,
                    file_hash=digest,
                    name=name,
                    symbols=stored(symbols),
                    status="PENDING" if symbols else "REVIEW",
                    review_reason=None if symbols else "The two extractions disagree",
                )
            )
        session.add(Source(process_id=process_id, name="suppliers", origin="x", rows=[]))
        session.add(Source(process_id=process_id, name="suppliers", origin="y", rows=SUPPLIERS))
        session.add(Source(process_id=process_id, name="erp", origin="erp:t", rows=ENTRIES))
        for name, (decision, _) in RULES_V3.items():
            session.add(
                Rule(
                    process_id=process_id,
                    text=name,
                    type="prohibition",
                    decision=decision,
                    code_a=name,
                    code_b=name,
                    hash=f"hash-{name}",
                    status="active",
                    report={"valid": True},
                )
            )
        await session.commit()


INVOICE_PROCESS = {
    "decision_types": [
        {"name": "ESCALAR", "priority": 3, "requires_human": True},
        {"name": "NO_PAGAR", "priority": 2},
        {"name": "PAGAR", "priority": 1, "is_default": True},
    ],
}


async def create_process(api: AsyncClient, suffix: str, role: str) -> tuple[int, dict[str, str]]:
    """A user with `role`, an invoice process and its seeded data."""
    r = await api.post("/users", json={"name": "Ana", "email": f"ana-{suffix}@x.com", "role": role})
    headers = {"X-User-Id": str(r.json()["id"])}
    r = await api.post(
        "/processes",
        json={
            "name": f"invoices-{suffix}",
            **INVOICE_PROCESS,
            "symbols": [{"name": "nif", "type": "text"}],
        },
    )
    assert r.status_code == 201, r.text
    process_id = r.json()["id"]
    await seed(process_id)
    return process_id, headers


async def test_run_review_and_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, headers = await create_process(api, uuid.uuid4().hex[:8], "manager")

        # The engine decides everything that has symbols. The one in REVIEW is left alone.
        r = await api.post(f"/processes/{process_id}/run")
        assert r.status_code == 200, r.text
        summary = r.json()
        assert summary["by_decision"] == {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1}

        r = await api.get(f"/processes/{process_id}/instances", params={"status": "REVIEW"})
        assert [i["name"] for i in r.json()] == ["FA-9999_sin_leer.pdf"]

        # The export refuses to invent a result for an instance nobody decided.
        r = await api.get(f"/processes/{process_id}/export")
        assert r.status_code == 409, r.text
        assert "FA-9999_sin_leer.pdf" in r.json()["message"]

        # What a person has to look at.
        r = await api.get(f"/processes/{process_id}/queue")
        assert [i["name"] for i in r.json()] == ["FA-5044_mensajería2.pdf"]
        escalated = r.json()[0]["id"]

        r = await api.get(f"/instances/{escalated}")
        detail = r.json()
        assert detail["decision"] == "ESCALAR"
        # The API shows symbols as stored, with their provenance.
        assert detail["symbols"]["purchase_order"] == {"value": "PO-2026-0813", "origin": "text"}
        assert len(detail["decisions"]) == 1
        decision = detail["decisions"][0]
        assert decision["author"] == "engine"
        assert decision["reason"] == "iban_mismatch"
        # Every rule's answer is recorded, not just the one that fired.
        assert {(r["reason"], r["fires"]) for r in decision["results"]} == {
            ("iban_mismatch", True),
            ("", False),
        }
        assert [e["step"] for e in detail["events"]] == ["decision"]

        # A person resolves it. The engine's decision stays exactly as it was, and it is still
        # what gets exported (P4): the challenge expects the process output.
        r = await api.post(
            f"/instances/{escalated}/resolve",
            json={"decision": "NO_PAGAR", "reason": "IBAN not verified with the supplier"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        history = r.json()["decisions"]
        assert [(d["author"], d["decision"], d["human_kind"]) for d in history] == [
            ("engine", "ESCALAR", None),
            ("Ana", "NO_PAGAR", "resolution"),
        ]
        assert r.json()["decision"] == "NO_PAGAR"

        # She also corrects the one in REVIEW: our own doubt, so her decision is exported.
        review = next(
            i["id"]
            for i in (await api.get(f"/processes/{process_id}/instances")).json()
            if i["name"] == "FA-9999_sin_leer.pdf"
        )
        r = await api.post(
            f"/instances/{review}/resolve",
            json={"decision": "NO_PAGAR", "reason": "Read by hand: the order is already paid"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["decisions"][-1]["human_kind"] == "review_correction"

        r = await api.get(f"/processes/{process_id}/export")
        assert r.status_code == 200, r.text
        output = [json.loads(line) for line in r.text.splitlines()]
        assert output == [
            {"file_id": "factura_1217.pdf", "result": "PAGAR"},
            {"file_id": "FA-1016_papelería.pdf", "result": "NO_PAGAR"},
            {"file_id": "FA-5044_mensajería2.pdf", "result": "ESCALAR"},
            {"file_id": "FA-9999_sin_leer.pdf", "result": "NO_PAGAR"},
        ]
        # The file_id must survive byte for byte, accents included.
        assert "papeler\\u00eda" not in r.text
        assert "X-Duplicate-Names" not in r.headers


async def test_resolve_rejects_a_decision_not_in_the_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, headers = await create_process(api, uuid.uuid4().hex[:8], "operator")
        instances: list[dict[str, Any]] = (
            await api.get(f"/processes/{process_id}/instances")
        ).json()

        r = await api.post(
            f"/instances/{instances[0]['id']}/resolve",
            json={"decision": "REEMBOLSAR", "reason": "does not exist in this process"},
            headers=headers,
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "conflict"


async def test_export_a_duplicate_name_gives_a_single_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, headers = await create_process(api, uuid.uuid4().hex[:8], "operator")
        # A second, different file with the same name arrives later: it is the one exported.
        async with session_factory() as session:
            digest = uuid.uuid4().hex
            session.add(File(hash=digest, name="factura_1217.pdf", content=b"%PDF"))
            session.add(
                Instance(
                    process_id=process_id,
                    file_hash=digest,
                    name="factura_1217.pdf",
                    symbols=stored(INVOICES["FA-1016_papelería.pdf"]),  # order already paid
                )
            )
            await session.commit()

        r = await api.post(f"/processes/{process_id}/run")
        assert r.json()["by_decision"] == {"PAGAR": 1, "NO_PAGAR": 2, "ESCALAR": 1}
        review = next(
            i["id"]
            for i in (await api.get(f"/processes/{process_id}/instances")).json()
            if i["status"] == "REVIEW"
        )
        r = await api.post(
            f"/instances/{review}/resolve",
            json={"decision": "PAGAR", "reason": "Read by hand"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        r = await api.get(f"/processes/{process_id}/export")
        assert r.status_code == 200, r.text
        output = [json.loads(line) for line in r.text.splitlines()]
        assert len(output) == 4
        assert [s for s in output if s["file_id"] == "factura_1217.pdf"] == [
            {"file_id": "factura_1217.pdf", "result": "NO_PAGAR"}
        ]
        assert json.loads(r.headers["X-Duplicate-Names"]) == ["factura_1217.pdf"]


async def test_a_priority_tie_at_runtime_goes_to_review(monkeypatch: pytest.MonkeyPatch) -> None:
    """The loader refuses two types with one priority; one inserted directly is still caught:
    the instance goes to REVIEW with the reason, and no decision is written."""
    monkeypatch.setattr(sandbox, "run_batch", fake_batch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, _ = await create_process(api, uuid.uuid4().hex[:8], "operator")
        async with session_factory() as session:
            no_pagar = await session.get(DecisionType, (process_id, "NO_PAGAR"))
            assert no_pagar is not None
            no_pagar.priority = 3
            # A new IBAN on an order already paid: both rules fire, ESCALAR ties NO_PAGAR.
            digest = uuid.uuid4().hex
            session.add(File(hash=digest, name="FA-7777_both.pdf", content=b"%PDF"))
            both = Instance(
                process_id=process_id,
                file_hash=digest,
                name="FA-7777_both.pdf",
                symbols=stored(
                    {**INVOICES["FA-5044_mensajería2.pdf"], "purchase_order": "PO-2026-0474"}
                ),
            )
            session.add(both)
            await session.commit()
            both_id = both.id

        r = await api.post(f"/processes/{process_id}/run")
        assert r.status_code == 200, r.text
        # The others fire one rule each: no tie, decided as before.
        assert r.json() == {
            "decided": 3,
            "by_decision": {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1},
            "review": 1,
        }

        detail = (await api.get(f"/instances/{both_id}")).json()
        assert detail["status"] == "REVIEW"
        assert detail["decisions"] == []
        assert [e["step"] for e in detail["events"]] == ["review"]
        assert "RULE_CONFLICT: ESCALAR, NO_PAGAR" in detail["events"][0]["data"]["reason"]
        async with session_factory() as session:
            instance = await session.get(Instance, both_id)
            assert instance is not None
            assert (instance.review_reason or "").startswith("RULE_CONFLICT")

        # Export refuses while our own doubt is open.
        assert (await api.get(f"/processes/{process_id}/export")).status_code == 409


def test_flat_symbols_are_refused_on_write() -> None:
    with pytest.raises(ValueError, match="must be stored as"):
        Instance(name="x.pdf", symbols={"nif": "B96233419"})


def recording(seen: list, batch: Any = fake_batch) -> Any:
    """`batch` that also keeps every case it was handed."""

    def run_batch(code: str, cases: list) -> list:
        seen.extend(cases)
        return batch(code, cases)

    return run_batch


def assert_flat(case: tuple) -> None:
    """The first case of the seeded process, as rule code must receive it."""
    instance, _, others = case
    assert instance == INVOICES["factura_1217.pdf"]
    assert others == [
        {**INVOICES[n], "_instance": n}
        for n in ("FA-1016_papelería.pdf", "FA-5044_mensajería2.pdf")
    ]


async def test_rule_code_gets_flat_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """The database holds {value, origin}; rule code only ever sees the values."""
    seen: list = []
    monkeypatch.setattr(sandbox, "run_batch", recording(seen))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        process_id, _ = await create_process(api, uuid.uuid4().hex[:8], "operator")
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
    assert_flat(seen[0])
