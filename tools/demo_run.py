"""Upload challenge invoices through the production API, decide and export them.

Requires `make setup`, downloaded OCR models and `make erp`. See tools/README.md.
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

ROOT = Path(__file__).resolve().parent.parent
CHALLENGE = ROOT / ".context/500-sombras-de-alberto"


async def authenticate(api: httpx.AsyncClient, email: str, process_id: int | None) -> int:
    login = await api.post("/login", json={"email": email})
    login.raise_for_status()
    api.headers["X-User-Id"] = str(login.json()["id"])
    if process_id is not None:
        return process_id
    response = await api.get("/processes")
    response.raise_for_status()
    matches = [p["id"] for p in response.json() if p["name"] == "Invoice payment"]
    if len(matches) != 1:
        raise ValueError("Load the invoice pack with `make setup`, or select --process ID.")
    return matches[0]


async def run(
    api: httpx.AsyncClient,
    process_id: int,
    files: list[Path],
    book: Path,
    cutoff: str,
    output: Path,
    *,
    local_only: bool = False,
) -> None:
    """Publish a complete set of artifacts only after the whole run succeeds."""
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".demo-", dir=output) as temporary:
        staging = Path(temporary)
        await _run(api, process_id, files, book, cutoff, staging, local_only=local_only)
        for name in ("extractions.jsonl", "outcomes.jsonl", "detail.json"):
            (staging / name).replace(output / name)
    print(f"written to {output}")


async def _run(
    api: httpx.AsyncClient,
    process_id: int,
    files: list[Path],
    book: Path,
    cutoff: str,
    output: Path,
    *,
    local_only: bool,
) -> None:
    """Load sources before extraction; decide only after every upload succeeds."""
    prefix = f"/processes/{process_id}"
    with book.open("rb") as stream:
        response = await api.post(
            f"{prefix}/sources/workbook",
            files={
                "file": (
                    book.name,
                    stream,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"cut_off_date": cutoff},
        )
    response.raise_for_status()
    print(f"workbook: {book.name}", flush=True)
    response = await api.post(f"{prefix}/sources/erp/sync")
    response.raise_for_status()
    print(f"erp sync: {response.json()['rows']} rows", flush=True)

    response = await api.get(f"{prefix}/instances")
    response.raise_for_status()
    existing = response.json()

    options = {"ocr": True}
    if local_only:
        options.update(vlm=False, jev=False)
    reused = 0
    with (output / "extractions.jsonl").open("w", encoding="utf-8") as evidence:
        for index, path in enumerate(files, 1):
            match = None
            candidates = sorted(
                (i for i in existing if i["name"] == path.name),
                key=lambda i: i["id"],
                reverse=True,
            )
            if candidates:
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                for candidate in candidates:
                    response = await api.get(f"/instances/{candidate['id']}")
                    response.raise_for_status()
                    if response.json()["file_hash"] == digest:
                        if candidate["id"] != candidates[0]["id"]:
                            raise ValueError(
                                f"{path.name} matches a historical instance, but export selects "
                                "a newer version. Use a fresh process to evaluate these files."
                            )
                        match = response.json()
                        break
            if match is None:
                with path.open("rb") as stream:
                    response = await api.post(
                        f"{prefix}/files",
                        files={"file": (path.name, stream, "application/pdf")},
                        data={key: str(value).lower() for key, value in options.items()},
                    )
                response.raise_for_status()
                upload = response.json()
            else:
                upload = {
                    "instance_id": match["id"],
                    "name": path.name,
                    "file_hash": digest,
                    "status": match["status"],
                    "created": False,
                    "reused": True,
                    "symbols": match["symbols"],
                }
            # Re-extract pending matches without uploading them twice. The fallback
            # also covers a concurrent upload; decided evidence is never overwritten.
            if not upload["created"] and upload["status"] == "PENDING":
                response = await api.post(
                    f"/instances/{upload['instance_id']}/extract", json=options
                )
                response.raise_for_status()
                upload = response.json()
            elif not upload["created"]:
                reused += 1
            evidence.write(json.dumps({"file_id": path.name, **upload}, ensure_ascii=False) + "\n")
            evidence.flush()
            print(f"upload {index}/{len(files)}: {path.name} ({upload['status']})", flush=True)
    if reused:
        print(f"Preserved {reused} already-decided instances; their stored symbols are unchanged.")

    response = await api.post(f"{prefix}/run")
    response.raise_for_status()
    print(f"run: {response.json()}", flush=True)
    response = await api.get(f"{prefix}/export")
    response.raise_for_status()
    outcomes = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    (output / "outcomes.jsonl").write_text(response.text.rstrip() + "\n", encoding="utf-8")
    if duplicates := response.headers.get("X-Duplicate-Names"):
        print(f"Export uses the newest instance for duplicate names: {duplicates}")

    response = await api.get(f"{prefix}/instances")
    response.raise_for_status()
    by_name = {i["name"]: i for i in sorted(response.json(), key=lambda i: i["id"])}
    detail = []
    for outcome in outcomes:
        instance = by_name[outcome["file_id"]]
        response = await api.get(f"/instances/{instance['id']}")
        response.raise_for_status()
        document = response.json()
        # Match export: latest engine decision, falling back to a human decision.
        decisions = document["decisions"]
        latest = next((d for d in reversed(decisions) if d["author"] == "engine"), decisions[-1])
        detail.append(
            {
                **outcome,
                "rules_that_fired": [r["reason"] for r in latest["results"] if r["fires"]],
                "symbols": document["symbols"],
            }
        )
    (output / "detail.json").write_text(
        json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"export: {len(outcomes)} invoices (whole process)")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-url", default=f"http://127.0.0.1:{os.getenv('BACKEND_PORT', '8000')}"
    )
    parser.add_argument("--email", default="martin@trace-it.local")
    parser.add_argument("--process", type=int, help="default: discover the Invoice payment process")
    parser.add_argument("--invoices", type=Path, default=CHALLENGE / "facturas")
    parser.add_argument("--book", type=Path, default=CHALLENGE / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    parser.add_argument("--cutoff", type=date.fromisoformat, default="2026-09-18")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--limit", type=int, help="upload first N PDFs; run/export whole process")
    parser.add_argument("--local-only", action="store_true", help="disable VLM/Jev; keep local OCR")
    parser.add_argument(
        "--timeout", type=float, default=900, help="HTTP timeout in seconds for OCR"
    )
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not args.book.is_file():
        parser.error(f"Workbook not found: {args.book}")
    args.files = sorted(args.invoices.glob("*.pdf"))[: args.limit]
    if not args.files:
        parser.error(f"No PDFs found in {args.invoices}")
    return args


async def main() -> None:
    args = parse_args()
    started = time.monotonic()
    async with httpx.AsyncClient(
        base_url=args.api_url.rstrip("/"), timeout=httpx.Timeout(args.timeout, connect=10)
    ) as api:
        process_id = await authenticate(api, args.email, args.process)
        await run(
            api,
            process_id,
            args.files,
            args.book,
            args.cutoff.isoformat(),
            args.output,
            local_only=args.local_only,
        )
    print(f"total: {time.monotonic() - started:.0f}s")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.HTTPStatusError as exc:
        sys.exit(
            f"API {exc.request.url.path}: HTTP {exc.response.status_code}: "
            f"{exc.response.text[:500]}"
        )
    except (httpx.RequestError, OSError, ValueError) as exc:
        sys.exit(f"Demo failed: {exc}")
