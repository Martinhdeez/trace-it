"""Usage reconciliation, nested/concurrent timing, cache replay and time-window drill-down."""

import uuid
from datetime import UTC, datetime, timedelta

from app.core.database import session_factory
from app.core.events import Event
from app.features.decisions.tests.test_api import client, create_process
from app.features.traces.breakdown import aggregate, self_ms, usage

START = datetime(2026, 1, 1, tzinfo=UTC)


def row(step="llm_run", duration=100, start=0, **data):
    return {
        "step": step,
        "status": "ok",
        "started_at": START + timedelta(milliseconds=start),
        "duration_ms": duration,
        "data": data,
    }


def test_exclusive_time_unions_overlapping_children_and_clips_to_parent():
    parent = row(duration=1000)
    children = [
        row(start=-100, duration=200),
        row(start=200, duration=400),
        row(start=400, duration=400),
        row(start=900, duration=500),
    ]
    assert self_ms(parent, children) == 200
    assert self_ms(row(duration=None), children) is None
    assert self_ms(row(duration=0), children) == 0
    assert self_ms(parent, [row(duration=None)]) == 1000


def test_only_network_calls_and_llm_runs_contribute_usage():
    reported = dict(
        input_tokens=100,
        output_tokens=20,
        cached_tokens=70,
        cost_usd=0.25,
        cost_status="known",
        requests=2,
    )
    for step, extra in [
        ("extraction", {}),
        ("provider_call", {"outcome": "replay"}),
        ("provider_call", {"outcome": "blocked_uncertain"}),
    ]:
        item = usage(row(step, **reported, **extra), 100)
        assert (item.input_tokens, item.output_tokens, item.known_cost_usd, item.requests) == (
            0,
            0,
            0,
            0,
        )
    provider = usage(row("provider_call", network_attempted=True, **reported), 100)
    agent = usage(row(**reported), 100)
    assert (provider.requests, agent.requests) == (1, 2)
    assert provider.input_tokens + provider.output_tokens == 120  # cached input is not added
    unknown = usage(row(requests=3, cost_status="unknown", cost_usd=20), None)
    assert unknown.known_cost_usd == 0 and unknown.unpriced_requests == 3
    assert unknown.timed_spans == 0
    included = usage(row(requests=1, cost_status="included"), 0)
    assert included.unpriced_requests == 0 and included.timed_spans == 1
    assert aggregate([provider, agent])["known_cost_usd"] == 0.5


def test_restored_measurements_keep_usage_and_identify_original_history():
    imported = usage(
        row(
            "provider_call",
            network_attempted=True,
            cached_replay=True,
            input_tokens=100,
            output_tokens=20,
            cost_usd=0.25,
            cost_status="known",
        ),
        50,
    )
    live = usage(row(requests=1, cost_status="unknown"), 10)
    assert imported.imported_spans == 1
    assert imported.requests == 1 and imported.known_cost_usd == 0.25
    total = aggregate([imported, live])
    assert total["spans"] == 2 and total["imported_spans"] == 1
    assert total["requests"] == 2 and total["unpriced_requests"] == 1
    assert total["self_ms"] == 60


