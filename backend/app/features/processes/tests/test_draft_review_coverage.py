"""The reviewer preview only receives historical cases evaluable under a new schema."""

from app.features.learning import evidence, validation
from app.features.processes import draft_compilation
from app.features.versions import execution


async def test_reviewer_preview_excludes_incomplete_cases_before_comparison(monkeypatch):
    captured = {
        "instances": [
            {"id": 1, "name": "old", "symbols": {"old": {"value": 1, "origin": "test"}}},
            {"id": 2, "name": "ready", "symbols": {"new": {"value": 2, "origin": "test"}}},
        ],
        "decisions": [
            {"id": 10, "instance_id": 1, "author": "engine", "decision": "CHECK"},
            {"id": 20, "instance_id": 2, "author": "engine", "decision": "PAY"},
        ],
        "reviews": [],
        "prompts": {"decision_reviewer": "Review"},
        "sources": [],
    }
    monkeypatch.setattr(evidence, "capture", lambda *_: async_value(captured))
    monkeypatch.setattr(execution, "evaluate", lambda *_, **__: async_value({}))
    observed = []

    async def compare(before, after):
        observed.extend((before, after))
        assert [case["id"] for case in evidence.cases(before, 10)] == [2]
        assert [case["id"] for case in evidence.cases(after, 10)] == [2]
        return {"valid": True, "previews": []}

    monkeypatch.setattr(validation, "compare_reviews", compare)
    config = {
        "execution": {},
        "process": {},
        "rules": [],
        "guidance": {},
        "agents": {},
        "reviewer_prompt": "Review",
    }
    result = await draft_compilation.review_preview(
        None, 1, config, config, {}, {}, excluded_ids={1}
    )
    assert result["valid"] and len(observed) == 2


async def async_value(value):
    return value
