"""The database API is part of the same OpenAPI contract as the business endpoints."""

import json
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.routing import APIRoute
from sqlalchemy.exc import DBAPIError, IntegrityError, StatementError

from app.core.api_auth import require_bearer
from app.core.database import Session
from app.features.database_api import service
from app.features.database_api.schemas import (
    DatabaseCreate,
    DatabaseDelete,
    DatabaseRow,
    DatabaseRows,
    DatabaseSchema,
    DatabaseTable,
    DatabaseUpdate,
    DatabaseWriteResult,
)


class DatabaseRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def guarded(request: Request) -> Response:
            # Authentication runs before parsing any body, including malformed JSON.
            from app.core.api_auth import bearer, bearer_identity

            require_bearer(bearer_identity(request, await bearer(request)))
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > 2 * 1024 * 1024:
                    raise HTTPException(413, "Database API body limit is 2 MiB")
                chunks.append(chunk)
            # Cache the bounded body for FastAPI's subsequent JSON parsing.
            request._body = b"".join(chunks)
            try:
                response = await handler(request)
            except IntegrityError as exc:
                raise HTTPException(409, "Database constraint conflict") from exc
            except DBAPIError as exc:
                code = getattr(exc.orig, "sqlstate", "") or ""
                if code.startswith("22"):
                    raise HTTPException(422, "Invalid database value") from exc
                if code.startswith("23"):
                    raise HTTPException(409, "Database constraint conflict") from exc
                raise HTTPException(503, "Database operation unavailable or timed out") from exc
            except StatementError as exc:
                raise HTTPException(422, "Invalid database value") from exc
            response.headers["Cache-Control"] = "no-store"
            return response

        return guarded


router = APIRouter(
    prefix="/db",
    tags=["database administration"],
    dependencies=[Depends(require_bearer)],
    route_class=DatabaseRoute,
)


@router.get("/tables", operation_id="listDatabaseTables")
async def tables(session: Session) -> list[DatabaseTable]:
    """Registered Trace-it application tables only; audit tables are read-only."""
    return [
        DatabaseTable(
            name=name,
            primary_key=[c.name for c in service.Base.metadata.tables[name].primary_key],
            writable=name not in service.READ_ONLY,
        )
        for name in service.names()
    ]


@router.get("/tables/{table_name}/schema", operation_id="getDatabaseTableSchema")
async def schema(table_name: str, session: Session) -> DatabaseSchema:
    """Columns, generated values, keys, checks and indexes. Names are not SQL expressions."""
    return DatabaseSchema(**await service.schema(session, table_name))


@router.get("/tables/{table_name}/rows", operation_id="listDatabaseRows")
async def rows(
    table_name: str,
    session: Session,
    filters: Annotated[
        str | None, Query(description='JSON equality filters, e.g. {"id":1}')
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DatabaseRows:
    """Primary-key ordered pages, including an etag for each complete row."""
    return await service.rows(session, table_name, service.object_parameter(filters), limit, offset)


@router.get("/tables/{table_name}/row", operation_id="getDatabaseRow")
async def row(
    table_name: str,
    session: Session,
    key: Annotated[str, Query(description='Complete primary key as JSON, e.g. {"id":1}')],
) -> DatabaseRow:
    return await service.one(session, table_name, service.object_parameter(key))


@router.get(
    "/tables/{table_name}/export",
    operation_id="exportDatabaseRows",
    response_class=Response,
    responses={200: {"content": {"application/x-ndjson": {"schema": {"type": "string"}}}}},
)
async def export(
    table_name: str,
    session: Session,
    filters: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Response:
    """A bounded JSONL page. Follow X-Next-Offset until it is absent."""
    page = await service.rows(session, table_name, service.object_parameter(filters), limit, offset)
    headers = {"Content-Disposition": f'attachment; filename="{table_name}.jsonl"'}
    if page.next_offset is not None:
        headers["X-Next-Offset"] = str(page.next_offset)
    return Response(
        "".join(json.dumps(item.values, ensure_ascii=True) + "\n" for item in page.rows),
        media_type="application/x-ndjson",
        headers=headers,
    )


@router.post("/tables/{table_name}/rows", status_code=201, operation_id="createDatabaseRow")
async def create(table_name: str, payload: DatabaseCreate, session: Session) -> DatabaseWriteResult:
    """Insert one row and audit it atomically. Omit generated columns."""
    return DatabaseWriteResult(
        **await service.mutate(session, table_name, "insert", payload.values, payload.reason)
    )


@router.patch("/tables/{table_name}/row", operation_id="updateDatabaseRow")
async def update(table_name: str, payload: DatabaseUpdate, session: Session) -> DatabaseWriteResult:
    """Update one locked row if its etag still matches; requires a reason."""
    return DatabaseWriteResult(
        **await service.mutate(
            session,
            table_name,
            "update",
            payload.values,
            payload.reason,
            payload.key,
            payload.expected_etag,
        )
    )


@router.delete("/tables/{table_name}/row", operation_id="deleteDatabaseRow")
async def delete(table_name: str, payload: DatabaseDelete, session: Session) -> DatabaseWriteResult:
    """Delete exactly one row by primary key and etag; foreign keys remain enforced."""
    return DatabaseWriteResult(
        **await service.mutate(
            session, table_name, "delete", {}, payload.reason, payload.key, payload.expected_etag
        )
    )
