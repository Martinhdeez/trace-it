"""Throughput figures of docs/scale-and-cost.md, measured through the application's own API.

    cd backend && uv run --env-file ../.env python ../tools/bench_scale.py engine --runs 3
    cd backend && uv run --env-file ../.env python ../tools/bench_scale.py extract
    cd backend && uv run --env-file ../.env python ../tools/bench_scale.py upload
    cd backend && uv run python ../tools/bench_scale.py capacity --sizes 500 5000 50000
    cd backend && uv run python ../tools/bench_scale.py grow --to 5000
    cd backend && uv run --env-file ../.env python ../tools/bench_scale.py workbook --process 2

Point `TRACE_DATABASE_URL` at a scratch database that `make demo` already filled: `engine`
re-decides every decided instance with `reprocess?dry_run=true` (nothing is written) and reads
the durations back from the spans; `upload` sends each PDF to `POST /processes/{id}/files`
(an instance that exists is never reset). `capacity` runs the engine and the sandbox directly
(nothing written) over the process's instances copied up to each size; `grow` adds such copies
to the database as PENDING instances, for a real `POST /processes/{id}/run`. `CHALLENGE_DIR`
points at the challenge corpus when the submodule lives elsewhere.
"""

# ruff: noqa: E402 - the imports below need `sys.path` set first.
import argparse
import asyncio
import json
import os
import resource
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "backend")]

from app.core.database import session_factory
from app.features.agents import sandbox
from app.features.decisions import engine as rules_engine
from app.features.decisions import service as decisions
from app.features.ingestion.model import Instance
from app.features.ingestion.symbols import flatten_symbols
from app.main import app
from httpx import ASGITransport, AsyncClient

import extractor

CHALLENGE = Path(os.getenv("CHALLENGE_DIR", ROOT / ".context/500-sombras-de-alberto"))
INVOICES = CHALLENGE / "facturas"

# The duplicate-order rule (R16) reading a purchase-order index built once per run, instead
# of scanning `others` for every instance: the fix path of docs/scale-and-cost.md, simulated.
INDEXED_DUPLICATE = """
def evaluate(instance, sources, others):
    order = key(instance.get("purchase_order"))
    names = sources["po_index"][0].get(order, []) if order else []
    if len(names) > 1:
        return fires("Same order as: " + ", ".join(sorted(names)[:5]))
    return passes()
"""


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
            scan = extractor.is_scan(extractor.text_of(path))
            t = time.perf_counter()
            r = await c.post(
                f"/processes/{process}/files", files={"file": (path.name, path.read_bytes())}
            )
            r.raise_for_status()
            times[scan].append(time.perf_counter() - t)
        total = time.perf_counter() - started
    print(f"upload: {len(paths)} PDFs in {total:.1f} s, {len(paths) / total:.1f}/s")
    for scan, ts in times.items():
        if ts:
            label = "scans (OCR)" if scan else "text layer"
            median, top = statistics.median(ts) * 1000, max(ts) * 1000
            print(f"  {label}: {len(ts)}, median {median:.0f} ms, max {top:.0f} ms, "
                  f"total {sum(ts):.1f} s")  # fmt: skip


async def workbook(process: int) -> None:
    book = CHALLENGE / "FINAL_v7_DEFINITIVO_ahorasi.xlsx"
    async with app.router.lifespan_context(app), api() as c:
        for _ in range(3):
            t = time.perf_counter()
            r = await c.post(
                f"/processes/{process}/sources/workbook",
                files={"file": (book.name, book.read_bytes())},
                data={"cut_off_date": "2026-09-18"},
            )
            r.raise_for_status()
            print(f"workbook ({book.stat().st_size} bytes): "
                  f"{(time.perf_counter() - t) * 1000:.0f} ms")  # fmt: skip


def copies(base: list[tuple[str, dict]], n: int) -> list[tuple[str, dict]]:
    """`base` repeated up to `n` entries. Copy c > 0 gets its own name and purchase order, so
    it is not a duplicate of its original: the duplicate rule fires at batch 1's rate."""
    out = []
    for i in range(n):
        c, (name, symbols) = i // len(base), base[i % len(base)]
        if c:
            symbols = dict(symbols)
            if symbols.get("purchase_order"):
                symbols["purchase_order"] = f"{symbols['purchase_order']}-C{c}"
            name = f"c{c}-{name}"
        out.append((name, symbols))
    return out


def children() -> tuple[float, int]:
    """CPU seconds of every finished child so far, and the largest child RSS (bytes on macOS)."""
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime + r.ru_stime, r.ru_maxrss


def key(value: object) -> str:  # the rules' own normalisation of a purchase order
    return str(value or "").strip().upper().replace(" ", "").replace("-", "").replace(".", "")


