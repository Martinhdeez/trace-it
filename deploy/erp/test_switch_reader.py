from copy import deepcopy

import pytest
from switch_reader import switch_reader


def client(*, existing_draft=False, unexpected_change=False, valid=True):
    settings = {"preset": "custom", "extraction": {"vision_model": "gemini:old"}}
    original = {
        "process": {"id": 1},
        "rules": ["keep"],
        "execution": deepcopy(settings),
    }
    calls = []

    def request(path, extra=(), body=None):
        calls.append(path)
        if path.endswith("/execution"):
            return {
                "settings": deepcopy(settings),
                "version_id": 1,
                "revision": 9 if existing_draft else None,
            }
        if path == "/process-versions/1":
            return {"snapshot": deepcopy(original)}
        if path.endswith("/draft"):
            snapshot = deepcopy(original)
            snapshot["execution"] = body["execution"]
            if unexpected_change:
                snapshot["rules"] = ["changed"]
            return {"snapshot": snapshot, "revision": 1, "base_version_id": 1}
        if path.endswith("/validate"):
            return {"revision": 1, "validation": {"valid": valid, "hash": "checked"}}
        assert path.endswith("/publish") and body["validation_hash"] == "checked"
        return {
            "number": 2,
            "snapshot": {
                "execution": {"extraction": {"vision_model": "helmcode:qwen3.6"}}
            },
        }

    return request, calls, original


def test_reader_migration_publishes_only_after_validation():
    request, calls, original = client()
    switch_reader(request, 1)
    assert calls[-2:] == ["/processes/1/draft/validate", "/processes/1/draft/publish"]
    assert original["execution"]["extraction"]["vision_model"] == "gemini:old"


@pytest.mark.parametrize(
    "options", [{"existing_draft": True}, {"unexpected_change": True}, {"valid": False}]
)
def test_reader_migration_preserves_drafts_and_rejects_unreviewed_changes(options):
    request, calls, _ = client(**options)
    with pytest.raises(SystemExit):
        switch_reader(request, 1)
    assert not any(path.endswith("/publish") for path in calls)
