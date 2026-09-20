"""API-level treasury planning invariants over captured decision evidence.

These fixtures deliberately bypass extraction and rule execution.  They create the same
immutable rows that those paths persist, so the scheduler is exercised through its real API
without a provider or language model.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.database import session_factory
from app.features.decisions.model import ENGINE, Decision, DecisionReview
from app.features.ingestion.model import File, Instance
from app.features.processes.model import Process
from app.features.sources.model import Source
from app.features.use_cases import service as use_cases
from app.features.versions.model import Execution, ProcessVersion

pytestmark = pytest.mark.skipif(
    os.getenv("TRACEPAY_TEST_POSTGRES") != "1", reason="Requires test PostgreSQL"
)

AS_OF = "2026-01-01"


@dataclass(frozen=True)
class Seed:
    process_id: int
    instance_ids: tuple[int, ...]
    decision_ids: tuple[int, ...]
    execution_id: int
    source_id: int


def _stored(symbols: dict[str, object]) -> dict[str, dict[str, object]]:
    return {name: {"value": value, "origin": "test"} for name, value in symbols.items()}


def _snapshot(process_id: int, name: str, *, pagar_requires_human: bool = False) -> dict:
    return {
        "process": {
            "id": process_id,
            "name": name,
            "use_case_id": 0,
            "description": "Treasury test process",
            "decision_types": [
                {"name": "ESCALAR", "priority": 2, "requires_human": True, "is_default": False},
                {
                    "name": "PAGAR",
                    "priority": 1,
                    "requires_human": pagar_requires_human,
                    "is_default": True,
                },
            ],
            "symbols": [],
            "decision_review": None,
        },
        "rules": [],
        "guidance": [],
        "agents": {},
        "reviewer_prompt": "",
    }


async def _seed(
    cases: list[dict],
    *,
    source_rows: list[dict] | None = None,
    current_source_rows: list[dict] | None = None,
    review_requires_human: bool = False,
    pagar_requires_human: bool = False,
    human_resolution: str | None = None,
) -> Seed:
    name = f"treasury-{uuid4().hex}"
    async with session_factory() as session:
        use_case = await use_cases.ensure(session, name, "Treasury tests")
        process = Process(name=name, use_case_id=use_case.id)
        session.add(process)
        await session.flush()

        snapshot = _snapshot(process.id, name, pagar_requires_human=pagar_requires_human)
        snapshot["process"]["use_case_id"] = use_case.id
        version = ProcessVersion(
            process_id=process.id,
            number=1,
            snapshot=snapshot,
            validation={"valid": True},
            content_hash=f"test-{uuid4().hex}",
            author="treasury tests",
            reason="treasury fixture",
        )
        session.add(version)
        await session.flush()
        process.active_version_id = version.id

        source = Source(
            process_id=process.id,
            name="orders",
            origin="test:initial",
            rows=source_rows or [],
        )
        session.add(source)
        await session.flush()

        instances: list[Instance] = []
        for index, case in enumerate(cases):
            file_hash = f"{uuid4().hex}{index}"
            session.add(File(hash=file_hash, name=case["name"], content=b"%PDF", text=""))
            instance = Instance(
                process_id=process.id,
                file_hash=file_hash,
                name=case["name"],
                status="DECIDED",
                symbols=_stored(case["symbols"]),
            )
            session.add(instance)
            instances.append(instance)
        await session.flush()

        execution = Execution(
            process_id=process.id,
            version_id=version.id,
            inputs={
                "instances": [
                    {
                        "id": instance.id,
                        "file_hash": instance.file_hash,
                        "symbols": instance.symbols,
                    }
                    for instance in instances
                ],
                "source_ids": [source.id],
            },
        )
        session.add(execution)
        await session.flush()

        decisions: list[Decision] = []
        for instance in instances:
            decision = Decision(
                instance_id=instance.id,
                version_id=version.id,
                execution_id=execution.id,
                decision="PAGAR",
                results=[],
                rules_hash="test-rules",
                author=ENGINE,
                reason="fixture",
            )
            session.add(decision)
            decisions.append(decision)
        await session.flush()

        if review_requires_human:
            for decision in decisions:
                session.add(
                    DecisionReview(
                        decision_id=decision.id,
                        status="completed",
                        recommendation="PAGAR",
                        reasoning="fixture review",
                        evidence=[],
                        requires_human=True,
                        snapshot={},
                        model=None,
                        error=None,
                    )
                )

        if human_resolution is not None:
            if len(decisions) != 1:
                raise AssertionError("human_resolution fixtures require one case")
            session.add(
                Decision(
                    instance_id=instances[0].id,
                    version_id=version.id,
                    execution_id=execution.id,
                    decision=human_resolution,
                    results=[],
                    rules_hash="test-rules",
                    author="Manager",
                    reason="resolved in fixture",
                )
            )

        if current_source_rows is not None:
            session.add(
                Source(
                    process_id=process.id,
                    name="orders",
                    origin="test:current",
                    rows=current_source_rows,
                )
            )
        await session.commit()
        return Seed(
            process_id=process.id,
            instance_ids=tuple(instance.id for instance in instances),
            decision_ids=tuple(decision.id for decision in decisions),
            execution_id=execution.id,
            source_id=source.id,
        )


@asynccontextmanager
async def _api() -> AsyncClient:
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        yield api


async def _preview(api: AsyncClient, process_id: int, **overrides: object):
    body = {
        "as_of": AS_OF,
        "weekly_budget": "100.00",
        "horizon_weeks": 4,
    }
    body.update(overrides)
    response = await api.post(f"/processes/{process_id}/treasury/preview", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _case(name: str, amount: str, due_date: str, **extra: object) -> dict:
    return {
        "name": name,
        "symbols": {"total": amount, "issuer_name": name, "due_date": due_date, **extra},
    }


async def test_exact_decimal_limits_and_deterministic_order() -> None:
    seed = await _seed(
        [
            _case("b.pdf", "0.20", "2026-01-01"),
            _case("a.pdf", "0.10", "2026-01-01"),
        ]
    )
    async with _api() as api:
        first = await _preview(api, seed.process_id, weekly_budget="0.30")
        second = await _preview(api, seed.process_id, weekly_budget="0.30")

    assert first == second
    assert [row["name"] for row in first["rows"]] == ["a.pdf", "b.pdf"]
    assert first["totals"]["scheduled_amount"] == "0.30"
    assert first["weeks"][0]["remaining_budget"] == "0.00"


async def test_oversized_invoice_is_backlog_without_splitting() -> None:
    seed = await _seed([_case("large.pdf", "0.31", "2026-01-01")])
    async with _api() as api:
        plan = await _preview(api, seed.process_id, weekly_budget="0.30")

    assert plan["rows"] == []
    assert plan["totals"]["backlog_count"] == 1
    assert plan["totals"]["backlog_amount"] == "0.31"
    assert plan["exclusions"][0]["reason_code"] == "unpayable_amount"


async def test_horizon_overflow_remains_explicit_backlog() -> None:
    seed = await _seed([_case("later.pdf", "10.00", "2026-01-08")])
    async with _api() as api:
        plan = await _preview(api, seed.process_id, horizon_weeks=1)

    assert plan["rows"] == []
    assert plan["exclusions"][0]["reason_code"] == "outside_horizon"
    assert plan["totals"]["backlog_amount"] == "10.00"


async def test_changed_current_source_makes_captured_decision_stale() -> None:
    seed = await _seed(
        [_case("invoice.pdf", "10.00", "2026-01-01")],
        source_rows=[{"purchase_order": "PO-1", "due_date": "2026-01-01"}],
        current_source_rows=[{"purchase_order": "PO-1", "due_date": "2026-02-01"}],
    )
    async with _api() as api:
        plan = await _preview(api, seed.process_id)

    assert plan["rows"] == []
    assert plan["exclusions"][0]["reason_code"] == "stale"


async def test_review_pending_is_excluded_until_human_decision() -> None:
    seed = await _seed(
        [_case("review.pdf", "10.00", "2026-01-01")],
        review_requires_human=True,
    )
    async with _api() as api:
        plan = await _preview(api, seed.process_id)

    assert plan["rows"] == []
    assert plan["exclusions"][0]["reason_code"] == "pending_review"


async def test_historical_human_outcome_is_pending_even_without_review_row() -> None:
    seed = await _seed(
        [_case("historical-review.pdf", "10.00", "2026-01-01")],
        pagar_requires_human=True,
    )
    async with _api() as api:
        plan = await _preview(api, seed.process_id)

    assert plan["rows"] == []
    assert plan["exclusions"][0]["reason_code"] == "pending_review"


async def test_human_resolution_is_latest_but_keeps_its_execution_evidence() -> None:
    seed = await _seed(
        [_case("resolved.pdf", "10.00", "2026-01-01")],
        review_requires_human=True,
        human_resolution="PAGAR",
    )
    async with _api() as api:
        plan = await _preview(api, seed.process_id)

    row = plan["rows"][0]
    assert row["decision_id"] != seed.decision_ids[0]
    assert row["provenance"]["decision_author"] == "Manager"
    assert row["provenance"]["execution_id"] == seed.execution_id


async def test_preview_does_not_append_decisions_sources_or_executions() -> None:
    seed = await _seed([_case("unchanged.pdf", "10.00", "2026-01-01")])
    async with session_factory() as session:
        before = (
            await session.scalar(
                select(func.count())
                .select_from(Decision)
                .where(Decision.instance_id.in_(seed.instance_ids))
            ),
            await session.scalar(
                select(func.count()).select_from(Source).where(Source.process_id == seed.process_id)
            ),
            await session.scalar(
                select(func.count())
                .select_from(Execution)
                .where(Execution.process_id == seed.process_id)
            ),
        )

    async with _api() as api:
        await _preview(api, seed.process_id)

    async with session_factory() as session:
        after = (
            await session.scalar(
                select(func.count())
                .select_from(Decision)
                .where(Decision.instance_id.in_(seed.instance_ids))
            ),
            await session.scalar(
                select(func.count()).select_from(Source).where(Source.process_id == seed.process_id)
            ),
            await session.scalar(
                select(func.count())
                .select_from(Execution)
                .where(Execution.process_id == seed.process_id)
            ),
        )

    assert after == before


async def test_foreign_currency_is_excluded_without_eur_summing() -> None:
    seed = await _seed(
        [
            _case("eur.pdf", "10.00", "2026-01-01", currency="EUR"),
            _case("usd.pdf", "20.00", "2026-01-01", currency="USD"),
        ]
    )
    async with _api() as api:
        plan = await _preview(api, seed.process_id)

    assert [row["name"] for row in plan["rows"]] == ["eur.pdf"]
    assert plan["totals"]["scheduled_amount"] == "10.00"
    assert plan["totals"]["excluded_amount"] == "0.00"
    assert plan["exclusions"][0]["reason_code"] == "currency"
    assert plan["exclusions"][0]["currency"] == "USD"
