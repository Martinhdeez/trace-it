"""Load invoice reference tables from the ingestion reader into immutable snapshots."""

import json

from sqlalchemy.dialects.postgresql import insert

from app.common.exceptions import ConflictError
from app.core import events
from app.core.config import settings
from app.features.ingestion.errors import InvalidDocumentError
from app.features.ingestion.model import File
from app.features.ingestion.process_extraction import payment_context

from .model import Source

TABLES = {
    "suppliers": (
        "suppliers",
        {
            "id": "supplier_ref",
            "company_name": "supplier_name",
            "nif": "supplier_tax_id",
            "iban": "authorized_iban",
        },
    ),
    "purchase_orders": (
        "orders",
        {
            "purchase_order": "purchase_order_ref",
            "supplier_id": "supplier_ref",
            "nif": "supplier_tax_id",
            "total_amount": "expected_gross_amount",
            "status": "state",
            "order_date": "ordered_on",
        },
    ),
}


def workbook_sources(result):
    tables = {"suppliers": [], "orders": []}
    for record in result.data.get("records", []):
        if record["role"] not in TABLES:
            continue
        name, mapping = TABLES[record["role"]]
        fields = record["fields"]
        row = {key: fields.get(field, {}).get("value") for key, field in mapping.items()}
        required = (
            ("id", "nif", "iban")
            if name == "suppliers"
            else (
                "purchase_order",
                "total_amount",
                "status",
            )
        )
        if any(row[key] is None for key in required) or (
            name == "orders" and not (row["nif"] or row["supplier_id"])
        ):
            raise InvalidDocumentError(
                f"Incomplete {name} row at {record['sheet']}!{record['row']}; no snapshots loaded"
            )
        tables[name].append(row)
    if not all(tables.values()):
        raise InvalidDocumentError("Workbook must contain supplier and purchase-order tables")
    return tables


def pack_rates():
    """The published exchange rates (`processes/invoice-payment/rates.json`): a reference
    table the manager keeps beside the workbook, loaded with it so that a rule converting a
    foreign invoice reads a published figure and never a live market. This adapter is the
    invoice pack's own (`payment_context` below), so it reads the invoice pack's file."""
    path = settings.processes_dir / "invoice-payment" / "rates.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


async def load_workbook(session, process_id, user_id, result, content, cut_off_date=None):
    from app.features.versions.service import lock

    await lock(session, process_id)
    _, context = await payment_context(session, process_id)
    if context is None:
        raise ConflictError("This workbook adapter requires the invoice-payment symbol schema")
    tables = workbook_sources(result)
    if cut_off_date is not None:
        tables["parameters"] = [{"cut_off_date": cut_off_date.isoformat()}]
    if rates := pack_rates():
        tables["rates"] = rates
    await session.execute(
        insert(File)
        .values(
            hash=result.sha256,
            name=result.file_id,
            content=content,
            text=None,
        )
        .on_conflict_do_nothing(index_elements=[File.hash])
    )
    sources = [
        Source(process_id=process_id, name=name, origin=result.sha256, rows=rows)
        for name, rows in tables.items()
    ]
    session.add_all(sources)
    await session.flush()
    loaded = [
        {"id": source.id, "name": source.name, "rows": len(source.rows)} for source in sources
    ]
    events.record(
        session,
        "load_workbook",
        process_id=process_id,
        data={
            "process_id": process_id,
            "user_id": user_id,
            "sources": loaded,
            "extraction": result.model_dump(mode="json"),
        },
    )
    await session.commit()
    from app.features.alerts.service import after_source_load

    await after_source_load(process_id, list(tables))
    return {
        "process_id": process_id,
        "file_hash": result.sha256,
        "extraction_id": result.id,
        "sources": loaded,
        "warnings": result.warnings,
    }
