"""Idempotent production demo data bootstrap."""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import session_factory
from app.features.decisions import service as decisions
from app.features.ingestion.model import File, Instance
from app.features.processes.definition import load_pack
from app.features.processes.model import Process
from app.features.versions import service as versions


class SeedInstance(BaseModel):
    name: str
    symbols: dict[str, str | int | float | bool | None]


async def seed_hiring_case(pack: Path) -> tuple[int, int]:
    """Install and decide the hiring demo once, without changing an existing process."""
    process_name = json.loads(pack.read_text(encoding="utf-8"))["name"]
    async with session_factory() as session:
        process = await session.scalar(select(Process).where(Process.name == process_name))
        process_id = process.id if process is not None else None
        published = process is not None and process.active_version_id is not None

    if not published:
        # load_pack commits. A later retry can safely resume its unpublished pack draft.
        async with session_factory() as session:
            result = await load_pack(session, pack)
            process_id = result.process.id
            if await versions.active(session, process_id, required=False) is None:
                draft = await versions.validate(session, process_id)
                await versions.publish(
                    session,
                    process_id,
                    draft.revision,
                    draft.validation["hash"],
                    "Production seed",
                    "Initial hiring case seed",
                )

    rows = [
        SeedInstance.model_validate(row)
        for row in json.loads((pack.with_suffix("") / "seed.json").read_text(encoding="utf-8"))
    ]
    async with session_factory() as session:
        assert process_id is not None
        existing = set(
            await session.scalars(select(Instance.name).where(Instance.process_id == process_id))
        )
        for row in rows:
            if row.name in existing:
                continue
            content = json.dumps(row.symbols, sort_keys=True).encode()
            digest = hashlib.sha256(content).hexdigest()
            if await session.get(File, digest) is None:
                session.add(
                    File(hash=digest, name=row.name, content=content, text=content.decode())
                )
            session.add(
                Instance(
                    process_id=process_id,
                    file_hash=digest,
                    name=row.name,
                    symbols={
                        name: {"value": value, "origin": "seed"}
                        for name, value in row.symbols.items()
                    },
                )
            )
        await session.commit()
        summary = await decisions.run(session, process_id)
        return process_id, summary.decided