async def test_breakdown_reconciles_all_levels_and_paginates_one_snapshot():
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        other_id, _ = await create_process(api, "manager")
        trace_id = uuid.uuid4().hex
        parent_id = uuid.uuid4().hex[:16]
        data = dict(
            input_tokens=100, output_tokens=20, cached_tokens=60, cost_usd=0.25, cost_status="known"
        )
        events = [
            dict(step="upload_document", duration=1000, span_id=parent_id, **data),
            dict(
                step="provider_call",
                duration=500,
                start=100,
                parent_id=parent_id,
                provider="vendor",
                operation="ocr",
                network_attempted=True,
                cached_replay=True,
                **data,
            ),
            # Cross-plane child overlaps the provider: subtract their union from the parent.
            dict(
                step="llm_run",
                duration=500,
                start=400,
                parent_id=parent_id,
                agent="compiler",
                model="a",
                requests=2,
                **data,
            ),
            dict(
                step="provider_call",
                duration=50,
                start=1100,
                provider="vendor",
                operation="ocr",
                outcome="replay",
                network_attempted=False,
                **data,
            ),
            dict(
                step="llm_run",
                duration=1500,
                start=86400000,
                role="compiler",
                model="b",
                requests=1,
                input_tokens=40,
                output_tokens=10,
                cost_status="unknown",
            ),
            dict(
                step="llm_run",
                duration=None,
                start=86403000,
                role="compiler",
                model="a",
                requests=0,
                cost_status="included",
            ),
            dict(step="run_process", duration=10, start=86406000),
        ]
        async with session_factory() as session:
            for item in events:
                record = item.copy()
                span_id = record.pop("span_id", uuid.uuid4().hex[:16])
                parent = record.pop("parent_id", None)
                base = row(
                    record.pop("step"), record.pop("duration"), record.pop("start", 0), **record
                )
                session.add(
                    Event(
                        **base,
                        trace_id=trace_id,
                        span_id=span_id,
                        parent_id=parent,
                        process_id=process_id,
                    )
                )
            session.add(
                Event(
                    **row(requests=1, **data),
                    trace_id=uuid.uuid4().hex,
                    span_id=uuid.uuid4().hex[:16],
                    process_id=other_id,
                )
            )
            await session.commit()
        url = f"/processes/{process_id}/metrics/breakdown"
        window = {"since": START.isoformat(), "until": (START + timedelta(days=3)).isoformat()}
        response = await api.get(url, params=window)
        assert response.status_code == 200, response.text
        overview = response.json()
        assert overview["totals"] is None
        planes = {r["plane"]: r for r in overview["groups"]}
        assert planes["ingestion"]["known_cost_usd"] == 0.25
        assert planes["ingestion"]["imported_spans"] == 1
        assert planes["ingestion"]["self_ms"] == 750  # parent 200 + network 500 + replay 50
        assert planes["ingestion"]["input_tokens"] == 100
        assert planes["ingestion"]["replays"] == 1
        assert planes["agents"]["input_tokens"] == 140
        assert planes["agents"]["known_cost_usd"] == 0.25
        assert planes["agents"]["unpriced_requests"] == 1
        assert planes["execution"]["input_tokens"] == 0
        assert planes["execution"]["self_ms"] == 10
        assert overview["bucket_seconds"] == 86400
        assert len(overview["series"]) == 4  # separate plane/day series
        for plane, expected in planes.items():
            plane_data = (await api.get(url, params={**window, "plane": plane})).json()
            for field in (
                "input_tokens",
                "output_tokens",
                "known_cost_usd",
                "self_ms",
                "unpriced_requests",
            ):
                assert sum(r[field] for r in plane_data["groups"]) == expected[field]
                assert (
                    sum(r[field] for r in overview["flow"] if r["plane"] == plane)
                    == expected[field]
                )
                assert sum(r[field] for r in plane_data["flow"]) == expected[field]
                assert (
                    sum(r[field] for r in overview["series"] if r["plane"] == plane)
                    == expected[field]
                )
            for group in plane_data["groups"]:
                detail = (
                    await api.get(url, params={**window, "plane": plane, "module": group["module"]})
                ).json()
                for field in ("known_cost_usd", "input_tokens", "output_tokens", "self_ms"):
                    assert sum(r[field] for r in detail["flow"]) == group[field]
                assert {r["module"] for r in detail["flow"]} == {group["module"]}
                assert detail["activity_total"] == group["spans"]
                assert sum(r["self_ms"] for r in detail["groups"]) == group["self_ms"]
                assert (
                    sum(r["known_cost_usd"] for r in detail["activity"]) == group["known_cost_usd"]
                )
                assert sum(r["self_ms"] for r in detail["activity"]) == group["self_ms"]
        params = {**window, "plane": "agents", "module": "agent:compiler", "limit": 1}
        first = (await api.get(url, params=params)).json()
        second = (await api.get(url, params={**params, "offset": 1})).json()
        # A previously started operation finishes after this snapshot was captured.
        async with session_factory() as session:
            session.add(
                Event(
                    **row("llm_run", start=86409000, agent="compiler", requests=1, **data),
                    process_id=process_id,
                    trace_id=uuid.uuid4().hex,
                    span_id=uuid.uuid4().hex[:16],
                )
            )
            await session.commit()
        frozen = (
            await api.get(url, params={**params, "offset": 1, "through_id": first["through_id"]})
        ).json()
        assert frozen["activity"] == second["activity"]
        assert frozen["totals"] == first["totals"]
        assert frozen["flow"] == first["flow"]
        refreshed = (await api.get(url, params=params)).json()
        assert refreshed["activity_total"] == 4
        assert first["activity_total"] == 3
        assert first["activity"][0]["id"] != second["activity"][0]["id"]
        assert first["totals"] == second["totals"]
        assert first["totals"]["p50_ms"] == 1000  # only the two timed spans
        assert first["totals"]["p95_ms"] == 1450
        assert {r["model"] for r in first["groups"]} == {"a", "b"}
        # A child outside the selected start-time window still consumes parent time.
        clipped = (
            await api.get(
                url,
                params={
                    **window,
                    "until": (START + timedelta(milliseconds=50)).isoformat(),
                    "plane": "ingestion",
                },
            )
        ).json()
        assert clipped["totals"]["self_ms"] == 200
        day_two = (
            await api.get(
                url,
                params={
                    **window,
                    "since": (START + timedelta(days=1)).isoformat(),
                    "plane": "agents",
                    "through_id": first["through_id"],
                },
            )
        ).json()
        assert day_two["totals"]["input_tokens"] == 40
        empty = (
            await api.get(url, params={**window, "since": (START + timedelta(days=2)).isoformat()})
        ).json()
        assert len(empty["groups"]) == 3 and all(r["spans"] == 0 for r in empty["groups"])
        assert empty["series"] == []
        assert empty["flow"] == []
        for params in (
            {"module": "agent:compiler"},
            {"since": "2026-01-01"},
            {"since": window["until"], "until": window["since"]},
            {"offset": -1},
        ):
            assert (await api.get(url, params=params)).status_code == 422
        assert (await api.get("/processes/999999999/metrics/breakdown")).status_code == 404


def test_reference_estimate_never_reprices_known_cost_or_cache_replay():
    data = dict(
        provider="helmcode",
        model="qwen3.6",
        input_tokens=1000,
        output_tokens=100,
        cached_tokens=100,
        network_attempted=True,
    )
    estimate = usage(row("provider_call", **data), 1)
    assert abs(estimate.estimated_cost_usd - 0.0001953) < 1e-12
    assert estimate.estimated_requests == estimate.unpriced_requests == 1
    assert estimate.known_cost_usd == 0
    known = usage(row("provider_call", **data, cost_status="known", cost_usd=0.3), 1)
    assert known.estimated_cost_usd == 0 and known.known_cost_usd == 0.3
    replay = usage(row("provider_call", **{**data, "network_attempted": False}), 1)
    assert replay.estimated_cost_usd == 0 and replay.estimated_requests == 0
    missing = usage(row("provider_call", provider="helmcode", network_attempted=True), 1)
    assert missing.estimated_requests == 0 and missing.unpriced_requests == 1
