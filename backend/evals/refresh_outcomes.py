"""Regenerate a corpus through current production endpoints in a fresh process.

Use a migrated, isolated database via TRACE_DATABASE_URL. No prior decisions or
extraction caches are reused. Inputs, provider evidence and decisions stay local;
outcomes.jsonl and summary.json can be shared after reviewing the comparison.
"""

import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def run(args):
    from httpx import ASGITransport, AsyncClient

    from app.core.database import engine, session_factory
    from app.features.ingestion.config import Settings
    from app.features.ingestion.quality import validate_quality_profile
    from app.features.ingestion.runtime import current_service
    from app.features.ingestion.service import PIPELINE_VERSION, ExtractionService
    from app.features.processes.definition import Definition, load_definition
    from app.features.sources.model import Source
    from app.features.users.model import User
    from app.main import app

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "data").exists() or (output / "outcomes.jsonl").exists():
        raise ValueError("Choose a fresh output directory; previous evidence is never overwritten")
    files = sorted(args.invoices.glob("*.pdf"))
    if len(files) != args.expected_files:
        raise ValueError(f"Expected {args.expected_files} invoices; found {len(files)}")
    settings = Settings(data_dir=output / "data", ocr_profile="verified", vlm_timeout=120)
    profile = validate_quality_profile(settings)
    service = ExtractionService(settings)
    if args.reader_cache_from:
        for name in ("reader-cache", "provider-journal"):
            source = args.reader_cache_from / name
            if source.is_dir():
                shutil.copytree(source, settings.data_dir / name)
    spec = json.loads((ROOT / "processes/invoice-payment.json").read_text(encoding="utf-8"))
    spec["name"] = "Verified OCR corpus " + uuid.uuid4().hex[:12]
    spec.pop("use_case", None)
    erp = json.loads(args.erp_snapshot.read_text(encoding="utf-8"))
    started = datetime.now(UTC).isoformat()
    source_hashes = {
        p.relative_to(ROOT).as_posix(): digest(p)
        for folder in (ROOT / "backend/app", ROOT / "processes")
        for p in sorted(folder.rglob("*"))
        if p.is_file() and p.suffix in {".py", ".json"}
    }
    source_hashes["backend/uv.lock"] = digest(ROOT / "backend/uv.lock")
    dump(output / "code-manifest.json", source_hashes)
    async with session_factory() as session:
        loaded = await load_definition(session, Definition.model_validate(spec), ROOT / "processes")
        pid = loaded.process.id
        user = User(
            name="OCR corpus verifier", email=uuid.uuid4().hex + "@test.invalid", role="manager"
        )
        session.add(user)
        session.add(
            Source(process_id=pid, name="erp", origin="Frozen real HTTP ERP snapshot", rows=erp)
        )
        await session.commit()
        uid = user.id
    app.dependency_overrides[current_service] = lambda: service
    counts, warnings, versions = Counter(), Counter(), Counter()
    hashes = {p.name: digest(p) for p in files}
    dump(
        output / "inputs.json",
        {
            "invoices": hashes,
            "workbook_sha256": digest(args.book),
            "erp_sha256": digest(args.erp_snapshot),
        },
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://corpus",
            headers={"X-User-Id": str(uid)},
            timeout=None,
        ) as api:

            async def post(path, **kwargs):
                response = await api.post(path, **kwargs)
                response.raise_for_status()
                return response.json()

            draft = await post(f"/processes/{pid}/draft/validate")
            if not draft["validation"]["valid"]:
                raise ValueError("Process pack validation failed")
            version = await post(
                f"/processes/{pid}/draft/publish",
                json={
                    "revision": draft["revision"],
                    "validation_hash": draft["validation"]["hash"],
                    "reason": "Regenerate the OCR corpus with the supplied validated invoice rules",
                },
            )
            workbook = await post(
                f"/processes/{pid}/sources/workbook",
                files={"file": (args.book.name, args.book.read_bytes())},
                data={"cut_off_date": args.cutoff},
            )
            dump(output / "workbook.json", workbook)
            dump(
                output / "workbook-extraction.json", service.store.result(workbook["extraction_id"])
            )
            with (
                (output / "extractions.jsonl").open("w", encoding="utf-8") as extractions,
                (output / "uploads.jsonl").open("w", encoding="utf-8") as uploads,
            ):
                for i, path in enumerate(files, 1):
                    data = await post(
                        f"/processes/{pid}/files",
                        files={"file": (path.name, path.read_bytes())},
                        data={"ocr": "true", "vlm": "true", "jev": "true"},
                    )
                    extraction = data["extraction"]
                    if not data["created"] or extraction["pipeline_version"] != PIPELINE_VERSION:
                        raise ValueError("Expected a new instance with the current pipeline")
                    if extraction["sha256"] != hashes[path.name]:
                        raise ValueError("Document identity changed during extraction")
                    versions[extraction["pipeline_version"]] += 1
                    warnings.update(w["code"] for w in extraction["warnings"])
                    counts.update(
                        {
                            k: v
                            for k, v in extraction["metrics"].items()
                            if isinstance(v, int) and not isinstance(v, bool)
                        }
                    )
                    extractions.write(json.dumps(extraction, ensure_ascii=False) + "\n")
                    uploads.write(json.dumps(data, ensure_ascii=False) + "\n")
                    extractions.flush()
                    uploads.flush()
                    print(f"{i}/{len(files)} {path.name}", flush=True)
            result = await post(f"/processes/{pid}/run")
            response = await api.get(f"/processes/{pid}/export")
            response.raise_for_status()
            outcomes = [json.loads(line) for line in response.text.splitlines()]
            if (
                len(outcomes) != len(files)
                or {r["file_id"] for r in outcomes} != set(hashes)
                or any(r["result"] not in {"PAGAR", "NO_PAGAR", "ESCALAR"} for r in outcomes)
            ):
                raise ValueError("Export does not contain one valid outcome per input")
            detail = []
            with (output / "uploads.jsonl").open(encoding="utf-8") as uploads:
                for line in uploads:
                    ident = json.loads(line)["instance_id"]
                    response = await api.get(f"/instances/{ident}")
                    response.raise_for_status()
                    detail.append(response.json())
            dump(output / "instances.json", detail)
            repeated = await post(f"/processes/{pid}/run")
            if repeated["decided"] != 0:
                raise ValueError("Repeated run changed already decided instances")
            (output / "outcomes.jsonl").write_text(
                "".join(
                    json.dumps(row, ensure_ascii=False) + "\n"
                    for row in sorted(outcomes, key=lambda r: r["file_id"])
                ),
                encoding="utf-8",
            )
            summary = {
                "started_at": started,
                "finished_at": datetime.now(UTC).isoformat(),
                "git_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                "code_manifest_sha256": digest(output / "code-manifest.json"),
                "pipeline_version": PIPELINE_VERSION,
                "profile": profile,
                "files": len(files),
                "by_decision": dict(Counter(r["result"] for r in outcomes)),
                "extraction_versions": dict(versions),
                "warnings": dict(warnings),
                "metrics": dict(counts),
                "process_version_hash": version["content_hash"],
                "cut_off_date": args.cutoff,
                "erp": "Frozen real HTTP ERP snapshot",
                "erp_sha256": digest(args.erp_snapshot),
                "workbook_sha256": digest(args.book),
                "inputs_sha256": digest(output / "inputs.json"),
                "outcomes_sha256": digest(output / "outcomes.jsonl"),
                "fresh_process": True,
                "fresh_extraction_store": True,
                "fresh_provider_journal": not bool(args.reader_cache_from),
                "reader_cache_source": str(args.reader_cache_from)
                if args.reader_cache_from
                else None,
                "rerun_decided": repeated["decided"],
                "run": result,
            }
            dump(output / "summary.json", summary)
            print(
                json.dumps({"files": len(files), "by_decision": summary["by_decision"]}), flush=True
            )
    finally:
        app.dependency_overrides.pop(current_service, None)
        service.close()
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoices", type=Path, required=True)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--erp-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--expected-files", type=int, default=500)
    parser.add_argument(
        "--reader-cache-from",
        type=Path,
        help="Reuse content-addressed reader evidence only; extraction and decisions remain fresh",
    )
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
