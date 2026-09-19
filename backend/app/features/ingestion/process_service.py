"""Persist document evidence using dev's existing files, instances and trace contracts."""

import hashlib

from sqlalchemy import or_, select, text
from sqlalchemy.dialects.postgresql import insert

from app.common.exceptions import NotFoundError
from app.core import events
from app.core.events import Event
from app.features.processes.model import Process

from .model import File, Instance
from .process_extraction import name_symbols, reusable_evidence
from .schemas import ExtractionResult


async def require_process(session, process_id):
    if await session.get(Process, process_id) is None:
        raise NotFoundError(f"Process {process_id} does not exist")


async def existing_document(session, process_id, item, service, options):
    """Serialize duplicate uploads, then inspect immutable or reusable evidence."""
    identity = f"{process_id}\0{item['file_id']}\0{item['sha256']}".encode()
    lock_key = int.from_bytes(hashlib.sha256(identity).digest()[:8], "big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    instance = await session.scalar(
        select(Instance)
        .where(
            Instance.process_id == process_id,
            Instance.name == item["file_id"],
            Instance.file_hash == item["sha256"],
        )
        .with_for_update()
    )
    if instance is None:
        return None, None
    result = await reusable_evidence(session, instance, service, item, options)
    return instance, result


def stored_upload(instance, result):
    return {
        "instance_id": instance.id,
        "process_id": instance.process_id,
        "name": instance.name,
        "file_hash": instance.file_hash,
        "status": instance.status,
        "created": False,
        "extraction": result,
        "symbols": instance.symbols,
    }


async def attach_document(
    session, process_id, user_id, content, result, symbols=None, context=None
):
    from app.features.versions.service import lock

    await lock(session, process_id)
    text = result.text
    await session.execute(
        insert(File)
        .values(hash=result.sha256, name=result.file_id, content=content, text=text or None)
        .on_conflict_do_nothing(index_elements=[File.hash])
    )
    # Missing or uncertain readings do not decide the workflow: the instance stays
    # PENDING until symbol extraction fills it and the rules decide it.
    statement = (
        insert(Instance)
        .values(
            process_id=process_id,
            file_hash=result.sha256,
            name=result.file_id,
            status="PENDING",
            symbols=symbols,
        )
        .on_conflict_do_nothing(
            index_elements=[Instance.process_id, Instance.name, Instance.file_hash]
        )
        .returning(Instance.id)
    )
    created_id = await session.scalar(statement)
    instance = await session.scalar(
        select(Instance).where(
            Instance.process_id == process_id,
            Instance.name == result.file_id,
            Instance.file_hash == result.sha256,
        )
    )
    # Re-uploading never resets an existing instance or edits its decision history.
    events.record(
        session,
        "ingest_document",
        process_id=process_id,
        instance_id=instance.id,
        data={
            "user_id": user_id,
            "created": created_id is not None,
            "extraction": result.model_dump(mode="json"),
            "symbols": symbols,
            **(context or {}),
        },
        duration_ms=round(result.metrics.get("extraction_ms", 0)),
    )
    await session.commit()
    return {
        "instance_id": instance.id,
        "process_id": process_id,
        "name": instance.name,
        "file_hash": instance.file_hash,
        "status": instance.status,
        "created": created_id is not None,
        "extraction": result,
        "symbols": instance.symbols,
    }


async def document_result(session, instance_id):
    event = await document_event(session, instance_id)
    return name_symbols(ExtractionResult.model_validate(event.data["extraction"]), event.data)


async def document_event(session, instance_id):
    """The persisted reading and adapter that supplied this instance's symbols."""
    if await session.get(Instance, instance_id) is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    event = await session.scalar(
        select(Event)
        .where(
            Event.instance_id == instance_id,
            Event.step.in_(("ingest_document", "extract_document")),
            # A duplicate upload is audited, but never changes the instance's
            # symbols. Its attempted reading must not replace attached evidence.
            # Older ingestion events without `created` remain readable.
            or_(Event.step == "extract_document", Event.data["created"].as_boolean().is_not(False)),
        )
        .order_by(Event.id.desc())
        .limit(1)
    )
    if event is None:
        raise NotFoundError("No document extraction is recorded for this instance")
    return event


async def document_content(session, instance_id) -> tuple[str, bytes]:
    """The file an instance was made from, byte for byte, with its name."""
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    file = await session.get(File, instance.file_hash)
    return instance.name, file.content
