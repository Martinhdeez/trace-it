"""Run the whole invoice process over the challenge corpus and write `outcomes.jsonl`.

    make demo          # or: PYTHONPATH=backend:tools uv run --project backend \
                       #       python tools/demo_run.py

Stand-in for ingestion, sources and extraction, which are not built yet. Everything to their
right — the rules, the engine, the decision history, the export — is the real application,
called through its own API. When those features land, this script goes away.
"""

# ruff: noqa: E402 - the imports below need `sys.path` set first.
import argparse
import asyncio
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "backend")]

from app.core import events
from app.core.database import session_factory
from app.features.ingestion.model import File, Instance
from app.features.sources.model import Source
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import insert

import extractor
import workbook

CHALLENGE = ROOT / ".context/500-sombras-de-alberto"


async def ingest(process_id: int, invoices: Path, book: Path, cutoff: str, limit: int | None):
    """Everything ingestion and extraction will do for real.

    The ERP is not loaded here: `features/sources` has a real connector for it, driven by
    `processes/invoice-payment/sources.json`. Only the spreadsheet has no connector yet.
    """
    sources = workbook.sources(str(book), cutoff)
    print("spreadsheet: " + ", ".join(f"{k}={len(v)}" for k, v in sources.items()))

    read = scans = 0
    async with session_factory() as session:
        for name, rows in sources.items():
            session.add(Source(process_id=process_id, name=name, origin="demo", rows=rows))
        for path in sorted(invoices.glob("*.pdf"))[:limit]:
            content = path.read_bytes()
            text = extractor.text_of(path)
            if extractor.is_scan(text):
                symbols, scans = {}, scans + 1
            else:
                # Stored with provenance: rule code only ever sees the values (ADR 0008).
                symbols = {
                    name: {"value": value, "origin": "pdf-text"}
                    for name, value in extractor.symbols(path.name, text).items()
                    if value
                }
                read += 1
            digest = hashlib.sha256(content).hexdigest()
            # A file already stored (same bytes under another name, or a second run over
            # the same folder) is not stored twice, and an instance is never reset.
            await session.execute(
                insert(File)
                .values(hash=digest, name=path.name, content=content, text=text)
                .on_conflict_do_nothing()
            )
            instance_id = await session.scalar(
                insert(Instance)
                .values(process_id=process_id, file_hash=digest, name=path.name, symbols=symbols)
                .on_conflict_do_nothing()
                .returning(Instance.id)
            )
            if instance_id is not None:  # the same audit point as the ingestion API
                events.record(
                    session,
                    "ingest_document",
                    process_id=process_id,
                    instance_id=instance_id,
                    data={"file": path.name, "reader": "pdf-text", "symbols": symbols},
                )
        await session.commit()
    print(f"extraction: {read} read from the text layer, {scans} scans left without symbols")


async def decide(process_id: int, output: Path):
    """From here on it is the application, through its own API."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://demo", timeout=None
    ) as api:
        # The ERP through its own connector: sessions, retries and paging are its problem.
        r = await api.post(f"/processes/{process_id}/sources/erp/sync")
        if r.status_code != 200:
            sys.exit(f"the ERP sync failed ({r.status_code}): {r.text[:300]}\nIs `make erp` up?")
        sync = r.json()
        stats = sync["stats"]
        print(
            f"erp sync: {sync['rows']} rows, {stats['pages']} pages, "
            f"{stats['retries']} retries, {stats['logins']} logins, {stats['duration_ms']}ms"
        )

        started = time.monotonic()
        r = await api.post(f"/processes/{process_id}/run")
        r.raise_for_status()
        print(f"\nrun: {r.json()}  ({time.monotonic() - started:.0f}s)")

        r = await api.get(f"/processes/{process_id}/export")
        if r.status_code != 200:
            sys.exit(f"export refused ({r.status_code}): {r.text[:300]}")
        output.mkdir(parents=True, exist_ok=True)
        (output / "outcomes.jsonl").write_text(r.text + "\n", encoding="utf-8")
        print(f"export: {len(r.text.splitlines())} lines")

        detail, reasons = [], Counter()
        for i in (await api.get(f"/processes/{process_id}/instances")).json():
            d = (await api.get(f"/instances/{i['id']}")).json()
            latest = d["decisions"][-1]
            detail.append(
                {
                    "file_id": i["name"],
                    "result": latest["decision"],
                    "rules_that_fired": [x["reason"] for x in latest["results"] if x["fires"]],
                    "symbols": d["symbols"],
                }
            )
            if latest["decision"] != "PAGAR":
                reasons[(latest["decision"], (latest["reason"] or "")[:60])] += 1
        (output / "detail.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print("\nwhy an invoice is not paid:")
    for (decision, reason), times in reasons.most_common(20):
        print(f"  {times:3}x {decision:9} {reason}")
    print(f"\nwritten to {output}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process", type=int, default=1)
    parser.add_argument("--invoices", type=Path, default=CHALLENGE / "facturas")
    parser.add_argument(
        "--book", type=Path, default=CHALLENGE / "FINAL_v7_DEFINITIVO_ahorasi.xlsx"
    )
    parser.add_argument("--cutoff", default="2026-09-18", help="`parameters.cut_off_date`")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--limit", type=int, help="only the first N invoices")
    args = parser.parse_args()

    started = time.monotonic()
    # One trace for the ingestion, one `ingest_document` point per new instance (ADR 0018).
    with events.span("demo_ingest", process_id=args.process, reader="pdf-text"):
        await ingest(args.process, args.invoices, args.book, args.cutoff, args.limit)
    await decide(args.process, args.output)
    print(f"total: {time.monotonic() - started:.0f}s")


asyncio.run(main())
