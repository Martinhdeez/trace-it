from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.exceptions import TraceError
from app.features.agents.router import router as agents_router
from app.features.decisions.router import router as decisions_router
from app.features.llm.router import router as llm_router
from app.features.processes.router import router as processes_router
from app.features.rules.router import router as rules_router
from app.features.sources.router import router as sources_router
from app.features.users.router import router as users_router

app = FastAPI(
    title="trace-it",
    version="0.1.0",
    description=(
        "Deterministic decision processes with rules compiled to code by agents.\n\n"
        "Identify with the `X-User-Id` header (see `POST /login`). Errors are "
        '`{"code", "message"}`; 501 means the contract exists but is not implemented yet.'
    ),
)

# ponytail: open CORS for the hackathon frontend; restrict origins if deployed.
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
    users_router,
    processes_router,
    rules_router,
    decisions_router,
    llm_router,
    agents_router,
    sources_router,
):
    app.include_router(router)
