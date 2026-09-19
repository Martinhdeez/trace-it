"""Connect PDF readers to stored process symbols and append-only source snapshots."""

import hashlib
import inspect
import io
import json
import time
import uuid

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.core.events import Event
from app.features.processes.model import Symbol
from app.features.sources.model import Source
from app.features.sources.service import current_loads

from .model import File, Instance
from .payment_verification import (
    PAYMENT_FIELDS,
    REQUIRED_PAYMENT_SYMBOLS,
    extract_for_payment,
    payment_symbols,
)
from .schemas import ExtractionResult


async def payment_state(session, process_id):
    definitions = list(await session.scalars(select(Symbol).where(Symbol.process_id == process_id)))
    names = {definition.name for definition in definitions}
    adapter = "invoice-payment" if names >= REQUIRED_PAYMENT_SYMBOLS else "generic"
    schema = [
        [row.name, row.type, row.description, row.required]
        for row in sorted(definitions, key=lambda row: row.name)
    ]
    code = (
        inspect.getsource(inspect.getmodule(payment_symbols))
        if adapter == "invoice-payment"
        else ""
    )
    schema_key = hashlib.sha256(
        json.dumps(
            [adapter, schema, PAYMENT_FIELDS, sorted(REQUIRED_PAYMENT_SYMBOLS), code],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    if not names >= REQUIRED_PAYMENT_SYMBOLS:
        return names, None, schema_key
    loads = await current_loads(session, process_id)
    current = {row.name: row for row in loads}
    return names, current, schema_key


async def payment_context(session, process_id):
    """Keep the source workbook adapter's existing two-value contract."""
    names, sources, _ = await payment_state(session, process_id)
    return names, sources


def source_ids(sources):
    return {name: source.id for name, source in sources.items()} if sources is not None else {}


async def equivalent_sources(session, recorded, current):
    """A new append-only snapshot with the same rows cannot change document symbols."""
    if recorded == current:
        return True
    if set(recorded) != set(current):
        return False
    previous = {
        row.id: row
        for row in await session.scalars(select(Source).where(Source.id.in_(recorded.values())))
    }
    latest = {
        row.id: row
        for row in await session.scalars(select(Source).where(Source.id.in_(current.values())))
    }
    return all(
        old_id in previous
        and new_id in latest
        and previous[old_id].name == latest[new_id].name == name
        and previous[old_id].process_id == latest[new_id].process_id
        and previous[old_id].rows == latest[new_id].rows
        for name, old_id in recorded.items()
        for new_id in (current[name],)
    )


async def latest_evidence(session, instance_id):
    return await session.scalar(
        select(Event)
        .where(
            Event.instance_id == instance_id,
            Event.step.in_(("ingest_document", "extract_document")),
        )
        .order_by(Event.id.desc())
        .limit(1)
    )


def reused_result(result, started):
    """Report work done by this request without changing append-only evidence."""
    reused = result.model_copy(deep=True)
    reused.cache_hit = True
    reused.metrics["request_ms"] = round((time.perf_counter() - started) * 1000, 2)
    for reader in ("ocr", "vlm", "jev"):
        reused.metrics[f"{reader}_calls_this_request"] = 0
        reused.metrics[f"{reader}_cache_hits_this_request"] = 0
    return reused


async def reusable_evidence(session, instance, service, item, options):
    """Return matching persisted evidence, or None when a pending reading is stale."""
    started = time.perf_counter()
    event = await latest_evidence(session, instance.id)
    if event is None:
        return None
    result = ExtractionResult.model_validate(event.data["extraction"])
    if instance.status == "DECIDED":
        return reused_result(result, started)
    _, sources, schema_key = await payment_state(session, instance.process_id)
    requested_key = service.cache_key(item, options)
    initial = event.data.get("initial_extraction", event.data["extraction"])
    transient_codes = {"OCR_ERROR", "VLM_ERROR", "JEV_ERROR", "FOCUSED_READER_ERROR"}
    if any(
        warning.get("code") in transient_codes
        for warning in result.warnings + initial.get("warnings", [])
    ):
        return None
    initial_key = initial.get("data", {}).get("provenance", {}).get("cache_key")
    if not (
        initial_key == requested_key
        and event.data.get("request_cache_key") == requested_key
        and event.data.get("schema_key") == schema_key
    ):
        return None
    if not await equivalent_sources(session, event.data.get("source_ids", {}), source_ids(sources)):
        return None
    return reused_result(result, started)


async def read_document(session, process_id, service, item, options):
    names, sources, schema_key = await payment_state(session, process_id)
    metadata = {
        "request_cache_key": service.cache_key(item, options),
        "schema_key": schema_key,
        "source_ids": source_ids(sources),
    }
    if sources is None:
        result = await run_in_threadpool(service.extract, item, options)
        return result, None, metadata
    reading = await run_in_threadpool(
        extract_for_payment,
        service,
        item,
        options,
        {name: source.rows for name, source in sources.items()},
    )
    context = {
        "adapter": "invoice-payment",
        **metadata,
        "rechecked_fields": reading.triggers,
        "initial_extraction_id": reading.initial.id,
    }
    if reading.initial.id != reading.result.id:
        context["initial_extraction"] = reading.initial.model_dump(mode="json")
    return reading.result, payment_symbols(reading.result, names), context


async def reextract_document(session, instance_id, user_id, service, options):
    # The decision run takes the same row lock before reading symbols. Neither
    # operation can change the evidence after the other has decided the instance.
    instance = await session.scalar(
        select(Instance).where(Instance.id == instance_id).with_for_update()
    )
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    if instance.status != "PENDING":
        raise ConflictError(
            "Only pending instances can be re-extracted; decision history is immutable"
        )
    links = {"process_id": instance.process_id, "instance_id": instance.id, "user_id": user_id}
    # One trace: the reading steps, then the `extract_document` point with the symbols.
    with events.span("reextract_document", **links):
        item = {
            "id": uuid.uuid4().hex,
            "file_id": instance.name,
            "sha256": instance.file_hash,
            "kind": "invoice",
        }
        existing = await reusable_evidence(session, instance, service, item, options)
        if existing is not None:
            return {
                "instance_id": instance.id,
                "process_id": instance.process_id,
                "name": instance.name,
                "file_hash": instance.file_hash,
                "status": instance.status,
                "created": False,
                "extraction": existing,
                "symbols": instance.symbols,
            }
        previous = await latest_evidence(session, instance.id)
        if not (service.objects / instance.file_hash).exists():
            original = await session.get(File, instance.file_hash)
            item = await run_in_threadpool(
                service.ingest, io.BytesIO(original.content), instance.name
            )
        result, symbols, context = await read_document(
            session, instance.process_id, service, item, options
        )
        if symbols is not None:
            instance.symbols = symbols
        elif previous is not None and previous.data.get("adapter") == "invoice-payment":
            instance.symbols = None
        events.record(
            session,
            "extract_document",
            process_id=instance.process_id,
            instance_id=instance.id,
            data={
                "user_id": user_id,
                "extraction": result.model_dump(mode="json"),
                "symbols": symbols,
                **context,
            },
            duration_ms=round(result.metrics.get("extraction_ms", 0)),
        )
        await session.commit()
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
