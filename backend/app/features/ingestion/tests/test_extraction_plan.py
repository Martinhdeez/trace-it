"""The plan follows published configuration, or live bootstrap inputs."""

import pytest
from pydantic import ValidationError

from app.features.ingestion import extraction_plan
from app.features.ingestion.extraction_plan import (
    ExtractionField,
    ExtractionPlan,
    load_extraction_plan,
)
from app.features.processes.schemas import SymbolIO


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Session:
    def __init__(self, symbols, rules):
        self.symbols = symbols
        self.rules = rules
        self.calls = 0
        self.active_version_id = None
        self.published = None

    async def scalar(self, statement):
        if "processes.active_version_id" in str(statement):
            return self.active_version_id
        return self.published

    async def execute(self, _statement):
        self.calls += 1
        return _Rows(self.symbols if self.calls % 2 else self.rules)


async def test_published_plan_ignores_unpublished_inputs_and_tracks_new_version() -> None:
    session = _Session([("live", "text", "", False, None)], [])
    session.active_version_id = 10
    session.published = {
        "process": {
            "symbols": [
                {
                    "name": "approved",
                    "type": "date",
                    "description": "Approved date",
                    "required": True,
                    "extraction": {"labels": ["Valid until"], "source": "document"},
                }
            ]
        },
        "rules": [],
    }
    first = await load_extraction_plan(session, 42)
    assert [field.name for field in first.fields] == ["approved"]
    assert first.fields[0].labels == ["Valid until"]
    session.symbols = [("draft_only", "number", "", False, None)]
    assert (await load_extraction_plan(session, 42)).fingerprint == first.fingerprint
    assert session.calls == 0

    # Simulate a later committed publication while retaining the same session.
    session.active_version_id = 11
    session.published = {
        **session.published,
        "process": {
            "symbols": [
                {
                    "name": "approved",
                    "type": "date",
                    "extraction": {"labels": ["Expires on"], "source": "document"},
                },
                {"name": "draft_only", "type": "number"},
            ]
        },
    }
    second = await load_extraction_plan(session, 42)
    assert second.field_fingerprint != first.field_fingerprint
    assert [field.name for field in second.fields] == ["approved", "draft_only"]
    assert second.fields[0].labels == ["Expires on"]


async def test_published_rule_code_invalidates_analysis_even_with_same_rule_hash() -> None:
    session = _Session([], [])
    session.active_version_id = 20
    session.published = {
        "process": {"symbols": [{"name": "approved", "type": "text"}]},
        "rules": [
            {
                "id": 3,
                "hash": "unchanged",
                "status": "active",
                "code": "def evaluate(i, s, o):\n    return i['approved']",
            }
        ],
    }
    first = await load_extraction_plan(session, 9)
    session.published["rules"][0]["code"] = "def evaluate(i, s, o):\n    return i['new_key']"
    second = await load_extraction_plan(session, 9)
    assert first.field_fingerprint == second.field_fingerprint
    assert first.rule_fingerprint != second.rule_fingerprint
    assert second.warnings == [
        {"code": "SCHEMA_UNDECLARED_SYMBOL", "rule_id": 3, "symbol": "new_key"}
    ]


async def test_plan_reads_current_symbols_and_rule_dependencies() -> None:
    session = _Session(
        [
            ("expiry_date", "date", "Date of expiry", True, {"labels": ["Válido hasta"]}),
            ("file_id", "text", "", False, None),
            ("free_text", "text", "", False, None),
        ],
        [
            (
                7,
                "rule-hash",
                "active",
                "def evaluate(instance, sources, others):\n"
                '    return instance["expiry_date"] and instance.get("missing") '
                'and sources.get("erp")',
            ),
            (8, None, "blocked", None),
        ],
    )
    first = await load_extraction_plan(session, 42)
    assert [field.name for field in first.fields] == ["expiry_date", "file_id", "free_text"]
    assert [field.source for field in first.fields] == ["document", "filename", "text"]
    assert first.fields[0].labels == ["Válido hasta"]
    assert first.rules[0]["instance_keys"] == ["expiry_date", "missing"]
    assert first.rules[0]["source_keys"] == ["erp"]
    assert first.warnings == [
        {"code": "SCHEMA_UNDECLARED_SYMBOL", "rule_id": 7, "symbol": "missing"}
    ]
    assert "missing" not in [field.name for field in first.fields]

    session.symbols[0] = ("expiry_date", "date", "Date of expiry", True, {"labels": ["Caduca el"]})
    second = await load_extraction_plan(session, 42)
    assert second.fingerprint != first.fingerprint
    session.rules[0] = (
        7,
        "rule-hash",
        "active",
        "def evaluate(instance, sources, others):\n    return instance.get('expiry_date')",
    )
    third = await load_extraction_plan(session, 42)
    assert third.fingerprint != second.fingerprint
    assert third.warnings == []


def test_plan_fingerprint_is_deterministic_and_metadata_is_bounded() -> None:
    field = ExtractionField(name="amount", type="number")
    plan = ExtractionPlan(process_id=1, fields=[field], rules=[{"id": 3, "status": "active"}])
    assert plan.fingerprint == ExtractionPlan.model_validate(plan.model_dump()).fingerprint
    assert len(plan.fingerprint) == 64
    assert SymbolIO(name="x", type="text").extraction is None
    with pytest.raises(ValidationError):
        SymbolIO(name="x", type="text", extraction={"labels": ["x"] * 13})


async def test_rule_analysis_cache_tracks_content_and_returns_independent_plans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extraction_plan._analyze_snapshot.cache_clear()
    calls = 0
    original = extraction_plan.read_keys

    def counted(code: str):
        nonlocal calls
        calls += 1
        return original(code)

    monkeypatch.setattr(extraction_plan, "read_keys", counted)
    session = _Session(
        [("amount", "number", "", False, None)],
        [(1, "unchanged-hash", "active", "def evaluate(i, s, o):\n    return i['amount']")],
    )
    first = await load_extraction_plan(session, 1)
    first.fields[0].name = "mutated"
    second = await load_extraction_plan(session, 1)
    assert calls == 1
    assert second.fields[0].name == "amount"
    assert first.field_fingerprint != second.field_fingerprint

    # The stored rule hash may be stale; code itself must invalidate the analysis.
    session.rules[0] = (
        1,
        "unchanged-hash",
        "active",
        "def evaluate(i, s, o):\n    return i['new_key']",
    )
    third = await load_extraction_plan(session, 1)
    assert calls == 2
    assert third.rules[0]["instance_keys"] == ["new_key"]
    assert third.field_fingerprint == second.field_fingerprint
    assert third.rule_fingerprint != second.rule_fingerprint
    assert third.fingerprint != second.fingerprint

    session.symbols[0] = ("amount", "number", "", False, {"labels": ["Importe"]})
    revised = await load_extraction_plan(session, 1)
    assert calls == 3
    assert revised.field_fingerprint != third.field_fingerprint
    assert revised.rule_fingerprint == third.rule_fingerprint

    other = await load_extraction_plan(session, 2)
    assert calls == 4
    assert other.process_id == 2
