"""Persist document evidence using dev's existing files, instances and trace contracts."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.common.exceptions import NotFoundError
from app.core import events
from app.core.events import Event
from app.features.processes.model import Process

from .model import File, Instance
from .schemas import ExtractionResult


async def require_process(session, process_id):
    if await session.get(Process, process_id) is None:
        raise NotFoundError(f"Process {process_id} does not exist")


async def attach_document(
    session, process_id, user_id, content, result, symbols=None, context=None
):
    await require_process(session, process_id)
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
        latency_ms=round(result.metrics.get("extraction_ms", 0)),
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
    if await session.get(Instance, instance_id) is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    event = await session.scalar(
        select(Event)
        .where(
            Event.instance_id == instance_id,
            Event.step.in_(("ingest_document", "extract_document")),
        )
        .order_by(Event.id.desc())
        .limit(1)
    )
    if event is None:
        raise NotFoundError("No document extraction is recorded for this instance")
    return ExtractionResult.model_validate(event.data["extraction"])


async def document_content(session, instance_id) -> tuple[str, bytes]:
    """The file an instance was made from, byte for byte, with its name."""
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    file = await session.get(File, instance.file_hash)
    return instance.name, file.content