async def capacity(process: int, sizes: list[int], timeout: float) -> None:
    async with session_factory() as session:
        rules = await decisions.active_rules(session, process)
        outcomes = await decisions.outcomes(session, process)
        sources = await decisions.current_sources(session, process)
        instances = await decisions.instances_of(session, process)
    base = [(i.name, flatten_symbols(i.symbols)) for i in instances if i.symbols is not None]
    base = base[:500]
    print(f"{len(rules)} rules, base {len(base)} instances, sandbox timeout {timeout} s, "
          f"{os.cpu_count()} CPUs")  # fmt: skip
    names = {r.code: f"R{r.id}" for r in rules}
    for n in sizes:
        data = copies(base, n)
        population = [(k, {**s, "_instance": name}) for k, (name, s) in enumerate(data)]
        dataset = [(k, s) for k, (_, s) in enumerate(data)]
        stdin_mb = len(json.dumps({"sources": sources, "population": population})) / 1e6
        per_rule: list[tuple[str, float, float]] = []

        def timed(code, instances, src, pop, per_rule=per_rule, check=True):
            cpu, t = children()[0], time.perf_counter()
            try:
                return sandbox.run_dataset(code, instances, src, pop, timeout_s=timeout)
            except sandbox.SandboxError:
                if check:
                    raise
                return []  # timed out: the engine would escalate every instance
            finally:
                wall = time.perf_counter() - t
                per_rule.append((names.get(code, "fix"), wall, children()[0] - cpu))

        t = time.perf_counter()
        verdicts = rules_engine.decide(rules, outcomes, dataset, sources, population, timed)
        seq = time.perf_counter() - t
        errors = sum("RULE_ERROR" in v.reason for v in verdicts)
        slow = max(per_rule, key=lambda r: r[1])
        cpu = sum(r[2] for r in per_rule)
        print(f"\nn={n}: sequential {seq:.2f} s, {n / seq:.0f}/s, stdin {stdin_mb:.1f} MB per "
              f"rule, child CPU {cpu:.1f} s, largest child RSS so far "
              f"{children()[1] / 1e6:.0f} MB, verdicts with RULE_ERROR {errors}")  # fmt: skip
        print("  per rule, wall s: " + ", ".join(f"{r}={w:.2f}" for r, w, _ in per_rule))
        print(f"  slowest {slow[0]} {slow[1]:.2f} s")

        # Every rule's subprocess at once: the engine with a worker pool.
        for workers in (4, os.cpu_count()):
            t = time.perf_counter()
            with ThreadPoolExecutor(workers) as pool:
                run = lambda r, d=dataset, p=population: timed(r.code, d, sources, p, check=False)  # noqa: E731
                answers = list(pool.map(run, rules))
            par = time.perf_counter() - t
            print(f"  parallel, {workers} workers: {par:.2f} s, {n / par:.0f}/s, "
                  f"rules timed out {sum(not a for a in answers)}")  # fmt: skip

        # The fix path, simulated: a rule that never reads `others` gets no population (the
        # child stops building an O(n) list per instance), and the duplicate rule reads a
        # purchase-order index built once.
        index: dict[str, list[str]] = {}
        t = time.perf_counter()
        for _, s in population:
            if key(s.get("purchase_order")):
                index.setdefault(key(s.get("purchase_order")), []).append(s["_instance"])
        for r in rules:
            if "for other in others" in r.code:
                code = r.code.split("def evaluate")[0] + INDEXED_DUPLICATE
                timed(code, dataset, {**sources, "po_index": [index]}, [], check=False)
            else:
                timed(r.code, dataset, sources, [], check=False)
        fix = time.perf_counter() - t
        print(f"  fix path, sequential: {fix:.2f} s, {n / fix:.0f}/s, slowest rule "
              f"{max(w for _, w, _ in per_rule[-len(rules):]):.2f} s")  # fmt: skip


async def grow(process: int, to: int) -> None:
    """Copies of the process's first 500 instances as new PENDING instances, up to `to`."""
    async with session_factory() as session:
        existing = await decisions.instances_of(session, process)
        base = [(i.name, i.symbols, i.file_hash) for i in existing[:500]]
        for i in range(len(existing), to):
            c, (name, symbols, file_hash) = i // len(base), base[i % len(base)]
            symbols = json.loads(json.dumps(symbols)) if symbols is not None else None
            if symbols and symbols.get("purchase_order", {}).get("value"):
                symbols["purchase_order"]["value"] += f"-C{c}"
            session.add(
                Instance(
                    process_id=process, file_hash=file_hash, name=f"c{c}-{name}", symbols=symbols
                )  # fmt: skip
            )
        await session.commit()
    print(f"process {process}: {max(to, len(existing))} instances")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "what", choices=["engine", "extract", "upload", "workbook", "capacity", "grow"]
    )
    parser.add_argument("--process", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sizes", type=int, nargs="+", default=[500, 5000, 50000])
    parser.add_argument("--timeout", type=float, default=10.0, help="sandbox seconds per rule")
    parser.add_argument("--to", type=int, default=5000)
    a = parser.parse_args()
    if a.what == "engine":
        asyncio.run(engine(a.process, a.runs))
    elif a.what == "extract":
        extract()
    elif a.what == "upload":
        asyncio.run(upload(a.process, a.limit))
    elif a.what == "workbook":
        asyncio.run(workbook(a.process))
    elif a.what == "capacity":
        asyncio.run(capacity(a.process, a.sizes, a.timeout))
    else:
        asyncio.run(grow(a.process, a.to))
