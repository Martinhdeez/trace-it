"""Stale decision alerts (ADR 0026): after a source changes or a new process version is
published, decide the past again in dry run and flag every decision that would change.

Detection reuses `reprocess(dry_run=True)`, so it never writes a decision: the manager
acts on an alert through `resolve` or `reprocess`, and that later decision resolves it.
Detection runs after the triggering change has committed, in its own session, and a
failure is recorded on its span without undoing the sync or the publication.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.core.database import session_factory
from app.features.alerts.model import Alert
from app.features.alerts.schemas import AlertOut
from app.features.decisions.model import Decision
from app.features.ingestion.model import Instance
from app.features.ingestion.symbols import flatten_symbols
from app.features.sources.model import Source
from app.features.users.model import User
from app.features.versions.model import ProcessVersion

log = logging.getLogger(__name__)

# The latest decision after the flagged one: set once the manager has acted.
_resolved_by = (
    select(func.max(Decision.id))
    .where(Decision.instance_id == Alert.instance_id, Decision.id > Alert.decision_id)
    .correlate(Alert)
    .scalar_subquery()
)


def _changed_rows(old: list[dict], new: list[dict]) -> tuple[list[dict], list[dict]]:
    """Rows only in the previous load, rows only in the new one. Keyless, so it serves
    every source (the ERP, workbook tables, parameters)."""
    before = {json.dumps(r, sort_keys=True) for r in old}
    after = {json.dumps(r, sort_keys=True) for r in new}
    return (
        [r for r in old if json.dumps(r, sort_keys=True) not in after],
        [r for r in new if json.dumps(r, sort_keys=True) not in before],
    )


def _involved(rows: list[dict], symbols: dict | None) -> list[dict]:
    """The changed rows that share a value with the instance (its order, NIF, IBAN...)."""
    values = {str(v) for v in flatten_symbols(symbols or {}).values() if v not in (None, "")}
    return [r for r in rows if values & {str(v) for v in r.values()}]


async def after_source_load(process_id: int, names: list[str]) -> list[int]:
    """After a sync or upload of `names`: detect, if any of them changed rows."""
    async with session_factory() as session:
        changed = []
        for name in names:
            current, *previous = await session.scalars(
                select(Source)
                .where(Source.process_id == process_id, Source.name == name)
                .order_by(Source.id.desc())
                .limit(2)
            )
            if not previous:  # a first load changes nothing already decided
                continue
            gone, new = _changed_rows(previous[0].rows, current.rows)
            if gone or new:
                changed.append(
                    {
                        "name": name,
                        "source_id": current.id,
                        "previous_id": previous[0].id,
                        "before": gone,
                        "after": new,
                    }
                )
    if not changed:
        return []
    return await detect(process_id, {"kind": "source_sync", "sources": changed})


async def after_publish(process_id: int, version_id: int) -> list[int]:
    """After a process version is published: which rules came, went or changed."""
    async with session_factory() as session:
        version = await session.get(ProcessVersion, version_id)
        if version.parent_id is None:  # the first version: nothing was decided before it
            return []
        parent = await session.get(ProcessVersion, version.parent_id)
    new = {r["id"]: r["hash"] for r in version.snapshot["rules"]}
    old = {r["id"]: r["hash"] for r in parent.snapshot["rules"]}
    trigger = {
        "kind": "rule_change",
        "version_id": version.id,
        "version": version.number,
        "added_rule_ids": sorted(new.keys() - old.keys()),
        "removed_rule_ids": sorted(old.keys() - new.keys()),
        "changed_rule_ids": sorted(k for k in new.keys() & old.keys() if new[k] != old[k]),
    }
    return await detect(process_id, trigger)


async def detect(process_id: int, trigger: dict[str, Any]) -> list[int]:
    """Dry-run the decided instances and open one alert per decision that would change.
    Returns the ids of the alerts created (an alert already open for the same decision
    and outcome is not created again)."""
    try:
        with events.span(
            "detect_stale_decisions", process_id=process_id, trigger=trigger["kind"]
        ) as span:
            async with session_factory() as session:
                return await _detect(session, process_id, trigger, span)
    except Exception:  # noqa: BLE001 - the sync or publication is already committed
        log.exception("Stale decision detection failed for process %s", process_id)
        return []


async def _detect(session: AsyncSession, process_id: int, trigger: dict, span) -> list[int]:
    from app.features.decisions import service as decisions
    from app.features.versions import service as versions

    if await versions.active(session, process_id, required=False) is None:
        return []
    dry = await decisions.reprocess(session, process_id, None, dry_run=True)
    default = (await decisions.outcomes(session, process_id)).default
    source_sync = trigger["kind"] == "source_sync"
    # New data behind a decision to pay usually records that payment (the ERP now says
    # PAGADA): the decision was right. Held back or escalated ones are what new data unlocks.
    flips = [c for c in [*dry.changes, *dry.conflicts] if not (source_sync and c.before == default)]
    instances = {
        i.id: i
        for i in await session.scalars(
            select(Instance).where(Instance.id.in_([c.instance_id for c in flips]))
        )
    }
    latest = await decisions.latest_decisions(session, list(instances.values()))
    summary = {k: v for k, v in trigger.items() if k != "sources"}
    if source_sync:
        summary["sources"] = [
            {k: s[k] for k in ("name", "source_id", "previous_id")}
            | {"rows_removed": len(s["before"]), "rows_added": len(s["after"])}
            for s in trigger["sources"]
        ]
    rows = []
    for change in flips:
        previous = latest[change.instance_id]
        symbols = instances[change.instance_id].symbols
        own = dict(summary)
        if source_sync:
            own["rows"] = {
                "before": [r for s in trigger["sources"] for r in _involved(s["before"], symbols)],
                "after": [r for s in trigger["sources"] for r in _involved(s["after"], symbols)],
            }
        rows.append(
            {
                "process_id": process_id,
                "instance_id": change.instance_id,
                "decision_id": previous.id,
                "before": change.before,
                "after": change.after,
                "trigger": own,
                "evidence": {
                    "before": {"author": previous.author, "reason": previous.reason},
                    "after": {"author": "engine", "reason": change.reason},
                },
                "status": "open",
            }
        )
    created = []
    if rows:
        created = list(
            await session.scalars(
                insert(Alert)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["decision_id", "after"])
                .returning(Alert.id)
            )
        )
        await session.commit()
    span.set(
        trigger=summary,
        instances=dry.unchanged + len(dry.changes) + len(dry.conflicts),
        would_change=len(dry.changes) + len(dry.conflicts),
        alerts_created=len(created),
        alert_ids=created,
    )
    return created


def _out(alert: Alert, name: str, resolved_by: int | None) -> AlertOut:
    derived = {
        "name": name,
        "resolved_by_decision_id": resolved_by,
        "status": "resolved" if resolved_by else alert.status,
    }
    stored = {k: getattr(alert, k) for k in AlertOut.model_fields if k not in derived}
    return AlertOut(**stored, **derived)


async def list_alerts(
    session: AsyncSession,
    process_id: int,
    status: str | None = None,
    instance_id: int | None = None,
) -> list[AlertOut]:
    from app.features.processes.service import get as get_process

    await get_process(session, process_id)
    rows = await session.execute(
        select(Alert, Instance.name, _resolved_by)
        .join(Instance, Instance.id == Alert.instance_id)
        .where(
            Alert.process_id == process_id,
            *([Alert.instance_id == instance_id] if instance_id is not None else []),
        )
        .order_by(Alert.id)
    )
    out = [_out(*row) for row in rows]
    return [a for a in out if status is None or a.status == status]


async def ack(session: AsyncSession, alert_id: int, note: str | None, user: User) -> AlertOut:
    alert = await session.get(Alert, alert_id, with_for_update=True)
    if alert is None:
        raise NotFoundError(f"Alert {alert_id} does not exist")
    with events.span(
        "ack_alert",
        process_id=alert.process_id,
        instance_id=alert.instance_id,
        alert_id=alert.id,
        author=user.name,
    ):
        if alert.status != "open":
            raise ConflictError(f"Alert {alert_id} was already acknowledged")
        alert.status = "acknowledged"
        alert.acknowledged_by = user.name
        alert.acknowledged_at = datetime.now(UTC)
        alert.note = note
        await session.commit()
    name = await session.scalar(select(Instance.name).where(Instance.id == alert.instance_id))
    resolved_by = await session.scalar(select(_resolved_by).where(Alert.id == alert.id))
    return _out(alert, name, resolved_by)


async def open_count(session: AsyncSession, process_id: int | None) -> int:
    """Alerts nobody has acknowledged or acted on yet."""
    query = (
        select(func.count())
        .select_from(Alert)
        .where(Alert.status == "open", _resolved_by.is_(None))
    )
    if process_id is not None:
        query = query.where(Alert.process_id == process_id)
    return await session.scalar(query)
