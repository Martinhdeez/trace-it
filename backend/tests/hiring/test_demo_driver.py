"""The hiring demo driver speaks the discovery contract: the proposal keys it reviews are
the ones `prepare` demands, and it never decides in the manager's place."""

import runpy
from pathlib import Path

import httpx
import pytest

from app.features.processes import draft_compilation
from app.features.processes.draft_schemas import DraftPlan

ROOT = Path(__file__).resolve().parents[3]
DEMO = runpy.run_path(str(ROOT / "tools" / "hiring_demo.py"))

PLAN = {
    "name": "Hiring screening",
    "summary": "Screen CVs.",
    "decision_types": [
        {"name": "REVIEW", "priority": 3, "requires_human": True},
        {"name": "REJECT", "priority": 2},
        {"name": "INTERVIEW", "priority": 1, "is_default": True},
    ],
    "symbols": [{"name": "email", "type": "text", "required": True}],
    "sources": [
        {
            "name": "positions",
            "explanation": "Open roles",
            "evidence": [{"reference": "abc:positions!A1", "explanation": "header"}],
            "kind": "workbook",
            "document": "abc",
            "sheet": "positions",
            "first_row": 2,
            "last_row": 9,
            "columns": {"code": "A"},
        }
    ],
    "rules": [
        {
            "name": "known-position",
            "text": "`position_code` is a `code` in `positions`.",
            "type": "requirement",
            "decision": "REVIEW",
            "evidence": [{"reference": "chat:1", "explanation": "point 1"}],
        }
    ],
    "guidance": [
        {
            "name": "gaps",
            "text": "Career gaps deserve a look.",
            "evidence": [{"reference": "chat:1", "explanation": "point 9"}],
        }
    ],
    "examples": [
        {
            "name": "unknown-code",
            "instance": {"email": "a@example.com", "position_code": "X"},
            "decision": "REVIEW",
            "explanation": "Nobody knows X.",
        }
    ],
    "questions": [],
}


def test_driver_reviews_exactly_the_proposals_prepare_requires():
    plan = DraftPlan.model_validate(PLAN)
    assert DEMO["proposal_keys"](PLAN) == draft_compilation.proposals(plan)
    for key in DEMO["proposal_keys"](PLAN):
        assert DEMO["proposal_summary"](PLAN, key)


def test_auto_manager_sends_the_notes_then_defers_to_the_policy_thread():
    """The scripted manager must not invent policy: a blunt follow-up once made the agent
    soften two checks the thread settles, so it now points back at the thread."""
    manager = DEMO["Manager"](auto=True, notes="NOTES")
    assert manager.answer(["What is the screening date?"], 1) == "NOTES"
    follow_up = manager.answer(["Still unsure"], 2)
    assert follow_up != "NOTES" and "policy thread" in follow_up
    assert "do not soften" in follow_up
    assert manager.review("rule:known-position", "...") == ("accepted", "Accepted as proposed.")


def test_totals_add_up_what_the_llm_run_spans_recorded():
    spans = [
        {
            "id": 1,
            "step": "llm_run",
            "status": "ok",
            "trace_id": "t1",
            "duration_ms": 1500,
            "data": {
                "agent": "discovery",
                "model": "deepseek",
                "requests": 2,
                "retries": 1,
                "input_tokens": 10,
                "output_tokens": 5,
                "cached_tokens": 3,
                "failed_attempts": [{"model": "a", "error": "503"}],
            },
        },
        {"id": 2, "step": "upload_document", "status": "ok", "trace_id": "t2", "data": {}},
    ]
    assert DEMO["model_calls"](spans) == [spans[0]]
    assert DEMO["totals"]([spans[0]]) == {
        "calls": 1,
        "requests": 2,
        "retries": 1,
        "input_tokens": 10,
        "output_tokens": 5,
        "cached_tokens": 3,
        "seconds": 1.5,
        "failed_over": 1,
    }


def test_trace_tables_name_the_model_the_fallback_and_the_failed_steps(tmp_path):
    report = DEMO["Report"](tmp_path / "r.md")
    spans = [
        {
            "id": 1,
            "step": "llm_run",
            "status": "ok",
            "trace_id": "abcdef123456789",
            "duration_ms": 900,
            "data": {
                "agent": "discovery",
                "model": "deepseek-v4",
                "requests": 1,
                "retries": 0,
                "input_tokens": 7,
                "output_tokens": 2,
                "failed_attempts": [{"model": "glm5.3", "error": "timeout"}],
            },
        },
        {
            "id": 2,
            "step": "upload_document",
            "status": "error",
            "trace_id": "z",
            "duration_ms": 10,
            "data": {"file": "cv-001.pdf"},
        },
    ]
    DEMO["agent_table"](report, spans, "Round 1")
    text = "\n".join(report.lines)
    assert "deepseek-v4" in text and "abcdef123456" in text
    assert "fell back after glm5.3: timeout" in text
    assert "ERROR span `upload_document`" in text

    other = DEMO["Report"](tmp_path / "s.md")
    DEMO["step_table"](other, spans, "Batch")
    text = "\n".join(other.lines)
    assert "`llm_run` | 1 | 900 | 0" in text
    assert "`upload_document` | 1 | 10 | 1" in text


def test_plain_symbols_accept_both_stored_and_flat_shapes():
    plain = DEMO["plain"]
    assert plain({"email": {"value": "a@b", "origin": "document:1"}, "n": "5"}) == {
        "email": "a@b",
        "n": "5",
    }
    assert plain(None) == {}


async def test_login_creates_the_manager_only_when_the_email_is_unknown(tmp_path):
    calls = []

    def respond(request):
        calls.append((request.method, request.url.path))
        if request.url.path == "/login":
            return httpx.Response(404, json={"code": "not_found", "message": "No user"})
        assert request.url.path == "/users"
        assert b'"role":"manager"' in request.read()
        return httpx.Response(
            201, json={"id": 9, "name": "Marta", "email": "m@x", "role": "manager"}
        )

    report = DEMO["Report"](tmp_path / "report.md")
    api = DEMO["Api"]("http://test", report)
    api.http = httpx.AsyncClient(transport=httpx.MockTransport(respond), base_url="http://test")
    user = await api.login("m@x", "Marta")
    assert user["id"] == 9
    assert api.http.headers["X-User-Id"] == "9"
    assert calls == [("POST", "/login"), ("POST", "/users")]
    assert report.friction == []  # the expected 404 is not friction


@pytest.mark.parametrize("status", [409, 502])
async def test_http_errors_are_logged_verbatim_and_raised(tmp_path, status):
    def respond(request):
        return httpx.Response(status, json={"code": "x", "message": "boom"})

    report = DEMO["Report"](tmp_path / "report.md")
    api = DEMO["Api"]("http://test", report)
    api.http = httpx.AsyncClient(transport=httpx.MockTransport(respond), base_url="http://test")
    with pytest.raises(DEMO["ApiError"]):
        await api.call("POST", "/process-drafts/1/prepare", json={"revision": 1})
    assert report.friction and str(status) in report.friction[0] and "boom" in report.friction[0]
    report.write(["# t"])
    assert "boom" in (tmp_path / "report.md").read_text()
