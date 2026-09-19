"""The whole invoice flow through the HTTP API and the real database. No LLM.

Loads the invoice pack the way `python -m app.cli load` does, so its 16 rules arrive with
the hand-written code from `processes/rules-v3/` and no compiler runs. Activates them
through the API, loads the real sources, and decides a sample of ~40 files that covers every
trap category. Ingestion and extraction do not exist yet, so instances carry the golden
symbols.
"""

import hashlib
import json
import uuid
from collections import Counter
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import session_factory
from app.features.ingestion.model import File, Instance
from app.features.processes.definition import Definition, load_definition
from app.features.sources.model import Source
from app.features.sources.tests.conftest import start_erp
from app.features.use_cases import service as use_cases
from app.main import app
from tests.golden import golden
from tests.support import challenge, pack

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not challenge.available(), reason="challenge submodule not checked out"),
]

PER_CATEGORY = 3
SAMPLE_SIZE = 40


def category(part: str) -> str:
    """`AMOUNT_NE_PO: 1 vs 2` -> `AMOUNT_NE_PO`; `INJECTED_TEXT ignored: ...` -> `INJECTED_TEXT`."""
    return part.split(":")[0].split(" ")[0]


def sample() -> list[str]:
    """Up to three files per finding in the golden `why`, then clean ones up to 40.

    Deterministic. Both files of a duplicated order are always in, or the pair would not
    be a duplicate inside the sample.
    """
    rows = {
        fid: row
        for fid, row in golden.expected().items()
        if row["expected"] is not None and fid not in golden.KNOWN_MISMATCHES
    }
    by_category: dict[str, list[str]] = {}
    for fid, row in sorted(rows.items()):
        for part in row["why"].split("; "):
            by_category.setdefault(category(part), []).append(fid)
    chosen = {f for c, fids in by_category.items() if c != "clean" for f in fids[:PER_CATEGORY]}
    chosen |= set(by_category["DUPLICATE_PO"])
    clean = [f for f in by_category["clean"] if f not in chosen]
    return sorted(chosen | set(clean[: max(0, SAMPLE_SIZE - len(chosen))]))


def test_the_sample_covers_every_trap_category() -> None:
    expected = golden.expected()
    files = sample()
    categories = {
        category(part)
        for row in expected.values()
        if row["expected"] is not None
        for part in row["why"].split("; ")
    }
    covered = {category(part) for f in files for part in expected[f]["why"].split("; ")}
    assert covered == categories
    assert 35 <= len(files) <= 45
    assert {expected[f]["expected"] for f in files} == {"PAGAR", "NO_PAGAR", "ESCALAR"}


async def load(defn: dict[str, Any], files: dict[str, dict[str, Any]]) -> int:
    """What the CLI loader, the source connectors and extraction do: the pack with its code
    files, the real sources, and one instance per file with the golden symbols stored as
    extraction writes them."""
    async with session_factory() as session:
        await use_cases.load(session, pack.use_case())
        result = await load_definition(session, Definition.model_validate(defn), pack.PACK)
        process_id = result.process.id
        for name, rows in challenge.sources().items():
            session.add(Source(process_id=process_id, name=name, origin="tests", rows=rows))
        for name, values in files.items():
            content = (challenge.INVOICES / name).read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if await session.get(File, digest) is None:
                session.add(File(hash=digest, name=name, content=content, text=None))
            symbols = {k: {"value": v, "origin": "golden"} for k, v in values.items()}
            session.add(
                Instance(process_id=process_id, file_hash=digest, name=name, symbols=symbols)
            )
        await session.commit()
    return process_id


async def test_decide_resolve_and_export_through_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ERP is live: the run syncs it first (ADR 0028) and decides on what it served."""
    erp, url = start_erp()
    try:
        monkeypatch.setenv("TRACE_ERP_URL", url)
        monkeypatch.setenv("TRACE_ERP_USER", "alberto")
        monkeypatch.setenv("TRACE_ERP_PASSWORD", "FACTURAS2009")
        await decide_resolve_and_export()
    finally:
        erp.kill()
        erp.wait()


async def decide_resolve_and_export() -> None:
    files = sample()
    expected = {f: golden.expected()[f]["expected"] for f in files}
    symbols = {s["file_id"]: s for s in golden.symbols() if s["file_id"] in expected}
    suffix = uuid.uuid4().hex[:8]

    defn = pack.definition()
    defn["name"] = f"{defn['name']} e2e-{suffix}"
    defn.pop("users", None)
    process_id = await load(defn, symbols)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as api:
        r = await api.post(
            "/users",
            json={"name": "Manager", "email": f"manager-{suffix}@e2e.test", "role": "manager"},
        )
        manager = {"X-User-Id": str(r.json()["id"])}
        rules = (await api.get(f"/processes/{process_id}/rules")).json()
        assert len(rules) == 17
        for rule in rules:
            r = await api.post(f"/rules/{rule['id']}/activate", headers=manager)
            assert r.status_code == 200, r.text

        from app.features.versions.tests.test_api import publish

        await publish(api, process_id, manager)
        r = await api.post(f"/processes/{process_id}/run")
        assert r.status_code == 200, r.text
        assert "down_sources" not in r.json()
        assert r.json()["by_decision"] == dict(Counter(expected.values()))
        erp = next(
            s
            for s in (await api.get(f"/processes/{process_id}/sources")).json()
            if s["name"] == "erp"
        )
        assert (erp["status"], erp["rows"]) == ("ok", 516) and erp["origin"].startswith("erp:")

        instances = {
            i["name"]: i for i in (await api.get(f"/processes/{process_id}/instances")).json()
        }
        got = {name: i["decision"] for name, i in instances.items()}
        wrong = {f: (expected[f], got.get(f)) for f in files if got.get(f) != expected[f]}
        assert not wrong, f"file: (expected, got): {wrong}"

        escalated = sorted(f for f, d in expected.items() if d == "ESCALAR")
        queue = (await api.get(f"/processes/{process_id}/queue")).json()
        assert sorted(i["name"] for i in queue) == escalated

        # Every rule's answer is recorded, not only the ones that fired.
        case_id = instances[escalated[0]]["id"]
        [engine] = (await api.get(f"/instances/{case_id}")).json()["decisions"]
        assert (engine["author"], engine["decision"], len(engine["results"])) == (
            "engine",
            "ESCALAR",
            17,
        )

        # A person resolves it. The engine's decision stays; the person's is appended.
        r = await api.post(
            f"/instances/{case_id}/resolve",
            json={"decision": "NO_PAGAR", "reason": "Paid the first one"},
            headers=manager,
        )
        assert r.status_code == 200, r.text
        assert [(h["author"], h["decision"]) for h in r.json()["decisions"]] == [
            ("engine", "ESCALAR"),
            ("Manager", "NO_PAGAR"),
        ]

        r = await api.get(f"/processes/{process_id}/export")
        assert r.status_code == 200, r.text
        lines = [json.loads(line) for line in r.text.splitlines()]
        assert sorted(line["file_id"] for line in lines) == files  # accents survive
        # The export is the engine's decision, even for the case a person resolved.
        assert {line["file_id"]: line["result"] for line in lines} == expected
