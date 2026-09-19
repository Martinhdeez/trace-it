"""Run the 540 original PDFs through upload, publication, live ERP, decisions and export.

Requires an already migrated isolated database ending in _test. Never uses a live DB.
Reader journals can be reused; extraction, mapping, HTTP routes and rules are real.
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import uuid
from pathlib import Path


async def rehearse(args):
    from app.core.config import settings as app_settings
    from app.core.database import engine, session_factory
    from app.features.ingestion.config import Settings
    from app.features.ingestion.runtime import current_service
    from app.features.ingestion.service import ExtractionService
    from app.features.processes.definition import Definition, load_definition
    from app.features.sources.tests.conftest import start_erp
    from app.features.use_cases import service as use_cases
    from app.features.versions.tests.test_api import publish
    from app.main import app
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.engine import make_url
    from tests.support import pack, users

    assert make_url(app_settings.database_url).database.endswith("_test"), "Use an isolated test DB"
    for name in ("provider-journal", "reader-cache"):
        shutil.copytree(
            args.readers / "cache" / name, args.output / "cache" / name, dirs_exist_ok=True
        )
    reader = ExtractionService(Settings(data_dir=args.output / "cache", workers=2))
    app.dependency_overrides[current_service] = lambda: reader
    erp, url = start_erp("--lote2", str(args.data / "erp_export_lote2.csv"))
    os.environ.update(
        TRACE_ERP_URL=url, TRACE_ERP_USER="alberto", TRACE_ERP_PASSWORD="FACTURAS2009"
    )
    definition = pack.definition()
    definition["name"] += " batch2-rehearsal-" + uuid.uuid4().hex[:8]
    definition.pop("users", None)
    try:
        async with session_factory() as session:
            await use_cases.load(session, pack.use_case())
            loaded = await load_definition(
                session, Definition.model_validate(definition), pack.PACK
            )
            pid = loaded.process.id
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", timeout=600
        ) as api:
            headers = await users.manager(api)
            response = await api.post(
                f"/processes/{pid}/sources/workbook",
                files={"file": (args.workbook.name, args.workbook.read_bytes())},
                data={"cut_off_date": "2026-09-19"},
            )
            assert response.status_code == 201, response.text
            sources = response.json()
            response = await api.post(f"/processes/{pid}/sources/erp/sync")
            assert response.status_code == 200, response.text
            assert response.json()["rows"] == 556, response.text
            erp_snapshot = response.json()
            version = await publish(api, pid, headers)
            paths = [
                p
                for batch in ("facturas", "facturas_primin")
                for p in sorted((args.data / batch).glob("*.pdf"))
            ]
            assert len(paths) == 540
            semaphore = asyncio.Semaphore(2)
            uploaded = []

            async def upload(path):
                async with semaphore:
                    response = await api.post(
                        f"/processes/{pid}/files", files={"file": (path.name, path.read_bytes())}
                    )
                    assert response.status_code == 201, (path.name, response.text)
                    record = response.json()
                    target = args.output / "uploads" / (path.name + ".json")
                    target.parent.mkdir(exist_ok=True)
                    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
                    uploaded.append({"file": path.name, "instance_id": record["instance_id"]})
                    print("uploaded", len(uploaded), path.name, flush=True)

            await asyncio.gather(*(upload(path) for path in paths))
            response = await api.post(f"/processes/{pid}/run")
            assert response.status_code == 200, response.text
            run = response.json()
            assert run["decided"] == 540 and not run.get("down_sources"), run
            response = await api.get(f"/processes/{pid}/export")
            assert response.status_code == 200, response.text
            (args.output / "outcomes.jsonl").write_text(response.text, encoding="utf-8")
            outcomes = [json.loads(line) for line in response.text.splitlines()]
            assert len(outcomes) == 540
            assert {r["file_id"] for r in outcomes} == {p.name for p in paths}
            assert (await api.post(f"/processes/{pid}/run")).json()["decided"] == 0
            replays = {}
            for file in ("e13_P014.pdf", "e16_P011.pdf", "e18_P001.pdf", "factura_4635.pdf"):
                instance = next(row for row in uploaded if row["file"] == file)
                detail = (await api.get(f"/instances/{instance['instance_id']}")).json()
                did = detail["decisions"][-1]["id"]
                replay = await api.post(f"/decisions/{did}/replay")
                assert replay.status_code == 200 and replay.json()["matches"], replay.text
                replays[file] = replay.json()
            summary = {
                "process_id": pid,
                "version": version,
                "sources": sources,
                "erp": erp_snapshot,
                "run": run,
                "replays": replays,
            }
            (args.output / "summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
            print(json.dumps(run), flush=True)
    finally:
        erp.kill()
        erp.wait()
        app.dependency_overrides.pop(current_service, None)
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("data", "models", "env", "readers", "workbook", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    from dotenv import load_dotenv

    load_dotenv(args.env)
    os.environ.update(
        TRACEPAY_MODEL_DIR=str(args.models.resolve()), TRACEPAY_OCR_PROFILE="experimental"
    )
    args.output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(rehearse(args))


if __name__ == "__main__":
    main()
