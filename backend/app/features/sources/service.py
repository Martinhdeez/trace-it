"""Sync an HTTP source into a new snapshot, and compare snapshots.

A sync downloads everything first and writes one `Source` row only if the download is
complete; a failed sync leaves the previous snapshot current and records why.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError, TraceError
from app.core import events
from app.core.config import settings
from app.features.processes.model import Process
from app.features.sources.http_connector import (
    HttpConnector,
    HttpSourceConfig,
    SourcesFile,
    SyncError,
)
from app.features.sources.model import Source


class SourceUnavailableError(TraceError):
    status_code = 502
    code = "source_unavailable"


class Diff(BaseModel):
    previous_id: int | None
    current_id: int | None
    added: list[str] = []
    removed: list[str] = []
    changed: dict[str, dict[str, list[Any]]] = {}  # key -> field -> [before, after]

    def summary(self) -> dict[str, int]:
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "changed": len(self.changed),
        }


class SyncResult(BaseModel):
    source_id: int
    origin: str
    rows: int
    rows_hash: str
    stats: dict[str, Any]
    diff: Diff


class SourceOut(BaseModel):
    id: int
    name: str
    origin: str
    rows: int
    loaded_at: datetime


class SourceDetail(SourceOut):
    data: list[dict[str, Any]]  # the rows of this load, as the rules see them


async def current_loads(session: AsyncSession, process_id: int) -> list[Source]:
    """The latest load of each source, in order of first appearance. Every load is kept;
    only the last one per name is current."""
    loads = await session.scalars(
        select(Source).where(Source.process_id == process_id).order_by(Source.id)
    )
    current: dict[str, Source] = {}
    for load in loads:
        current[load.name] = load
    return list(current.values())


def _out(load: Source) -> SourceOut:
    return SourceOut(
        id=load.id,
        name=load.name,
        origin=load.origin,
        rows=len(load.rows),
        loaded_at=load.loaded_at,
    )


async def list_sources(session: AsyncSession, process_id: int) -> list[SourceOut]:
    if await session.get(Process, process_id) is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    return [_out(load) for load in await current_loads(session, process_id)]


async def get_source(session: AsyncSession, process_id: int, name: str) -> SourceDetail:
    """The current load of one source, rows included."""
    if await session.get(Process, process_id) is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    load = await session.scalar(
        select(Source)
        .where(Source.process_id == process_id, Source.name == name)
        .order_by(Source.id.desc())
        .limit(1)
    )
    if load is None:
        raise NotFoundError(f"Process {process_id} has no load of source {name!r}")
    return SourceDetail(**_out(load).model_dump(), data=load.rows)


def pack_sources_file(pack_file: Path) -> Path:
    """`processes/invoice-payment.json` keeps its sources in `processes/invoice-payment/`."""
    return pack_file.with_suffix("") / "sources.json"


def find_pack(process_name: str) -> Path:
    for pack in sorted(settings.processes_dir.glob("*.json")):
        try:
            if json.loads(pack.read_text(encoding="utf-8")).get("name") == process_name:
                return pack
        except (json.JSONDecodeError, AttributeError):
            continue
    raise NotFoundError(f"No process pack in {settings.processes_dir} is named {process_name!r}")


def load_config(sources_file: Path, source_name: str) -> HttpSourceConfig:
    """Read on every sync, so a changed limit or timeout applies without a restart."""
    if not sources_file.is_file():
        raise NotFoundError(f"{sources_file} does not exist")
    try:
        sources = SourcesFile.model_validate_json(sources_file.read_text(encoding="utf-8"))
    except ValidationError as e:
        raise SourceUnavailableError(f"{sources_file}: invalid configuration\n{e}") from e
    if source_name not in sources.sources:
        raise NotFoundError(f"{sources_file} does not declare the source {source_name!r}")
    return sources.sources[source_name]


def rows_hash(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def diff_rows(
    before: list[dict[str, Any]], after: list[dict[str, Any]], key: str
) -> tuple[list[str], list[str], dict[str, dict[str, list[Any]]]]:
    old = {str(r.get(key)): r for r in before}
    new = {str(r.get(key)): r for r in after}
    changed = {}
    for k in sorted(old.keys() & new.keys()):
        fields = {
            f: [old[k].get(f), new[k].get(f)]
            for f in sorted(old[k].keys() | new[k].keys())
            if old[k].get(f) != new[k].get(f)
        }
        if fields:
            changed[k] = fields
    return sorted(new.keys() - old.keys()), sorted(old.keys() - new.keys()), changed


async def diff_latest(session: AsyncSession, process_id: int, name: str, key: str) -> Diff:
    """The latest snapshot of a source against the one before it."""
    last_two = list(
        await session.scalars(
            select(Source)
            .where(Source.process_id == process_id, Source.name == name)
            .order_by(Source.id.desc())
            .limit(2)
        )
    )
    current = last_two[0] if last_two else None
    previous = last_two[1] if len(last_two) > 1 else None
    added, removed, changed = diff_rows(
        previous.rows if previous else [], current.rows if current else [], key
    )
    return Diff(
        previous_id=previous.id if previous else None,
        current_id=current.id if current else None,
        added=added,
        removed=removed,
        changed=changed,
    )


async def sync(
    session: AsyncSession,
    process_id: int,
    name: str,
    config: HttpSourceConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SyncResult:
    if await session.get(Process, process_id) is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    connector = HttpConnector(config, transport)
    started = datetime.now(UTC)
    # The connector's stats (requests, retries, 429s, logins, pages) go on the span.
    with events.span("sync_source", process_id=process_id, source=name) as span:
        try:
            rows = await connector.download()
        except SyncError as e:
            span.set(**connector.stats.__dict__)
            raise SourceUnavailableError(
                f"Sync of {name!r} failed; the previous snapshot stays current. {e}"
            ) from e

        origin = f"{name}:{started.isoformat(timespec='seconds')}|{connector.base_url}"
        digest = rows_hash(rows)
        source = Source(process_id=process_id, name=name, origin=origin, rows=rows)
        session.add(source)
        await session.flush()
        diff = await diff_latest(session, process_id, name, config.key)
        stats = connector.stats.__dict__
        span.set(
            source_id=source.id,
            origin=origin,
            rows=len(rows),
            rows_hash=digest,
            diff=diff.summary(),
            **stats,
        )
        await session.commit()
    return SyncResult(
        source_id=source.id,
        origin=origin,
        rows=len(rows),
        rows_hash=digest,
        stats=stats,
        diff=diff,
    )


async def sync_process(session: AsyncSession, process_id: int, name: str) -> SyncResult:
    process = await session.get(Process, process_id)
    if process is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    config = load_config(pack_sources_file(find_pack(process.name)), name)
    return await sync(session, process_id, name, config)
