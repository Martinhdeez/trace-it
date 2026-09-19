"""Throughput figures of docs/scale-and-cost.md, measured through the application's own API.

    cd backend && uv run --env-file ../.env python ../tools/bench_scale.py engine --runs 3
    cd backend && uv run --env-file ../.env python ../tools/bench_scale.py extract
    cd backend && uv run --env-file ../.env python ../tools/bench_scale.py upload

Point `TRACE_DATABASE_URL` at a scratch database that `make demo` already filled: `engine`
re-decides every decided instance with `reprocess?dry_run=true` (nothing is written) and reads
the durations back from the spans; `upload` sends each PDF to `POST /processes/{id}/files`
(an instance that exists is never reset).
"""

# ruff: noqa: E402 - the imports below need `sys.path` set first.
import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "backend")]

from app.main import app
from httpx import ASGITransport, AsyncClient

import extractor

INVOICES = ROOT / ".context/500-sombras-de-alberto/facturas"


def api() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://bench", timeout=None,
        headers={"X-User-Id": "1"},
    )  # fmt: skip


async def engine(process: int, runs: int) -> None:
    async with api() as c:
        for _ in range(runs):
            r = await c.post(f"/processes/{process}/reprocess?dry_run=true")
            r.raise_for_status()
        spans = (await c.get(f"/traces?process_id={process}&name=reprocess&limit={runs}")).json()
        rates = []
        for s in reversed(spans):
            n, ms = s["data"]["instances"], s["duration_ms"]
            rates.append(n / ms * 1000)
            print(f"reprocess: {n} instances, {s['data']['rules']} rules, {ms} ms, "
                  f"{rates[-1]:.0f}/s")  # fmt: skip
        print(f"median: {statistics.median(rates):.0f} instances/s")
        # The per-rule spans of these runs only: the children of the spans above.
        ids = {s["span_id"] for s in spans}
        rules = (await c.get(f"/traces?process_id={process}&name=evaluate_rule&limit=1000")).json()
        ms = sorted(s["duration_ms"] for s in rules if s["parent_id"] in ids)
        q = statistics.quantiles(ms, n=20)
        print(f"evaluate_rule: {len(ms)} spans, p50 {q[9]:.0f} ms, p95 {q[18]:.0f} ms, "
              f"max {ms[-1]} ms")  # fmt: skip


def extract() -> None:
    started, scans = time.perf_counter(), 0
    paths = sorted(INVOICES.glob("*.pdf"))
    for path in paths:
        text = extractor.text_of(path)
        if extractor.is_scan(text):
            scans += 1
        else:
            extractor.symbols(path.name, text)
    s = time.perf_counter() - started
    print(f"extractor: {len(paths)} PDFs ({scans} scans) in {s:.1f} s, {len(paths) / s:.0f}/s")


async def upload(process: int, limit: int | None) -> None:
    paths = sorted(INVOICES.glob("*.pdf"))[:limit]
    times: dict[bool, list[float]] = {True: [], False: []}  # no symbols read -> seconds
    async with app.router.lifespan_context(app), api() as c:  # starts the ingestion service
        started = time.perf_counter()
        for path in paths:
            t = time.perf_counter()
            r = await c.post(
                f"/processes/{process}/files", files={"file": (path.name, path.read_bytes())}
            )
            r.raise_for_status()
            times[not r.json()["symbols"]].append(time.perf_counter() - t)
        total = time.perf_counter() - started
    print(f"upload: {len(paths)} PDFs in {total:.1f} s, {len(paths) / total:.1f}/s")
    for scan, ts in times.items():
        if ts:
            label = "no symbols (scans)" if scan else "symbols read"
            median, top = statistics.median(ts) * 1000, max(ts) * 1000
            print(f"  {label}: {len(ts)}, median {median:.0f} ms, max {top:.0f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("what", choices=["engine", "extract", "upload"])
    parser.add_argument("--process", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--limit", type=int)
    a = parser.parse_args()
    if a.what == "engine":
        asyncio.run(engine(a.process, a.runs))
    elif a.what == "extract":
        extract()
    else:
        asyncio.run(upload(a.process, a.limit))
