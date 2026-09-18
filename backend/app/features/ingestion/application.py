import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from filelock import FileLock, Timeout

from app.common.exceptions import TraceError
from app.features.ingestion.config import Settings
from app.features.ingestion.router import create_router
from app.features.ingestion.service import ExtractionService

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None, service: ExtractionService | None = None
) -> FastAPI:
    settings = settings or Settings()
    service = service or ExtractionService(settings)

    @asynccontextmanager
    async def lifespan(app):
        lock = FileLock(settings.data_dir / "server.lock")
        try:
            lock.acquire(timeout=0)
        except Timeout as exc:
            raise RuntimeError(
                "Use one Uvicorn process per data directory; workers are managed internally"
            ) from exc
        service.start()
        try:
            yield
        finally:
            await run_in_threadpool(service.close)
            lock.release()

    app = FastAPI(
        title="Trace Pay",
        version="0.1.0",
        lifespan=lifespan,
        description=(
            "PDF/XLSX text and field extraction with provenance. "
            "Missing fields are allowed; workflow decisions belong to the caller."
        ),
    )
    app.state.service = service

    @app.exception_handler(TraceError)
    async def app_error_handler(request: Request, exc: TraceError):
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "workers": settings.workers,
            "ocr_models": service.ocr.signature(),
            "vlm_configured": getattr(service.vlm, "configured", False),
            "jev_configured": getattr(service.judge, "configured", False),
        }

    app.include_router(create_router(settings, service))
    return app
