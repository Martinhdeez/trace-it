from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.exceptions import TraceError
from app.features.llm.router import router as llm_router
from app.features.procesos.router import router as procesos_router
from app.features.reglas.router import router as reglas_router
from app.features.usuarios.router import router as usuarios_router

app = FastAPI(
    title="trace-pay",
    version="0.1.0",
    description=(
        "Deterministic decision processes with rules compiled to code by agents.\n\n"
        "Identify with the `X-Usuario-Id` header (see `POST /login`). Errors are "
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


@app.get("/salud", tags=["sistema"], operation_id="health")
async def salud() -> dict[str, str]:
    return {"estado": "ok"}


for router in (usuarios_router, procesos_router, reglas_router, llm_router):
    app.include_router(router)
