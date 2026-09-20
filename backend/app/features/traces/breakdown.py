"""Additive usage drill-down over the existing audit trail. No new instrumentation.

Money/tokens belong only to llm_run and network provider_call spans. Time is exclusive:
subtract the union of direct child intervals, including children in another plane or
outside the selected window. Concurrent operations accumulate work, not wall-clock time.
"""

import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import Event
from app.features.processes.service import get as get_process
from app.features.traces.schemas import (
    Plane,
    UsageActivity,
    UsageBreakdown,
    UsageBucket,
    UsageGroup,
    UsageTotals,
)
from app.features.traces.service import PLANES, _quantile

# Do not load model prompts, answers, document symbols or other large payloads.
FIELDS = (
    "agent",
    "role",
    "operation",
    "provider",
    "model",
    "network_attempted",
    "outcome",
    "requests",
    "input_tokens",
    "output_tokens",
    "cached_tokens",
    "cost_usd",
    "cost_status",
    "cached_replay",
)
ADDITIVE = tuple(k for k in UsageTotals.model_fields if k not in {"p50_ms", "p95_ms"})


def module_of(row: dict) -> str:
    data = row["data"]
    if row["step"] == "llm_run":
        return f"agent:{data.get('agent') or data.get('role') or 'unknown'}"
    if row["step"] == "provider_call":
        return f"provider:{data.get('operation') or 'unknown'}"
    return row["step"]


def self_ms(row: dict, children: list[dict]) -> float | None:
    if row["duration_ms"] is None:
        return None
    duration = max(0, row["duration_ms"])
    intervals = []
    for child in children:
        start = (child["started_at"] - row["started_at"]).total_seconds() * 1000
        end = min(duration, start + (child["duration_ms"] or 0))
        start = max(0, start)
        if end > start:
            intervals.append((start, end))
    covered, last = 0.0, 0.0
    for start, end in sorted(intervals):
        covered += max(0, end - max(start, last))
        last = max(last, end)
    return round(max(0, duration - covered), 3)


def usage(row: dict, own_ms: float | None) -> UsageTotals:
    data = row["data"]
    provider = row["step"] == "provider_call"
    billable = row["step"] == "llm_run" or (provider and data.get("network_attempted") is True)
    requests = (1 if provider else data.get("requests") or 0) if billable else 0
    priced = data.get("cost_status") in {"known", "included"}
    return UsageTotals(
        spans=1,
        imported_spans=int(data.get("cached_replay") is True),
        errors=int(row["status"] == "error"),
        requests=requests,
        replays=int(provider and data.get("outcome") == "replay"),
        input_tokens=(data.get("input_tokens") or 0) if billable else 0,
        output_tokens=(data.get("output_tokens") or 0) if billable else 0,
        cached_tokens=(data.get("cached_tokens") or 0) if billable else 0,
        known_cost_usd=(data.get("cost_usd") or 0) if billable and priced else 0,
        unpriced_requests=requests if not priced else 0,
        timed_spans=int(own_ms is not None),
        self_ms=own_ms or 0,
        p50_ms=row["duration_ms"],
        p95_ms=row["duration_ms"],
    )


def aggregate(items: list[UsageTotals]) -> dict[str, Any]:
    result = {key: sum(getattr(item, key) for item in items) for key in ADDITIVE}
    result["known_cost_usd"] = float(
        sum((Decimal(str(item.known_cost_usd)) for item in items), Decimal(0))
    )
    durations = sorted(item.p50_ms for item in items if item.p50_ms is not None)
    result["p50_ms"] = _quantile(durations, 0.5) if durations else None
    result["p95_ms"] = _quantile(durations, 0.95) if durations else None
    return result


