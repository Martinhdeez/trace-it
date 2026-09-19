"""Live sources (ADR 0028): a run syncs the ERP first, decides on the fresh rows, and when the
sync fails never reads the older snapshot. Real sandbox, local database, the ERP scripted."""

import json
import shutil
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.database import session_factory
from app.features.agents.compiler import source_reads
from app.features.decisions.engine import Outcomes, RuleResult, _combine
from app.features.decisions.model import Decision
from app.features.decisions.tests.test_api import client, stored
from app.features.ingestion.model import File, Instance
from app.features.processes.model import DecisionType
from app.features.rules.model import Rule
from app.features.sources import service as sources
from app.features.sources.http_connector import Stats, SyncError
from app.features.sources.model import Source
from app.features.versions.model import Execution
from tests.support import pack

KNOWN_IBAN = """
def evaluate(instance, sources, others):
    ibans = [row["iban"] for row in sources.get("suppliers") or []]
    if instance.get("iban") not in ibans:
        return {"fires": True, "reason": "UNKNOWN_IBAN"}
    return {"fires": False, "reason": ""}
"""
ORDER_PAID = """
def rows(sources, name):
    return sources.get(name) or []


def evaluate(instance, sources, others):
    for row in rows(sources, "erp"):
        if row["purchase_order"] == instance.get("purchase_order") and row["status"] == "PAGADA":
            return {"fires": True, "reason": "ALREADY_PAID"}
    return {"fires": False, "reason": ""}
"""
IBAN = "ES2100752345670600123456"
INVOICES = {
    "bad-iban.pdf": {"iban": "ES00BAD", "purchase_order": "PO-1"},  # a non-ERP rule rejects
    "needs-erp.pdf": {"iban": IBAN, "purchase_order": "PO-2"},  # only the ERP can tell
}


def entry(order: str, status: str) -> dict:
    return {
        "entry_id": f"AS-{order}",
        "date": "2026-01-31",
        "supplier_id": "P001",
        "nif": "",
        "purchase_order": order,
        "amount": "100.00",
        "status": status,
    }


class ScriptedErp:
    """Stands in for `HttpConnector`: serves `rows`, or raises when they are an error."""

    rows: list[dict] | Exception = []

    def __init__(self, config, transport=None):
        self.stats = Stats()
        self.base_url = "http://scripted-erp"

    async def download(self) -> list[dict]:
        if isinstance(ScriptedErp.rows, Exception):
            raise ScriptedErp.rows
        return [dict(r) for r in ScriptedErp.rows]


@pytest.fixture
def erp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> type[ScriptedErp]:
    """The invoice pack's real `sources.json` and `schema.json`, for processes of the use
    case named `live-*`, with the connector scripted."""
    monkeypatch.setattr(sources, "HttpConnector", ScriptedErp)
    monkeypatch.setattr(settings, "processes_dir", tmp_path)
    (tmp_path / "pack").mkdir()
    for name in ("sources.json", "schema.json"):
        shutil.copy(pack.PACK / "invoice-payment" / name, tmp_path / "pack" / name)
    ScriptedErp.rows = []
    return ScriptedErp


async def live_process(tmp_path: Path, stale_erp: list[dict]) -> int:
    """A process whose use case has the pack's connectors, two rules, two invoices, the
    supplier master and an older ERP snapshot."""
    from tests.support.rows import process, publish_fixture

    name = f"live-{uuid.uuid4().hex[:8]}"
    (tmp_path / "pack.json").write_text(json.dumps({"name": name}))
    async with session_factory() as session:
        row = await process(session, name)
        for t, priority, default, human in (
            ("ESCALAR", 3, False, True),
            ("NO_PAGAR", 2, False, False),
            ("PAGAR", 1, True, False),
        ):
            session.add(
                DecisionType(
                    process_id=row.id,
                    name=t,
                    priority=priority,
                    is_default=default,
                    requires_human=human,
                )
            )
        for file_name, symbols in INVOICES.items():
            digest = uuid.uuid4().hex
            session.add(File(hash=digest, name=file_name, content=b"%PDF", text=""))
            session.add(
                Instance(
                    process_id=row.id, file_hash=digest, name=file_name, symbols=stored(symbols)
                )
            )
        session.add(Source(process_id=row.id, name="suppliers", origin="t", rows=[{"iban": IBAN}]))
        session.add(Source(process_id=row.id, name="erp", origin="erp:stale", rows=stale_erp))
        for text, code in (("known_iban", KNOWN_IBAN), ("order_paid", ORDER_PAID)):
            session.add(
                Rule(
                    process_id=row.id,
                    text=text,
                    type="prohibition",
                    decision="NO_PAGAR",
                    code=code,
                    hash=f"hash-{text}",
                    status="active",
                    report={"valid": True},
                )
            )
        await session.flush()
        process_id = row.id
        await publish_fixture(session, process_id)
    return process_id


