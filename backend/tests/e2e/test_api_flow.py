"""The whole invoice flow through the HTTP API and the real database. No LLM.

Loads the invoice pack the way `python -m app.cli load` does, so its 16 rules arrive with
Mateo's hand-written code from `processes/rules-v3/` and no compiler runs. Activates them
through the API, loads the real sources, and decides a sample of ~40 files that covers every
trap category. Ingestion and extraction do not exist yet, so instances carry the golden
symbols.
"""

import uuid
from collections import Counter

import pytest
from httpx import ASGITransport, AsyncClient

from tests.golden import golden
from tests.support import app_adapter as adapter
from tests.support import challenge

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


async def test_decide_review_and_export_through_the_api() -> None:
    files = sample()
    expected = {f: golden.expected()[f]["expected"] for f in files}
    symbols = {s["file_id"]: s for s in golden.symbols() if s["file_id"] in expected}
    suffix = uuid.uuid4().hex[:8]

    defn = adapter.definition()
    defn["name"] = f"{defn['name']} e2e-{suffix}"
    defn.pop("users", None)
    process_id = await adapter.load_pack(defn)
    await adapter.load_sources(process_id, challenge.sources())
    await adapter.add_instances(
        process_id, {f: ((challenge.INVOICES / f).read_bytes(), symbols[f]) for f in files}
    )

    async with AsyncClient(transport=ASGITransport(app=adapter.app), base_url="http://t") as api:
        manager = await adapter.create_user(api, "Manager", f"manager-{suffix}@e2e.test", "manager")
        rules = await adapter.list_rules(api, process_id)
        assert len(rules) == 16
        for rule in rules:
            assert await adapter.activate_rule(api, rule["id"], manager) == "active"

        summary = await adapter.run_process(api, process_id)
        assert summary == dict(Counter(expected.values()))

        instances = await adapter.list_instances(api, process_id)
        got = {name: i["decision"] for name, i in instances.items()}
        wrong = {f: (expected[f], got.get(f)) for f in files if got.get(f) != expected[f]}
        assert not wrong, f"file: (expected, got): {wrong}"

        escalated = sorted(f for f, d in expected.items() if d == "ESCALAR")
        assert sorted(await adapter.queue(api, process_id)) == escalated

        # Every rule's answer is recorded, not only the ones that fired.
        case = escalated[0]
        case_id = instances[case]["id"]
        [engine] = await adapter.history(api, case_id)
        assert engine["author"] == adapter.ENGINE_AUTHOR
        assert engine["decision"] == "ESCALAR"
        assert len(engine["results"]) == 16

        # A person resolves it. The engine's decision stays; the person's is appended.
        after = await adapter.resolve(api, case_id, "NO_PAGAR", "Paid the first one", manager)
        assert [(h["author"], h["decision"], h["human_kind"]) for h in after] == [
            (adapter.ENGINE_AUTHOR, "ESCALAR", None),
            ("Manager", "NO_PAGAR", "resolution"),
        ]

        lines = await adapter.export(api, process_id)
        assert len(lines) == len(files)
        assert sorted(line["file_id"] for line in lines) == files  # accents survive
        assert all(set(line) >= {"file_id", "result"} for line in lines)
        # The export is the engine's decision, even for the case a person resolved.
        assert {line["file_id"]: line["result"] for line in lines} == expected
