"""Application lifecycle for the bounded document processing workers."""

from contextlib import asynccontextmanager

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from filelock import FileLock, Timeout

from .config import Settings
from .quality import validate_quality_profile
from .service import ExtractionService


def current_service(request: Request) -> ExtractionService:
    return request.app.state.ingestion_service


@asynccontextmanager
async def ingestion_lifespan(app):
    service = getattr(app.state, "ingestion_service", None) or ExtractionService(Settings())
    app.state.ingestion_service = service
    await run_in_threadpool(validate_quality_profile, service.settings)
    lock = FileLock(service.settings.data_dir / "server.lock")
    try:
        lock.acquire(timeout=0)
    except Timeout as exc:
        raise RuntimeError("Use one server process per ingestion data directory") from exc
    service.start()
    try:
        yield
    finally:
        await run_in_threadpool(service.close)
        lock.release()
