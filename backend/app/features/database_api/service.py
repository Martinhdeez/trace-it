"""Bounded, parameterized access to registered Trace-it tables in public only.

No SQL from a caller is executed. Names resolve through application metadata and live
reflection; values are bound parameters. Writes and their audit record are one transaction.
"""

import base64
import hashlib
import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import JSON, LargeBinary, MetaData, Table, and_, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_auth import API_USER_EMAIL
from app.core.api_boundary import database_values
from app.features.database_api.model import DatabaseApiChange
from app.features.database_api.schemas import DatabaseRow, DatabaseRows
from app.models import Base

READ_ONLY = {"database_api_changes", "events", "mail_activity"}


def encode(value: Any) -> Any:
    """Lossless JSON representation, including PostgreSQL bytea and numeric values."""
    if isinstance(value, bytes | memoryview):
        return {"$base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Decimal | UUID):
        return str(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [encode(v) for v in value]
    return value


def names() -> list[str]:
    return sorted(t.name for t in Base.metadata.tables.values() if t.schema in (None, "public"))


async def table(session: AsyncSession, name: str, *, write: bool = False) -> Table:
    if name not in names():
        raise HTTPException(404, "Unknown application table")
    if write and name in READ_ONLY:
        raise HTTPException(403, "Audit tables are read-only")
    # Apply transaction-local limits, also bounding lock waits during mutations.
    await session.execute(text("SET LOCAL statement_timeout = '10s'"))
    await session.execute(text("SET LOCAL lock_timeout = '3s'"))
    connection = await session.connection()
    result = await connection.run_sync(
        lambda conn: Table(name, MetaData(), schema="public", autoload_with=conn, resolve_fks=False)
    )
    if not result.primary_key.columns:
        raise HTTPException(409, "Table has no primary key")
    return result


async def schema(session: AsyncSession, name: str) -> dict:
    target = await table(session, name)
    connection = await session.connection()

    def describe(conn):
        inspector = inspect(conn)
        return {
            "name": name,
            "primary_key": [c.name for c in target.primary_key],
            "writable": name not in READ_ONLY,
            "columns": [
                {
                    "name": c.name,
                    "type": str(c.type),
                    "nullable": c.nullable,
                    "primary_key": c.primary_key,
                    "default": str(c.server_default.arg)
                    if c.server_default is not None and hasattr(c.server_default, "arg")
                    else None,
                    "generated": c.identity is not None
                    or c.computed is not None
                    or c is target.autoincrement_column,
                }
                for c in target.columns
            ],
            "foreign_keys": inspector.get_foreign_keys(name, schema="public"),
            "unique_constraints": inspector.get_unique_constraints(name, schema="public"),
            "check_constraints": inspector.get_check_constraints(name, schema="public"),
            "indexes": inspector.get_indexes(name, schema="public"),
        }

    return await connection.run_sync(describe)


def object_parameter(raw: str | None) -> dict:
    if raw is None:
        return {}
    try:
        value = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, "Expected a JSON object") from exc
    if not isinstance(value, dict):
        raise HTTPException(422, "Expected a JSON object")
    return value


def values(target: Table, supplied: dict) -> dict:
    if set(supplied) - set(target.c.keys()):
        raise HTTPException(422, "Unknown column")
    result = {}
    for name, value in supplied.items():
        column = target.c[name]
        if value is None:
            result[name] = None
            continue
        try:
            if isinstance(column.type, LargeBinary):
                if not isinstance(value, dict) or set(value) != {"$base64"}:
                    raise ValueError("Binary columns require a $base64 object")
                result[name] = base64.b64decode(value["$base64"], validate=True)
            elif isinstance(column.type, JSON):
                result[name] = value
            else:
                result[name] = TypeAdapter(column.type.python_type).validate_python(value)
        except (ValueError, TypeError, ValidationError, NotImplementedError) as exc:
            raise HTTPException(422, f"Invalid value for column {name}") from exc
    return result


def key_values(target: Table, key: dict) -> dict:
    if set(key) != {c.name for c in target.primary_key} or any(v is None for v in key.values()):
        raise HTTPException(422, "Supply exactly the complete, non-null primary key")
    return values(target, key)


def predicate(target: Table, supplied: dict):
    return and_(True, *(target.c[k] == v for k, v in supplied.items()))


def row(target: Table, data: dict) -> DatabaseRow:
    encoded = encode(data)
    digest = hashlib.sha256(
        json.dumps(encoded, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return DatabaseRow(
        key={c.name: encoded[c.name] for c in target.primary_key}, values=encoded, etag=digest
    )


async def rows(
    session: AsyncSession, name: str, filters: dict, limit: int, offset: int
) -> DatabaseRows:
    target = await table(session, name)
    statement = (
        select(target)
        .where(predicate(target, values(target, filters)))
        .order_by(*target.primary_key.columns)
        .offset(offset)
        .limit(limit + 1)
    )
    result = await session.stream(statement.execution_options(yield_per=1))
    items = []
    size = 0
    more = False
    try:
        async for item in result.mappings():
            if len(items) == limit:
                more = True
                break
            encoded = row(target, dict(item))
            size += len(encoded.model_dump_json().encode())
            if size > 48 * 1024 * 1024:
                if not items:
                    raise HTTPException(413, "Row exceeds the 48 MiB response limit")
                more = True
                break
            items.append(encoded)
    finally:
        await result.close()
    return DatabaseRows(
        rows=items,
        limit=limit,
        offset=offset,
        next_offset=offset + len(items) if more else None,
    )


async def one(session: AsyncSession, name: str, key: dict) -> DatabaseRow:
    target = await table(session, name)
    result = (
        (await session.execute(select(target).where(predicate(target, key_values(target, key)))))
        .mappings()
        .one_or_none()
    )
    if result is None:
        raise HTTPException(404, "Row not found")
    return row(target, dict(result))


async def mutate(
    session: AsyncSession,
    name: str,
    operation: str,
    supplied: dict,
    reason: str,
    key: dict | None = None,
    expected_etag: str | None = None,
) -> dict:
    target = await table(session, name, write=True)
    try:
        database_values(supplied)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    converted = values(target, supplied)
    before = None
    if operation != "insert":
        match = predicate(target, key_values(target, key or {}))
        previous = (
            (await session.execute(select(target).where(match).with_for_update()))
            .mappings()
            .one_or_none()
        )
        if previous is None:
            raise HTTPException(404, "Row not found")
        before = row(target, dict(previous))
        if before.etag != expected_etag:
            raise HTTPException(409, "Row changed; read it again before retrying")
        if name == "users" and previous["email"] == API_USER_EMAIL:
            raise HTTPException(403, "The API manager is reserved")
        if set(converted) & {c.name for c in target.primary_key}:
            raise HTTPException(422, "Primary keys cannot be updated")
    if name == "users" and converted.get("email") == API_USER_EMAIL:
        raise HTTPException(403, "The API manager email is reserved")
    for column in target.columns:
        if column.name in converted and (
            column.computed is not None
            or column.identity is not None
            or (operation == "insert" and column is target.autoincrement_column)
        ):
            raise HTTPException(422, "Generated columns must be omitted")
    if operation == "insert":
        statement = target.insert().values(**converted).returning(target)
    elif operation == "update":
        statement = target.update().where(match).values(**converted).returning(target)
    else:
        statement = target.delete().where(match).returning(target)
    result = row(target, dict((await session.execute(statement)).mappings().one()))
    change = DatabaseApiChange(
        table_name=name,
        operation=operation,
        key=result.key,
        before=before.values if before else None,
        after=result.values if operation != "delete" else None,
        reason=reason,
        actor=API_USER_EMAIL,
    )
    session.add(change)
    await session.flush()
    change_id = change.id
    await session.commit()
    return {**result.model_dump(), "change_id": change_id}
