from contextlib import asynccontextmanager

import logfire
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.exceptions import TraceError
from app.core.events import configure_observability
from app.features.agents.router import router as agents_router
from app.features.alerts.router import router as alerts_router
from app.features.decisions.router import router as decisions_router
from app.features.ingestion.process_router import router as ingestion_router
from app.features.ingestion.router import create_router as create_extraction_router
from app.features.ingestion.runtime import ingestion_lifespan
from app.features.learning.router import router as learning_router
from app.features.processes.draft_router import router as draft_router
from app.features.processes.router import router as processes_router
from app.features.proposals.router import router as proposals_router
from app.features.rules import service as rules_service
from app.features.rules.router import router as rules_router
from app.features.sources.router import router as sources_router
from app.features.traces.router import router as traces_router
from app.features.use_cases.router import router as use_cases_router
from app.features.users.dependencies import current_user
from app.features.users.router import router as users_router
from app.features.versions.router import router as versions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with ingestion_lifespan(app):
        await rules_service.resume_compilations()
        yield


configure_observability()
app = FastAPI(
    title="trace-it",
    version="0.1.0",
    lifespan=lifespan,
    description=(
        "Deterministic decision processes with rules compiled to code by agents.\n\n"
        "Identify with the `X-User-Id` header (see `POST /login`). Errors are "
        '`{"code", "message"}`.'
    ),
)

logfire.instrument_fastapi(app)

# Open CORS for the hackathon frontend; restrict origins if deployed.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(TraceError)
async def trace_error(_: Request, error: TraceError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code, content={"code": error.code, "message": error.message}
    )


@app.get("/health", tags=["system"], operation_id="health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


for router in (
    versions_router,
    users_router,
    processes_router,
    draft_router,
    rules_router,
    decisions_router,
    agents_router,
    ingestion_router,
    sources_router,
    use_cases_router,
    traces_router,
    learning_router,
    alerts_router,
    proposals_router,
):
    app.include_router(router)

app.include_router(create_extraction_router(), dependencies=[Depends(current_user)])
