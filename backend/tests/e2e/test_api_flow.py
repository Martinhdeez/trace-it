"""The whole invoice flow through the HTTP API and the real database. No LLM.

Loads the invoice process definition, gives its 16 rules Mateo's hand-written code (the
compiler is bypassed, TEST ONLY, see `app_adapter.inject_rule_code`), activates them through
the API, loads the real sources, and decides a sample of ~40 files that covers every trap
category. Ingestion and extraction do not exist yet, so instances carry the golden symbols.
"""

import json
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
            by_category.setdefault(part.split(":")[0].split(" ")[0], []).append(fid)
    chosen = {f for cat, fids in by_category.items() if cat != "clean" for f in fids[:PER_CATEGORY]}
    chosen |= set(by_category["DUPLICATE_PO"])
    clean = [f for f in by_category["clean"] if f not in chosen]
    return sorted(chosen | set(clean[: max(0, SAMPLE_SIZE - len(chosen))]))


def test_the_sample_covers_every_trap_category() -> None:
    files = sample()
    categories = {
        part.split(":")[0].split(" ")[0]
        for row in golden.expected().values()
        if row["expected"] is not None
        for part in row["why"].split("; ")
    }
    covered = {
        part.split(":")[0].split(" ")[0]
        for fid in files
        for part in golden.expected()[fid]["why"].split("; ")
    }
    assert covered == categories
    assert 35 <= len(files) <= 45
    assert {golden.expected()[f]["expected"] for f in files} == {"PAGAR", "NO_PAGAR", "ESCALAR"}


async def test_decide_review_and_export_through_the_api() -> None:
    files = sample()
    expected = {f: golden.expected()[f]["expected"] for f in files}
    symbols = {s["file_id"]: s for s in golden.symbols() if s["file_id"] in expected}
    suffix = uuid.uuid4().hex[:8]

    defn = adapter.definition()
    defn["nombre"] = f"{defn['nombre']} e2e-{suffix}"
    defn.pop("usuarios", None)
    code_by_text = {
        spec.text: code
        for spec, code in zip(adapter.rules(defn), adapter.REFERENCE_CODE, strict=True)
    }

    async with AsyncClient(transport=ASGITransport(app=adapter.app), base_url="http://t") as api:
        approver = await adapter.create_user(
            api, "Approver", f"approver-{suffix}@e2e.test", "responsable"
        )
        process_id = await adapter.load_definition(api, defn)

        # TEST ONLY: the compiler is bypassed. Activation goes through the real endpoint.
        await adapter.inject_rule_code(process_id, code_by_text)
        await adapter.load_sources(process_id, challenge.sources())
        rules = await adapter.list_rules(api, process_id)
        assert len(rules) == 16
        for rule in rules:
            assert await adapter.activate_rule(api, rule["id"], approver) == "activa"

        await adapter.add_instances(
            process_id,
            {f: ((challenge.INVOICES / f).read_bytes(), symbols[f]) for f in files},
        )

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
        assert engine["author"] == "motor"
        assert engine["decision"] == "ESCALAR"
        assert len(engine["results"]) == 16

        # A person resolves it. The engine's decision stays, the person's is appended.
        after = await adapter.resolve(api, case_id, "NO_PAGAR", "Paid the first one", approver)
        assert [(h["author"], h["decision"]) for h in after] == [
            ("motor", "ESCALAR"),
            ("Approver", "NO_PAGAR"),
        ]

        lines = await adapter.export(api, process_id)
        assert len(lines) == len(files)
        assert sorted(line["file_id"] for line in lines) == files
        assert all(set(line) >= {"file_id", "result"} for line in lines)
        exported = {line["file_id"]: line["result"] for line in lines}
        assert {f: exported[f] for f in files if f != case} == {
            f: d for f, d in expected.items() if f != case
        }
        # file_id survives byte for byte, accents included.
        assert any("í" in f or "é" in f for f in exported), json.dumps(files)

        if after[-1]["human_kind"] == "<absent>":
            pytest.skip(
                "PR #17 not merged: the export still returns a person's resolution "
                f"({exported[case]}) instead of the engine decision (ESCALAR)"
            )
        assert exported[case] == "ESCALAR"
