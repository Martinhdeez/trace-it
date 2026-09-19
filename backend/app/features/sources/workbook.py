"""Load invoice reference tables from the ingestion reader into immutable snapshots."""

from sqlalchemy.dialects.postgresql import insert

from app.common.exceptions import ConflictError
from app.core import events
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


async def load_workbook(session, process_id, user_id, result, content, cut_off_date=None):
    _, context = await payment_context(session, process_id)
    if context is None:
        raise ConflictError("This workbook adapter requires the invoice-payment symbol schema")
    tables = workbook_sources(result)
    if cut_off_date is not None:
        tables["parameters"] = [{"cut_off_date": cut_off_date.isoformat()}]
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
    return {
        "process_id": process_id,
        "file_hash": result.sha256,
        "extraction_id": result.id,
        "sources": loaded,
        "warnings": result.warnings,
    }
