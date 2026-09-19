"""The decisions API against the local database (`make test-db`).

Ingestion and extraction do not exist yet, so the instances, sources and compiled rules are
inserted directly. The sandbox is faked except where a test says otherwise.
"""

import json
import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.core.database import session_factory
from app.features.agents import sandbox
from app.features.ingestion.model import File, Instance
from app.features.processes.model import DecisionType, Symbol
from app.features.rules.model import Rule
from app.features.sources.model import Source
from app.main import app
from tests.support.fakes import dataset_runner

SUPPLIERS = [
    {"nif": "B96233419", "iban": "ES2100752345670600123456"},
    {"nif": "B78451236", "iban": "ES9368884400123588900142"},
]
ENTRIES = [
    {"purchase_order": "PO-2026-0008", "status": "PENDIENTE"},
    {"purchase_order": "PO-2026-0474", "status": "PAGADA"},
    {"purchase_order": "PO-2026-0813", "status": "PENDIENTE"},
]

# Two rules of the v3 norm, as plain functions.
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
FAKE_SANDBOX = dataset_runner({name: fn for name, (_, fn) in RULES_V3.items()})

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
    "FA-9999_sin_leer.pdf": None,  # extraction has not read it yet
}
NAMES = [n for n, symbols in INVOICES.items() if symbols]

INVOICE_PROCESS = {
    "decision_types": [
        {"name": "ESCALAR", "priority": 3, "requires_human": True},
        {"name": "NO_PAGAR", "priority": 2},
        {"name": "PAGAR", "priority": 1, "is_default": True},
    ],
    "symbols": [{"name": "nif", "type": "text"}],
}


def stored(values: dict[str, Any] | None) -> dict[str, Any] | None:
    """Flat test values in the stored format, as extraction writes them."""
    if values is None:
        return None
    return {k: {"value": v, "origin": "text"} for k, v in values.items()}


async def seed(process_id: int, rules: dict[str, tuple[str, str]]) -> None:
    """Everything ingestion and the compiler will produce later. `rules`: name -> (decision,
    code); with the fake sandbox the code is the rule's name."""
    async with session_factory() as session:
        for name, symbols in INVOICES.items():
            digest = uuid.uuid4().hex
            session.add(File(hash=digest, name=name, content=b"%PDF", text=""))
            session.add(
                Instance(
                    process_id=process_id, file_hash=digest, name=name, symbols=stored(symbols)
                )
            )
        session.add(Source(process_id=process_id, name="suppliers", origin="x", rows=[]))
        session.add(Source(process_id=process_id, name="suppliers", origin="y", rows=SUPPLIERS))
        session.add(Source(process_id=process_id, name="erp", origin="erp:t", rows=ENTRIES))
        for name, (decision, code) in rules.items():
            session.add(
                Rule(
                    process_id=process_id,
                    text=name,
                    type="prohibition",
                    decision=decision,
                    code=code,
                    hash=f"hash-{name}",
                    status="active",
                    report={"valid": True},
                )
            )
        from tests.support.rows import publish_fixture

        await publish_fixture(session, process_id)


async def create_process(
    api: AsyncClient, role: str, rules: dict[str, tuple[str, str]] | None = None
) -> tuple[int, dict[str, str]]:
    """A user with `role`, an invoice process and its seeded data."""
    suffix = uuid.uuid4().hex[:8]
    r = await api.post("/users", json={"name": "Ana", "email": f"ana-{suffix}@x.com", "role": role})
    headers = {"X-User-Id": str(r.json()["id"])}
    r = await api.post(
        "/processes/definition", json={"name": f"invoices-{suffix}", **INVOICE_PROCESS}
    )
    assert r.status_code == 200, r.text
    process_id = r.json()["process"]["id"]
    await seed(process_id, rules or {n: (d, n) for n, (d, _) in RULES_V3.items()})
    return process_id, headers