async def breakdown(
    session: AsyncSession,
    process_id: int,
    plane: Plane | None = None,
    module: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    offset: int = 0,
    limit: int = 25,
    through_id: int | None = None,
) -> UsageBreakdown:
    await get_process(session, process_id)
    until = until or datetime.now(UTC)
    if through_id is None:
        through_id = await session.scalar(
            select(func.coalesce(func.max(Event.id), 0)).where(Event.process_id == process_id)
        )
    where = [Event.process_id == process_id, Event.started_at < until, Event.id <= through_id]
    if since is not None:
        where.append(Event.started_at >= since)
    if plane is not None:
        where.append(Event.step.in_([s for s, p in PLANES.items() if p == plane]))
    # A single snapshot feeds totals, models, time buckets and the paginated activity.
    data = func.jsonb_build_object(*[v for key in FIELDS for v in (key, Event.data[key])])
    query = (
        select(
            Event.id,
            Event.span_id,
            Event.trace_id,
            Event.step,
            Event.status,
            Event.started_at,
            Event.duration_ms,
            Event.rule_id,
            Event.instance_id,
            data.label("data"),
        )
        .where(*where)
        .order_by(Event.started_at.desc(), Event.id.desc())
    )
    rows = [dict(row) for row in (await session.execute(query)).mappings()]
    if module is not None:
        rows = [row for row in rows if module_of(row) == module]

    # Query children independently of plane/time filters. Cross-plane children still
    # consume parent time. A subquery avoids an unbounded list of SQL bind parameters.
    children: dict[str, list[dict]] = defaultdict(list)
    for child in (
        await session.execute(
            select(Event.parent_id, Event.started_at, Event.duration_ms).where(
                Event.parent_id.in_(select(Event.span_id).where(*where)),
                Event.duration_ms.is_not(None),
                Event.id <= through_id,
            )
        )
    ).mappings():
        children[child["parent_id"]].append(dict(child))

    first = since or min((row["started_at"] for row in rows), default=until)
    seconds = max(0, (until - first).total_seconds())
    # At most ~90 buckets for long histories; one-hour buckets for a day.
    bucket_seconds = 3600 if seconds <= 86400 else 86400 * max(1, math.ceil(seconds / 86400 / 90))
    grouped: dict[tuple, list[UsageTotals]] = defaultdict(list)
    flow: dict[tuple, list[UsageTotals]] = defaultdict(list)
    timeline: dict[tuple, list[UsageTotals]] = defaultdict(list)
    totals = []
    activity = []
    for index, row in enumerate(rows):
        row_plane = PLANES.get(row["step"])
        if row_plane is None:
            continue
        item = usage(row, self_ms(row, children[row["span_id"]]))
        totals.append(item)
        data = row["data"]
        flow[(row_plane, module_of(row), data.get("provider"), data.get("model"))].append(item)
        if plane is None:
            group = (row_plane, None, None, None)
        elif module is None:
            group = (row_plane, module_of(row), None, None)
        else:
            group = (row_plane, module, data.get("provider"), data.get("model"))
        grouped[group].append(item)
        start = datetime.fromtimestamp(
            int(row["started_at"].timestamp()) // bucket_seconds * bucket_seconds, UTC
        )
        timeline[(start, row_plane)].append(item)
        if module is not None and offset <= index < offset + limit:
            activity.append(
                UsageActivity(
                    **item.model_dump(),
                    **{
                        key: row[key]
                        for key in (
                            "id",
                            "span_id",
                            "trace_id",
                            "step",
                            "status",
                            "started_at",
                            "duration_ms",
                            "rule_id",
                            "instance_id",
                        )
                    },
                    model=data.get("model"),
                    provider=data.get("provider"),
                    cost_status=data.get("cost_status"),
                )
            )
    groups = [
        UsageGroup(
            key=p.value
            if plane is None
            else m
            if module is None
            else json.dumps([provider, model]),
            plane=p,
            module=m,
            provider=provider,
            model=model,
            **aggregate(items),
        )
        for (p, m, provider, model), items in grouped.items()
    ]
    if plane is None:
        present = {g.plane for g in groups}
        groups.extend(UsageGroup(key=p.value, plane=p) for p in Plane if p not in present)
    return UsageBreakdown(
        process_id=process_id,
        through_id=through_id,
        plane=plane,
        module=module,
        since=since,
        until=until,
        bucket_seconds=bucket_seconds,
        totals=UsageTotals(**aggregate(totals)) if plane is not None else None,
        groups=sorted(groups, key=lambda g: g.key),
        flow=[
            UsageGroup(
                key=json.dumps([p, m, provider, model]),
                plane=p,
                module=m,
                provider=provider,
                model=model,
                **aggregate(items),
            )
            for (p, m, provider, model), items in sorted(
                flow.items(), key=lambda entry: json.dumps(entry[0])
            )
        ],
        series=[
            UsageBucket(started_at=start, plane=p, **aggregate(items))
            for (start, p), items in sorted(timeline.items())
        ],
        activity=activity,
        activity_total=len(rows) if module else 0,
        offset=offset,
        limit=limit,
    )
