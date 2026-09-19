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


async def for_process(session, process_id, service, options):
    """Resolve a process once before reading or reusing document evidence."""
    from app.features.processes import execution
    from app.features.versions.model import ProcessDraft
    from app.features.versions.service import active

    version = await active(session, process_id, required=False)
    draft = None if version else await session.get(ProcessDraft, process_id)
    snapshot = version.snapshot if version else draft.snapshot if draft else {}
    if "execution" not in snapshot:
        return service, options  # Legacy snapshots preserve their historical behavior.
    config = execution.read(snapshot)
    extraction = config.extraction
    options = options.model_copy(
        update={
            "mode": extraction.mode,
            "ocr": extraction.ocr and options.ocr,
            "secondary_ocr": extraction.secondary_ocr and options.secondary_ocr,
            "focused_verification": extraction.focused_verification
            and options.focused_verification,
            "source_verification": extraction.source_verification and options.source_verification,
            "vlm": bool(extraction.vision_model) and options.vlm is not False,
            "jev": bool(extraction.text_judge_model) and options.jev is not False,
        }
    )
    return service.configured(config), options