async def decisions(api, process_id: int) -> dict[str, tuple[str, str | None]]:
    rows = (await api.get(f"/processes/{process_id}/instances")).json()
    return {i["name"]: (i["decision"], i["reason"]) for i in rows}


async def test_a_run_syncs_first_and_decides_on_the_fresh_rows(erp, tmp_path: Path) -> None:
    # The stored snapshot says PO-2 is paid; the ERP now says it is pending.
    process_id = await live_process(tmp_path, [entry("PO-1", "PENDIENTE"), entry("PO-2", "PAGADA")])
    erp.rows = [entry("PO-1", "PENDIENTE"), entry("PO-2", "PENDIENTE")]
    async with client() as api:
        r = await api.post(f"/processes/{process_id}/run")
        assert r.status_code == 200, r.text
        assert r.json() == {"decided": 2, "by_decision": {"NO_PAGAR": 1, "PAGAR": 1}}
        assert await decisions(api, process_id) == {
            "bad-iban.pdf": ("NO_PAGAR", "UNKNOWN_IBAN"),
            "needs-erp.pdf": ("PAGAR", None),
        }
        [erp_load] = [
            s
            for s in (await api.get(f"/processes/{process_id}/sources")).json()
            if s["name"] == "erp"
        ]
    assert erp_load["status"] == "ok" and erp_load["origin"].startswith("erp:20")


