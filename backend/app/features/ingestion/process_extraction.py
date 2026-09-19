"""Connect PDF readers to stored process symbols and append-only source snapshots."""

import io
import uuid

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.processes.model import Symbol
from app.features.sources.service import current_loads

from .extraction_plan import load_extraction_plan
from .model import File, Instance
from .payment_verification import (
    PAYMENT_FIELDS,
    REQUIRED_PAYMENT_SYMBOLS,
    extract_for_payment,
    payment_symbols,
)


async def payment_context(session, process_id):
    names = set(await session.scalars(select(Symbol.name).where(Symbol.process_id == process_id)))
    if not names >= REQUIRED_PAYMENT_SYMBOLS:
        return names, None
    loads = await current_loads(session, process_id)
    current = {row.name: row for row in loads}
    return names, current


async def read_document(session, process_id, service, item, options):
    plan = await load_extraction_plan(session, process_id)
    names = {field.name for field in plan.fields}
    if not plan.fields:
        result = await run_in_threadpool(service.extract, item, options)
        return result, None, {}
    snapshot = {**plan.model_dump(mode="json"), "fingerprint": plan.fingerprint}
    if not names >= REQUIRED_PAYMENT_SYMBOLS:
        result = await run_in_threadpool(service.extract_schema, item, options, plan)
        return (
            result,
            schema_symbols(result, plan.fields),
            {
                "adapter": "schema",
                "extraction_plan": snapshot,
            },
        )
    sources = {row.name: row for row in await current_loads(session, process_id)}
    reading = await run_in_threadpool(
        extract_for_payment,
        service,
        item,
        options,
        {name: source.rows for name, source in sources.items()},
    )
    context = {
        "adapter": "invoice-payment",
        "source_ids": {name: source.id for name, source in sources.items()},
        "rechecked_fields": reading.triggers,
        "initial_extraction_id": reading.initial.id,
        "extraction_plan": snapshot,
    }
    if reading.initial.id != reading.result.id:
        context["initial_extraction"] = reading.initial.model_dump(mode="json")
    result = reading.result
    # Keep every legacy invoice field (including the unused issuer_name) unchanged.
    legacy = set(PAYMENT_FIELDS) | {"file_id", "free_text", "issuer_name"}
    extra = [field for field in plan.fields if field.name not in legacy]
    if extra:
        result = await run_in_threadpool(
            service.extract_schema,
            {**item, "id": uuid.uuid4().hex},
            options,
            plan,
            extra,
            result,
        )
        context["adapter"] = "invoice-payment+schema"
        context["base_extraction_id"] = reading.result.id
    symbols = payment_symbols(result, names)
    symbols.update(schema_symbols(result, extra))
    return result, symbols, context


def schema_symbols(result, fields):
    """Only accepted readings reach the engine; proposals remain in document evidence."""
    symbols = {}
    readings = result.data.get("schema_fields", {})
    for field in fields:
        value = readings.get(field.name, {}).get("value")
        if value is not None and field.type.lower() == "boolean":
            value = {"true": True, "false": False}.get(value)
        symbols[field.name] = {"value": value, "origin": f"document:{result.id}"}
    return symbols


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
        original = await session.get(File, instance.file_hash)
        item = await run_in_threadpool(service.ingest, io.BytesIO(original.content), instance.name)
        result, symbols, context = await read_document(
            session, instance.process_id, service, item, options
        )
        if symbols is not None:
            instance.symbols = symbols
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
