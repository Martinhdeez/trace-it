"""Throwaway live dashboard for trace-it. Serves index.html, proxies /api/* to :8010 and adds a
few helpers: the norm text, the golden, and a loop that feeds the 500 PDFs (and the workbook)
one by one through the real ingestion API (POST /processes/{id}/files).

    cd backend && set -a; . ../.env; set +a
    TRACE_DATABASE_URL=postgresql+psycopg://trace:trace@localhost:5432/trace_demo \
      uv run uvicorn --app-dir ../demo-logs/dashboard server:app --port 8020
"""

import asyncio
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "backend")]

import app.models  # noqa: E402,F401 - registers every table
import httpx  # noqa: E402
import openpyxl  # noqa: E402
from fastapi import FastAPI, Request, Response  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import session_factory  # noqa: E402
from app.features.ingestion.model import Instance  # noqa: E402

API = "http://localhost:8010"
HEADERS = {"X-User-Id": "1"}
CHALLENGE = ROOT / ".context/500-sombras-de-alberto"
BOOK = CHALLENGE / "FINAL_v7_DEFINITIVO_ahorasi.xlsx"
GOLDEN = ROOT / "backend/tests/golden/batch1_expected.jsonl"

app = FastAPI()
client = httpx.AsyncClient(base_url=API, headers=HEADERS, timeout=None)
ingests: dict[int, dict] = {}  # process id -> {"running", "done", "total", "error"}
jobs: set[asyncio.Task] = set()


@app.get("/")
async def index():
    return FileResponse(HERE / "index.html", headers={"Cache-Control": "no-store"})


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT"])
async def proxy(path: str, request: Request):
    r = await client.request(
        request.method,
        "/" + path,
        params=request.query_params,
        content=await request.body(),
        headers={"content-type": request.headers.get("content-type", "application/json")},
    )
    return Response(r.content, r.status_code, media_type=r.headers.get("content-type"))


@app.get("/helper/norm")
async def norm():
    sheet = openpyxl.load_workbook(BOOK, data_only=True)["Norma_Pagos_v3"]
    lines = [str(r[0]) for r in sheet.iter_rows(values_only=True) if r and r[0]]
    return {"text": "\n".join(lines), "sentences": [x for x in lines if x[:1].isdigit()]}


@app.get("/helper/golden")
async def golden():
    rows = [json.loads(x) for x in GOLDEN.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {r["file_id"]: {"expected": r["expected"], "why": r.get("why", "")} for r in rows}


@app.post("/helper/create")
async def create():
    definition = json.loads((ROOT / "processes/invoice-payment.json").read_text(encoding="utf-8"))
    definition |= {"name": f"Prueba en vivo {time.strftime('%H:%M:%S')}", "rules": [], "users": []}
    r = await client.post("/processes/definition", json=definition)
    r.raise_for_status()
    return {"id": r.json()["process"]["id"], "name": definition["name"]}


async def _ingest(pid: int, delay: float, limit: int | None):
    """Workbook first (suppliers, orders, parameters), then every PDF through the real API."""
    state = ingests[pid]
    try:
        r = await client.post(f"/processes/{pid}/sources/workbook",
                              files={"file": (BOOK.name, BOOK.read_bytes())},
                              data={"cut_off_date": "2026-09-18"})
        r.raise_for_status()
        state["workbook"] = [f"{s['name']} {s['rows']}" for s in r.json()["sources"]]
        paths = sorted((CHALLENGE / "facturas").glob("*.pdf"))[:limit]
        state["total"] = len(paths)
        t0 = time.perf_counter()
        for path in paths:
            r = await client.post(f"/processes/{pid}/files",
                                  files={"file": (path.name, path.read_bytes(), "application/pdf")})
            if r.status_code >= 400:
                state["failed"].append(f"{path.name}: {r.status_code} {r.text[:120]}")
            state["done"] += 1
            state["secs"] = round(time.perf_counter() - t0, 1)
            await asyncio.sleep(delay)
    except Exception as e:  # shown in the page
        state["error"] = repr(e)
    state["running"] = False


@app.post("/helper/ingest/{pid}")
async def ingest(pid: int, delay: float = 0, limit: int | None = None):
    if ingests.get(pid, {}).get("running"):
        return ingests[pid]
    ingests[pid] = {"running": True, "done": 0, "total": None, "error": None, "failed": [],
                    "secs": 0, "workbook": None}
    task = asyncio.create_task(_ingest(pid, delay, limit))
    jobs.add(task)
    task.add_done_callback(jobs.discard)
    return ingests[pid]


def _read(symbols: dict | None) -> int:
    """How many business symbols the reading filled (file_id and free_text do not count)."""
    return sum(1 for k, v in (symbols or {}).items()
               if k not in ("file_id", "free_text") and (v or {}).get("value") is not None)


@app.get("/helper/pdfs/{pid}")
async def pdfs(pid: int, after: int = 0):
    async with session_factory() as session:
        rows = (await session.execute(
            select(Instance.id, Instance.name, Instance.symbols)
            .where(Instance.process_id == pid, Instance.id > after).order_by(Instance.id)
        )).all()
    return {
        "ingest": ingests.get(pid),
        "files": [{"id": i, "name": n, "symbols": _read(s), "scan": not _read(s)}
                  for i, n, s in rows],
    }