@pytest.fixture
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_run_resolve_and_export(fake_sandbox: None) -> None:
    async with client() as api:
        process_id, headers = await create_process(api, "manager")

        # The engine decides everything that has symbols; the unread one stays PENDING.
        r = await api.post(f"/processes/{process_id}/run")
        assert r.status_code == 200, r.text
        assert r.json() == {"decided": 3, "by_decision": {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1}}

        r = await api.get(f"/processes/{process_id}/instances", params={"status": "PENDING"})
        assert [i["name"] for i in r.json()] == ["FA-9999_sin_leer.pdf"]

        # The export refuses to invent a result for an instance nobody decided.
        r = await api.get(f"/processes/{process_id}/export")
        assert r.status_code == 409, r.text
        assert "FA-9999_sin_leer.pdf" in r.json()["message"]

        # What a person has to look at.
        r = await api.get(f"/processes/{process_id}/queue")
        assert [i["name"] for i in r.json()] == ["FA-5044_mensajería2.pdf"]
        escalated = r.json()[0]["id"]

        detail = (await api.get(f"/instances/{escalated}")).json()
        assert detail["decision"] == "ESCALAR"
        # The API shows symbols as stored, with their provenance.
        assert detail["symbols"]["purchase_order"] == {"value": "PO-2026-0813", "origin": "text"}
        [decision] = detail["decisions"]
        assert decision["author"] == "engine"
        assert decision["reason"] == "iban_mismatch"
        # Every rule's answer is recorded, not just the one that fired.
        assert {(r["reason"], r["fires"]) for r in decision["results"]} == {
            ("iban_mismatch", True),
            ("", False),
        }
        assert [e["step"] for e in detail["events"]] == ["decision"]

        # A person resolves it. The engine's decision stays exactly as it was, and it is still
        # what gets exported: the challenge expects the process output (ADR 0009).
        r = await api.post(
            f"/instances/{escalated}/resolve",
            json={"decision": "NO_PAGAR", "reason": "IBAN not verified with the supplier"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert [(d["author"], d["decision"]) for d in r.json()["decisions"]] == [
            ("engine", "ESCALAR"),
            ("Ana", "NO_PAGAR"),
        ]
        assert r.json()["decision"] == "NO_PAGAR"

        # She also decides the one nobody could read: the engine never did, so hers counts.
        unread = next(
            i["id"]
            for i in (await api.get(f"/processes/{process_id}/instances")).json()
            if i["name"] == "FA-9999_sin_leer.pdf"
        )
        r = await api.post(
            f"/instances/{unread}/resolve",
            json={"decision": "NO_PAGAR", "reason": "Read by hand: the order is already paid"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        r = await api.get(f"/processes/{process_id}/export")
        assert r.status_code == 200, r.text
        lines = [json.loads(line) for line in r.text.splitlines()]
        assert [{k: v for k, v in line.items() if k != "reason"} for line in lines] == [
            {"file_id": "factura_1217.pdf", "result": "PAGAR"},
            {"file_id": "FA-1016_papelería.pdf", "result": "NO_PAGAR"},
            {"file_id": "FA-5044_mensajería2.pdf", "result": "ESCALAR"},
            {"file_id": "FA-9999_sin_leer.pdf", "result": "NO_PAGAR"},
        ]
        # Every line carries the engine's own reason code; a clean case says so explicitly.
        assert all(line["reason"] for line in lines)
        assert [line["reason"] for line in lines][0] == "NO_FINDING"
        # The file_id must survive byte for byte, accents included.
        assert "papeler\\u00eda" not in r.text
        assert "X-Duplicate-Names" not in r.headers


async def test_resolve_rejects_a_decision_not_in_the_process(fake_sandbox: None) -> None:
    async with client() as api:
        process_id, headers = await create_process(api, "operator")
        [first, *_] = (await api.get(f"/processes/{process_id}/instances")).json()

        r = await api.post(
            f"/instances/{first['id']}/resolve",
            json={"decision": "REEMBOLSAR", "reason": "does not exist in this process"},
            headers=headers,
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "conflict"


async def test_export_a_duplicate_name_gives_a_single_line(fake_sandbox: None) -> None:
    async with client() as api:
        process_id, headers = await create_process(api, "operator")
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
        unread = next(
            i["id"]
            for i in (await api.get(f"/processes/{process_id}/instances")).json()
            if i["status"] == "PENDING"
        )
        r = await api.post(
            f"/instances/{unread}/resolve",
            json={"decision": "PAGAR", "reason": "Read by hand"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        r = await api.get(f"/processes/{process_id}/export")
        assert r.status_code == 200, r.text
        output = [json.loads(line) for line in r.text.splitlines()]
        assert len(output) == 4
        assert [
            {k: v for k, v in s.items() if k != "reason"}
            for s in output
            if s["file_id"] == "factura_1217.pdf"
        ] == [{"file_id": "factura_1217.pdf", "result": "NO_PAGAR"}]
        assert json.loads(r.headers["X-Duplicate-Names"]) == ["factura_1217.pdf"]


async def test_a_priority_tie_at_runtime_escalates(fake_sandbox: None) -> None:
    """The loader refuses two types with one priority; one inserted directly is still caught:
    the instance is escalated with the reason, so a person sees it and the export is whole."""
    async with client() as api:
        process_id, _ = await create_process(api, "operator")
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
            from tests.support.rows import publish_fixture

            await publish_fixture(session, process_id)
            both_id = both.id

        r = await api.post(f"/processes/{process_id}/run")
        assert r.status_code == 200, r.text
        assert r.json() == {"decided": 4, "by_decision": {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 2}}

        detail = (await api.get(f"/instances/{both_id}")).json()
        assert detail["decision"] == "ESCALAR"
        assert (
            detail["decisions"][0]["reason"] == "RULE_CONFLICT: ESCALAR, NO_PAGAR share priority 3"
        )


async def test_a_required_symbol_missing_escalates(fake_sandbox: None) -> None:
    """The process marks `nif` required: an instance extracted with no symbols at all is
    escalated with the reason, never paid by default."""
    async with client() as api:
        process_id, _ = await create_process(api, "operator")
        async with session_factory() as session:
            nif = await session.get(Symbol, (process_id, "nif"))
            assert nif is not None
            nif.required = True
            digest = uuid.uuid4().hex
            session.add(File(hash=digest, name="scan.pdf", content=b"%PDF"))
            scan = Instance(process_id=process_id, file_hash=digest, name="scan.pdf", symbols={})
            session.add(scan)
            from tests.support.rows import publish_fixture

            await publish_fixture(session, process_id)
            scan_id = scan.id

        r = await api.post(f"/processes/{process_id}/run")
        assert r.status_code == 200, r.text
        assert r.json() == {"decided": 4, "by_decision": {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 2}}
        detail = (await api.get(f"/instances/{scan_id}")).json()
        assert detail["decision"] == "ESCALAR"
        assert detail["decisions"][0]["reason"] == "MISSING_DATA: nif"


async def test_a_scan_the_rules_would_reject_escalates(fake_sandbox: None) -> None:
    """ADR 0025: a scanned copy of an already paid invoice escalates; its text twin does not."""
    async with client() as api:
        process_id, _ = await create_process(api, "operator")
        async with session_factory() as session:
            digest = uuid.uuid4().hex
            session.add(File(hash=digest, name="scan_paid.pdf", content=b"%PDF"))
            values = INVOICES["FA-1016_papelería.pdf"]
            symbols = {k: {"value": v, "origin": "scan:r1"} for k, v in values.items()}
            scan = Instance(
                process_id=process_id, file_hash=digest, name="scan_paid.pdf", symbols=symbols
            )
            session.add(scan)
            from tests.support.rows import publish_fixture

            await publish_fixture(session, process_id)
            scan_id = scan.id

        r = await api.post(f"/processes/{process_id}/run")
        assert r.json()["by_decision"] == {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 2}
        detail = (await api.get(f"/instances/{scan_id}")).json()
        [decision] = detail["decisions"]
        assert (decision["decision"], decision["reason"]) == (
            "ESCALAR",
            "SCAN_REVIEW: order_already_paid",
        )
        [event] = [e for e in detail["events"] if e["step"] == "decision"]
        assert event["data"]["reason"] == "SCAN_REVIEW: order_already_paid"


@pytest.mark.parametrize(
    ("status", "message"),
    [("compiling", "rules are still compiling"), ("retired", "has no active rules")],
)
async def test_draft_rule_status_does_not_stop_published_execution(
    fake_sandbox: None, status: str, message: str
) -> None:
    """Authoring status changes cannot alter the already approved execution rules."""
    async with client() as api:
        process_id, _ = await create_process(api, "operator")
        async with session_factory() as session:
            await session.execute(
                update(Rule).where(Rule.process_id == process_id).values(status=status)
            )
            await session.commit()

        for action in ("run", "reprocess"):
            r = await api.post(f"/processes/{process_id}/{action}")
            assert r.status_code == 200, r.text
        r = await api.get(f"/processes/{process_id}/instances", params={"status": "PENDING"})
        assert len(r.json()) == 1


def test_flat_symbols_are_refused_on_write() -> None:
    with pytest.raises(ValueError, match="must be stored as"):
        Instance(name="x.pdf", symbols={"nif": "B96233419"})


def assert_flat(case: tuple) -> None:
    """The first case of the seeded process, as rule code must receive it."""
    instance, _, others = case
    assert instance == INVOICES["factura_1217.pdf"]
    assert others == [{**INVOICES[n], "_instance": n} for n in NAMES[1:]]


async def test_rule_code_gets_flat_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """The database holds {value, origin}; rule code only ever sees the values, and every
    other instance of the process tagged with its name."""
    seen: list = []
    monkeypatch.setattr(
        sandbox, "run_dataset", dataset_runner({n: fn for n, (_, fn) in RULES_V3.items()}, seen)
    )
    async with client() as api:
        process_id, _ = await create_process(api, "operator")
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
    assert_flat(seen[0])


REAL_IBAN_RULE = """
def evaluate(instance, sources, others):
    master = [s["iban"] for s in sources["suppliers"] if s["nif"] == instance["nif"]]
    if instance["iban"] not in master:
        return {"fires": True, "reason": "IBAN_MISMATCH"}
    return {"fires": False, "reason": "OK"}
"""
REAL_PAID_RULE = """
def evaluate(instance, sources, others):
    paid = [e for e in sources["erp"]
            if e["purchase_order"] == instance["purchase_order"] and e["status"] == "PAGADA"]
    return {"fires": bool(paid), "reason": "ALREADY_PAID" if paid else "OK"}
"""


async def test_the_run_reaches_the_real_sandbox() -> None:
    """No fake anywhere: the service hands the real sandbox real code. A wrong argument
    between the two would pass every other test here and escalate every invoice in
    production, which is exactly what happened once."""
    real = {
        "iban_mismatch": ("ESCALAR", REAL_IBAN_RULE),
        "order_already_paid": ("NO_PAGAR", REAL_PAID_RULE),
    }
    async with client() as api:
        process_id, _ = await create_process(api, "operator", real)

        r = await api.post(f"/processes/{process_id}/run")

        assert r.status_code == 200, r.text
        assert r.json()["by_decision"] == {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1}
        decided = {
            i["name"]: i["decision"]
            for i in (await api.get(f"/processes/{process_id}/instances")).json()
        }
        assert decided["FA-5044_mensajería2.pdf"] == "ESCALAR"
        assert decided["FA-1016_papelería.pdf"] == "NO_PAGAR"


async def test_what_a_console_reads(fake_sandbox: None) -> None:
    """Summary, richer instance rows, filters, sources and the process trace: one call each."""
    async with client() as api:
        process_id, headers = await create_process(api, "manager")

        # Before any run: the numbers are all zero and the sources are already there.
        summary = (await api.get(f"/processes/{process_id}/summary")).json()
        assert summary["instances"] == 4
        assert summary["by_status"] == {"PENDING": 4}
        assert summary["by_decision"] == {} and summary["queue"] == 0
        assert summary["last_run_at"] is None
        assert [(r["text"], r["status"], r["fires"]) for r in summary["rules"]] == [
            ("iban_mismatch", "active", 0),
            ("order_already_paid", "active", 0),
        ]
        # The current load of each source: the second `suppliers` load replaced the first.
        assert [(s["name"], s["rows"], s["origin"]) for s in summary["sources"]] == [
            ("suppliers", 2, "y"),
            ("erp", 3, "erp:t"),
        ]

        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
        [escalated] = (await api.get(f"/processes/{process_id}/queue")).json()
        r = await api.post(
            f"/instances/{escalated['id']}/resolve",
            json={"decision": "NO_PAGAR", "reason": "Called the supplier"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        summary = (await api.get(f"/processes/{process_id}/summary")).json()
        assert summary["by_status"] == {"PENDING": 1, "DECIDED": 3}
        assert summary["by_decision"] == {"PAGAR": 1, "NO_PAGAR": 2}  # the latest decision counts
        assert summary["queue"] == 0 and summary["resolved"] == 1
        assert {r["text"]: r["fires"] for r in summary["rules"]} == {
            "iban_mismatch": 1,
            "order_already_paid": 1,
        }
        assert summary["last_run_at"] is not None

        # An instance row says what was decided, by whom, why and when.
        rows = (await api.get(f"/processes/{process_id}/instances")).json()
        resolved = next(i for i in rows if i["id"] == escalated["id"])
        assert resolved["author"] == "Ana" and resolved["reason"] == "Called the supplier"
        assert resolved["decided_at"] is not None
        pending = next(i for i in rows if i["status"] == "PENDING")
        assert (pending["decision"], pending["author"], pending["decided_at"]) == (None,) * 3

        r = await api.get(f"/processes/{process_id}/instances", params={"decision": "NO_PAGAR"})
        assert {i["name"] for i in r.json()} == {"FA-1016_papelería.pdf", "FA-5044_mensajería2.pdf"}
        r = await api.get(f"/processes/{process_id}/instances", params={"q": "PAPEL"})
        assert [i["name"] for i in r.json()] == ["FA-1016_papelería.pdf"]

        # The sources, with their rows.
        r = await api.get(f"/processes/{process_id}/sources")
        assert [(s["name"], s["rows"]) for s in r.json()] == [("suppliers", 2), ("erp", 3)]
        r = await api.get(f"/processes/{process_id}/sources/suppliers")
        assert r.json()["data"] == SUPPLIERS
        assert (await api.get(f"/processes/{process_id}/sources/nope")).status_code == 404

        # The trace of the process, newest first, filterable.
        steps = [e["step"] for e in (await api.get(f"/processes/{process_id}/events")).json()]
        # The run is a span with one child per rule; each decision is a point inside it.
        run = ["run_process"] + ["evaluate_rule"] * 2 + ["decision"] * 3
        assert steps == ["resolution", *run, "publish_process_version", "load_definition"]
        r = await api.get(f"/processes/{process_id}/events", params={"step": "resolution"})
        [event] = r.json()
        assert event["instance_id"] == escalated["id"]
        assert event["data"] == {
            "decision": "NO_PAGAR",
            "author": "Ana",
            "reason": "Called the supplier",
            "before": "ESCALAR",
            "previous_author": "engine",
        }
        r = await api.get(
            f"/processes/{process_id}/events", params={"instance_id": escalated["id"]}
        )
        assert [e["step"] for e in r.json()] == ["resolution", "decision"]

        # The file itself, for the viewer, with its exact name.
        r = await api.get(f"/instances/{escalated['id']}/file")
        assert r.status_code == 200
        assert r.content == b"%PDF" and r.headers["content-type"] == "application/pdf"
        assert r.headers["content-disposition"] == (
            "inline; filename*=UTF-8''FA-5044_mensajer%C3%ADa2.pdf"
        )