async def test_erp_down_escalates_only_what_depends_on_it(erp, tmp_path: Path) -> None:
    # The older snapshot would pay PO-2: it must not be read.
    process_id = await live_process(tmp_path, [entry("PO-2", "PENDIENTE")])
    erp.rows = SyncError("GET /erp/asientos: gave up after 6 attempts (last: 503)")
    async with client() as api:
        r = await api.post(f"/processes/{process_id}/run")
        assert r.status_code == 200, r.text
        assert r.json()["by_decision"] == {"NO_PAGAR": 1, "ESCALAR": 1}
        assert "gave up after 6 attempts" in r.json()["down_sources"]["erp"]
        assert await decisions(api, process_id) == {
            "bad-iban.pdf": ("NO_PAGAR", "UNKNOWN_IBAN"),
            "needs-erp.pdf": ("ESCALAR", "SOURCE_UNAVAILABLE: erp"),
        }

        # The source is shown as down, and so is the ingestion plane.
        listed = {s["name"]: s for s in (await api.get(f"/processes/{process_id}/sources")).json()}
        assert listed["erp"]["status"] == "down" and "503" in listed["erp"]["error"]
        assert listed["suppliers"]["status"] is None  # never synced: a workbook load
        [ingestion] = [
            p for p in (await api.get("/health/planes")).json() if p["plane"] == "ingestion"
        ]
        assert ingestion["status"] in ("degraded", "down")

        # The execution captured no ERP snapshot, only that it was down: a replay agrees.
        async with session_factory() as session:
            run = await session.scalar(
                select(Execution)
                .where(Execution.process_id == process_id)
                .order_by(Execution.id.desc())
            )
            erp_ids = set(
                await session.scalars(
                    select(Source.id).where(Source.process_id == process_id, Source.name == "erp")
                )
            )
            decision_id = await session.scalar(
                select(Decision.id)
                .join(Instance)
                .where(Instance.process_id == process_id, Instance.name == "needs-erp.pdf")
            )
        assert not erp_ids & set(run.inputs["source_ids"])
        assert run.inputs["down"] == r.json()["down_sources"]
        email = f"m-{uuid.uuid4().hex[:6]}@x.com"
        user = (
            await api.post("/users", json={"name": "M", "email": email, "role": "manager"})
        ).json()
        replay = await api.post(
            f"/decisions/{decision_id}/replay", headers={"X-User-Id": str(user["id"])}
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["matches"] is True


async def test_a_snapshot_missing_a_canonical_field_fails_the_sync(erp, tmp_path: Path) -> None:
    process_id = await live_process(tmp_path, [entry("PO-2", "PENDIENTE")])
    erp.rows = [{k: v for k, v in entry("PO-2", "PAGADA").items() if k != "status"}]
    async with client() as api:
        r = await api.post(f"/processes/{process_id}/sources/erp/sync")
        assert r.status_code == 502
        assert "Not the canonical schema: status missing in 1 rows (AS-PO-2)" in r.json()["message"]

        # Treated as down: the run does not read the older snapshot either.
        r = await api.post(f"/processes/{process_id}/run")
        assert "canonical schema" in r.json()["down_sources"]["erp"]
        assert (await decisions(api, process_id))["needs-erp.pdf"] == (
            "ESCALAR",
            "SOURCE_UNAVAILABLE: erp",
        )
    async with session_factory() as session:
        origins = list(
            await session.scalars(
                select(Source.origin).where(Source.process_id == process_id, Source.name == "erp")
            )
        )
    assert origins == ["erp:stale"]  # nothing written


async def test_a_connector_without_a_canonical_field_fails_the_sync(erp, tmp_path: Path) -> None:
    config = json.loads((tmp_path / "pack" / "sources.json").read_text())
    config["sources"]["erp"]["fields"]["order_ref"] = config["sources"]["erp"]["fields"].pop(
        "purchase_order"
    )
    (tmp_path / "pack" / "sources.json").write_text(json.dumps(config))
    process_id = await live_process(tmp_path, [])
    erp.rows = [entry("PO-2", "PENDIENTE")]
    async with client() as api:
        r = await api.post(f"/processes/{process_id}/sources/erp/sync")
    assert r.status_code == 502
    assert "No field mapped to canonical ['purchase_order']" in r.json()["message"]


def test_which_sources_each_rule_reads() -> None:
    assert source_reads(KNOWN_IBAN) == ["suppliers"]
    assert source_reads(ORDER_PAID) == ["erp"]
    assert source_reads('def evaluate(i, s, o):\n    return s["orders"] and s.get("erp")') == [
        "erp",
        "orders",
    ]
    computed = "def evaluate(i, s, o):\n    n = 'erp'\n    return s.get(n)"
    assert source_reads(computed) == ["*"]  # could be any source: every one
    assert source_reads("def evaluate(i, s, o):\n    return list(s)") == ["*"]
    assert source_reads("def evaluate(i, s, o):\n    return i['x']") == []
    assert source_reads(None) == []


def test_the_pack_rules_that_read_the_erp() -> None:
    """Hand-written and frozen rules, found by the same analysis."""
    hand = {
        Path(r["code"]).stem: source_reads(c)
        for r, c in zip(pack.definition()["rules"], pack.codes(), strict=True)
    }
    frozen = {
        p.stem: source_reads(p.read_text())
        for p in (pack.PACK / "invoice-payment" / "frozen" / "2026-09-19" / "rules").glob("*.py")
    }
    assert sorted(k for k, v in hand.items() if "erp" in v) == [
        "r13-entry-in-erp",
        "r14-erp-matches-orders",
        "r15-order-already-paid",
    ]
    assert sorted(k for k, v in frozen.items() if "erp" in v) == ["n5-1", "n5-2"]
    assert not any("*" in v for v in [*hand.values(), *frozen.values()])


OUTCOMES = Outcomes({"ESCALAR": 3, "NO_PAGAR": 2, "PAGAR": 1}, default="PAGAR", escalate="ESCALAR")


def rule(rule_id: int, decision: str) -> Rule:
    return Rule(id=rule_id, text=f"r{rule_id}", decision=decision, code="x", hash="h")


def combine(results: list[tuple[str, bool | None, str]], **kw) -> tuple[str, str]:
    rules = [rule(n, d) for n, (d, _, _) in enumerate(results, 1)]
    rows = [RuleResult(n, "h", f, why) for n, (_, f, why) in enumerate(results, 1)]
    verdict = _combine(rules, rows, OUTCOMES, "hash", kw.get("missing", []), kw.get("scan"))
    return verdict.decision, verdict.reason


DOWN = ("NO_PAGAR", None, "SOURCE_UNAVAILABLE 2: erp")


def test_precedence_with_a_source_down() -> None:
    # No rule that ran rejects: only the ERP could have.
    assert combine([("NO_PAGAR", False, ""), DOWN]) == ("ESCALAR", "SOURCE_UNAVAILABLE: erp")
    # A rule that ran rejects with the priority an unrun rule could reach: decided.
    assert combine([("NO_PAGAR", True, "BAD"), DOWN]) == ("NO_PAGAR", "BAD")
    # An unrun rule could escalate above the rejection: not decided.
    assert combine([("NO_PAGAR", True, "BAD"), ("ESCALAR", None, "SOURCE_UNAVAILABLE 2: erp")]) == (
        "ESCALAR",
        "SOURCE_UNAVAILABLE: erp",
    )
    # Earlier causes keep their place.
    assert combine([("NO_PAGAR", True, "BAD"), DOWN], missing=["iban"]) == (
        "ESCALAR",
        "MISSING_DATA: iban",
    )
    assert combine([("NO_PAGAR", True, "BAD"), DOWN], scan=["iban"]) == (
        "ESCALAR",
        "SCAN_REVIEW: BAD",
    )
    assert combine([("NO_PAGAR", None, "RULE_ERROR 1: boom"), DOWN])[1] == (
        "RULE_ERROR 1: boom | SOURCE_UNAVAILABLE 2: erp"
    )
