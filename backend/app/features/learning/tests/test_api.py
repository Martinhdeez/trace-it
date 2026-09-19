"""Learning through the API, real sandbox and database, scripted agents only."""

import json

import pytest
from sqlalchemy import select

from app.core.database import session_factory
from app.features.agents import llm
from app.features.decisions.tests.test_api import (
    REAL_IBAN_RULE,
    REAL_PAID_RULE,
    client,
    create_process,
)
from app.features.decisions.tests.test_reviews import answer, configure
from app.features.learning.model import Analysis
from app.features.rules.model import Rule
from app.features.sources.model import Source
from tests.support.models import down, per_role, user_json
from tests.support.users import anonymous

TEXT = "Escalate invoices whose nif is B96233419 for verification."
CODE = """def evaluate(instance, sources, others):
    return {"fires": instance["nif"] == "B96233419", "reason": "VERIFY_SUPPLIER"}
"""
GUIDANCE = "Consider the consequences of rejection when evidence is ambiguous."


def norm(kind, text, ref):
    return {
        "kind": kind,
        "text": text,
        "reasoning": "Repeated cases need supplier verification.",
        "evidence": [ref],
        "counterexamples": [],
        "limitations": "Small sample; manager approval required.",
    }


def scripts():
    tests = [
        {
            "name": f"case-{i}",
            "instance_json": json.dumps({"nif": value}),
            "sources_json": "{}",
            "others_json": "[]",
            "fires": value == "B96233419",
        }
        for i, value in enumerate(["B96233419", "B78451236", "", "OTHER", "B96233419", "X"])
    ]
    return {
        "normalizer": [
            {
                "norm_rules": [
                    {
                        "number": 1,
                        "text": TEXT,
                        "checks": [
                            {
                                "text": TEXT,
                                "type": "prohibition",
                                "decision": "ESCALAR",
                                "decision_source": "explicit",
                                "quote": "Escalate",
                                "interpretation": "Verification is required for this supplier.",
                            }
                        ],
                    }
                ]
            }
        ],
        "tester": [{"tests": tests}],
        "compiler": [{"code": CODE}],
    }


async def seed(api):
    pid, headers = await create_process(
        api,
        "manager",
        {
            "iban_mismatch": ("ESCALAR", REAL_IBAN_RULE),
            "order_already_paid": ("NO_PAGAR", REAL_PAID_RULE),
        },
    )
    assert (await api.post(f"/processes/{pid}/run")).status_code == 200
    cases = (await api.get(f"/processes/{pid}/instances")).json()
    ref = f"case:{next(c['id'] for c in cases if c['decision'] == 'PAGAR')}"
    return pid, headers, ref


async def propose(api, monkeypatch, pid, headers, ref, kind="deterministic", seen=None):
    monkeypatch.setattr(
        llm,
        "model_for",
        per_role(
            {
                "learner": [
                    {
                        "reasoning": "Review found a pattern.",
                        "proposals": [
                            norm(kind, TEXT if kind == "deterministic" else GUIDANCE, ref)
                        ],
                    }
                ]
            },
            seen,
        ),
    )
    response = await api.post(f"/processes/{pid}/learning", json={}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["proposals"][0]["id"]


async def prepare(api, monkeypatch, proposal_id, headers, replies=None):
    monkeypatch.setattr(llm, "model_for", per_role(replies or scripts()))
    response = await api.post(f"/norm-proposals/{proposal_id}/validate", headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def approve(api, proposal_id, validation_id, headers):
    result = await api.post(
        f"/norm-proposals/{proposal_id}/approve",
        headers=headers,
        json={"validation_id": validation_id, "reason": "Reviewed examples and impact."},
    )
    if result.status_code == 201:
        key = result.json()["snapshot"]["version_id"]
        version = (await api.get(f"/process-versions/{key}")).json()
        assert version["author"] == result.json()["author"]
        assert version["parent_id"] is not None
    return result


async def test_deterministic_norm_prepares_then_publishes_exact_code(monkeypatch):
    async with client() as api:
        pid, headers, ref = await seed(api)
        before = (await api.get(f"/processes/{pid}/instances")).json()
        seen = {}
        prop = await propose(api, monkeypatch, pid, headers, ref, seen=seen)
        context = user_json(seen["learner"][0])
        assert ref in context["evidence"]
        assert len([key for key in context["evidence"] if key.startswith("case:")]) == 3
        validation = await prepare(api, monkeypatch, prop, headers)
        assert validation["report"]["valid"], validation
        assert len(validation["report"]["impact"]["changes"]) == 2
        assert len((await api.get(f"/processes/{pid}/rules")).json()) == 2
        assert (await api.get(f"/processes/{pid}/instances")).json() == before
        response = await approve(api, prop, validation["id"], headers)
        assert response.status_code == 201, response.text
        adoption = response.json()
        assert adoption["approved"] and adoption["author"] == "Ana"
        [rid] = adoption["snapshot"]["rule_ids"]
        rule = (await api.get(f"/rules/{rid}")).json()
        assert rule["code"] == CODE and rule["status"] == "active"
        assert rule["report"]["learning"]["proposal_id"] == prop
        assert len(rule["tests"]) == 6
        assert (await api.get(f"/processes/{pid}/instances")).json() == before
        assert (await approve(api, prop, validation["id"], headers)).status_code == 409
        assert (
            await api.post(f"/norm-proposals/{prop}/validate", headers=headers)
        ).status_code == 409
        impact = (await api.post(f"/processes/{pid}/reprocess?dry_run=true")).json()
        assert len(impact["changes"]) == 2
        read = (await api.get(f"/norm-proposals/{prop}", headers=headers)).json()
        assert read["adoption"] == adoption and read["validations"] == [validation]
        analyses = (await api.get(f"/processes/{pid}/learning", headers=headers)).json()
        assert analyses[0]["proposals"][0] == read


async def test_human_conflict_prevents_adoption(monkeypatch):
    async with client() as api:
        pid, headers, ref = await seed(api)
        response = await api.post(
            f"/instances/{ref.split(':')[1]}/resolve",
            headers=headers,
            json={"decision": "PAGAR", "reason": "Verified this supplier; payment is appropriate."},
        )
        assert response.status_code == 200
        prop = await propose(api, monkeypatch, pid, headers, ref)
        result = await prepare(api, monkeypatch, prop, headers)
        assert not result["report"]["valid"]
        assert len(result["report"]["impact"]["conflicts"]) == 1
        assert (await approve(api, prop, result["id"], headers)).status_code == 409


@pytest.mark.parametrize("change", ["source", "human"])
async def test_stale_preview_cannot_be_approved(monkeypatch, change):
    async with client() as api:
        pid, headers, ref = await seed(api)
        prop = await propose(api, monkeypatch, pid, headers, ref)
        result = await prepare(api, monkeypatch, prop, headers)
        if change == "source":
            async with session_factory() as session:
                session.add(Source(process_id=pid, name="erp", origin="updated", rows=[]))
                await session.commit()
        else:
            await api.post(
                f"/instances/{ref.split(':')[1]}/resolve",
                headers=headers,
                json={"decision": "PAGAR", "reason": "Confirmed after preview."},
            )
        response = await approve(api, prop, result["id"], headers)
        assert response.status_code == 409 and "changed" in response.text
        assert len((await api.get(f"/processes/{pid}/rules")).json()) == 2


async def test_missing_data_and_model_failure_stay_isolated(monkeypatch):
    async with client() as api:
        pid, headers, ref = await seed(api)
        prop = await propose(api, monkeypatch, pid, headers, ref)
        replies = scripts()
        replies["tester"] = [
            {
                "_output": "NeedsData",
                "missing": ["symbol:approval"],
                "explanation": "Need approval evidence.",
            }
        ]
        result = await prepare(api, monkeypatch, prop, headers, replies)
        assert not result["report"]["valid"]
        assert "needs_data" in result["report"]["rules"][0]["report"]
        assert len((await api.get(f"/processes/{pid}/rules")).json()) == 2
        monkeypatch.setattr(llm, "model_for", lambda role: down("unavailable"))
        response = await api.post(f"/norm-proposals/{prop}/validate", headers=headers)
        assert response.status_code == 201 and not response.json()["report"]["valid"]
        read = (await api.get(f"/norm-proposals/{prop}", headers=headers)).json()
        assert len(read["validations"]) == 2 and "error" in read["validations"][-1]["report"]
        assert (await approve(api, prop, result["id"], headers)).status_code == 409


async def test_guidance_only_reaches_reviewer_after_approval(monkeypatch):
    async with client() as api:
        pid, headers, ref = await seed(api)
        await configure(api, pid, {"guidance": "Explain uncertainty.", "timeout_seconds": 30})
        prop = await propose(api, monkeypatch, pid, headers, ref, "guidance")
        before = (await api.get(f"/instances/{ref.split(':')[1]}")).json()
        seen = {}
        monkeypatch.setattr(
            llm,
            "model_for",
            per_role({"decision_reviewer": [answer("PAGAR"), answer("ESCALAR")] * 3}, seen),
        )
        response = await api.post(f"/norm-proposals/{prop}/validate", headers=headers)
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["report"]["valid"] and len(result["report"]["previews"]) == 3
        assert "proposed_norm" not in user_json(seen["decision_reviewer"][0])["evidence"]
        assert user_json(seen["decision_reviewer"][1])["evidence"]["proposed_norm"] == GUIDANCE
        assert (await api.get(f"/instances/{ref.split(':')[1]}")).json() == before
        response = await approve(api, prop, result["id"], headers)
        assert response.status_code == 201, response.text
        adopted = response.json()
        assert adopted["snapshot"]["guidance"] == {f"norm:{adopted['id']}": GUIDANCE}
        # Force a new engine decision through a changed ERP load, then inspect live review input.
        async with session_factory() as session:
            session.add(
                Source(
                    process_id=pid,
                    name="erp",
                    origin="changed",
                    rows=[
                        {"purchase_order": "PO-2026-0008", "status": "PAGADA"},
                        {"purchase_order": "PO-2026-0474", "status": "PAGADA"},
                        {"purchase_order": "PO-2026-0813", "status": "PENDIENTE"},
                    ],
                )
            )
            await session.commit()
        live = {}
        monkeypatch.setattr(
            llm, "model_for", per_role({"decision_reviewer": [answer("ESCALAR")]}, live)
        )
        assert (await api.post(f"/processes/{pid}/reprocess")).status_code == 200
        assert (
            user_json(live["decision_reviewer"][0])["evidence"][f"norm:{adopted['id']}"] == GUIDANCE
        )
        detail = (await api.get(f"/instances/{ref.split(':')[1]}")).json()
        assert detail["decision"] == "NO_PAGAR" and detail["review_pending"]


async def test_disabled_guidance_and_rejected_proposals_never_publish(monkeypatch):
    async with client() as api:
        pid, headers, ref = await seed(api)
        prop = await propose(api, monkeypatch, pid, headers, ref, "guidance")
        monkeypatch.setattr(llm, "model_for", lambda role: pytest.fail("Disabled reviewer called"))
        result = (await api.post(f"/norm-proposals/{prop}/validate", headers=headers)).json()
        assert not result["report"]["valid"]
        response = await api.post(
            f"/norm-proposals/{prop}/reject",
            headers=headers,
            json={"reason": "Insufficient evidence."},
        )
        assert response.status_code == 201 and not response.json()["approved"]
        assert (await approve(api, prop, result["id"], headers)).status_code == 409
        assert (
            await api.post(f"/norm-proposals/{prop}/validate", headers=headers)
        ).status_code == 409


async def test_manager_only_and_invalid_evidence_retry(monkeypatch):
    async with client() as api:
        pid, headers, ref = await seed(api)
        _, operator = await create_process(api, "operator")
        assert (
            await api.post(f"/processes/{pid}/learning", json={}, headers=operator)
        ).status_code == 403
        assert (await anonymous("POST", f"/processes/{pid}/learning", json={})).status_code == 401
        seen = {}
        monkeypatch.setattr(
            llm,
            "model_for",
            per_role(
                {
                    "learner": [
                        {
                            "reasoning": "Pattern",
                            "proposals": [norm("guidance", GUIDANCE, "case:invented")],
                        },
                        {
                            "reasoning": "Insufficient evidence after considering counterexamples.",
                            "proposals": [],
                        },
                    ]
                },
                seen,
            ),
        )
        response = await api.post(f"/processes/{pid}/learning", json={}, headers=headers)
        assert response.status_code == 201 and not response.json()["proposals"]
        assert len(seen["learner"]) == 2
        assert (
            await api.get(f"/learning/{response.json()['id']}", headers=operator)
        ).status_code == 403


async def test_failed_analysis_does_not_leave_partial_proposals(monkeypatch):
    async with client() as api:
        pid, headers, _ = await seed(api)
        monkeypatch.setattr(llm, "model_for", lambda role: down("unavailable"))
        response = await api.post(f"/processes/{pid}/learning", json={}, headers=headers)
        assert response.status_code == 502
        async with session_factory() as session:
            assert not list(
                await session.scalars(select(Analysis).where(Analysis.process_id == pid))
            )
            assert len(list(await session.scalars(select(Rule).where(Rule.process_id == pid)))) == 2


async def test_concurrent_approval_publishes_once(monkeypatch):
    import asyncio

    async with client() as api:
        pid, headers, ref = await seed(api)
        prop = await propose(api, monkeypatch, pid, headers, ref)
        result = await prepare(api, monkeypatch, prop, headers)
        responses = await asyncio.gather(
            approve(api, prop, result["id"], headers),
            approve(api, prop, result["id"], headers),
        )
        assert sorted(r.status_code for r in responses) == [201, 409]
        assert len((await api.get(f"/processes/{pid}/rules")).json()) == 3


async def test_pending_review_disagreement_blocks_conflicting_rule(monkeypatch):
    async with client() as api:
        pid, headers = await create_process(
            api,
            "manager",
            {
                "iban_mismatch": ("ESCALAR", REAL_IBAN_RULE),
                "order_already_paid": ("NO_PAGAR", REAL_PAID_RULE),
            },
        )
        await configure(api, pid, {"guidance": "Explain uncertainty.", "timeout_seconds": 30})
        monkeypatch.setattr(
            llm, "model_for", per_role({"decision_reviewer": [answer("ESCALAR")] * 3})
        )
        assert (await api.post(f"/processes/{pid}/run")).status_code == 200
        cases = (await api.get(f"/processes/{pid}/instances")).json()
        ref = f"case:{next(c['id'] for c in cases if c['decision'] == 'PAGAR')}"
        prop = await propose(api, monkeypatch, pid, headers, ref)
        result = await prepare(api, monkeypatch, prop, headers)
        assert not result["report"]["valid"] and result["report"]["impact"]["conflicts"]
        assert (await approve(api, prop, result["id"], headers)).status_code == 409


async def test_guidance_cannot_be_approved_after_config_changes(monkeypatch):
    async with client() as api:
        pid, headers, ref = await seed(api)
        await configure(api, pid, {"guidance": "Explain uncertainty.", "timeout_seconds": 30})
        prop = await propose(api, monkeypatch, pid, headers, ref, "guidance")
        result = await prepare(
            api, monkeypatch, prop, headers, {"decision_reviewer": [answer("PAGAR")] * 6}
        )
        assert result["report"]["valid"]
        await configure(api, pid, None)
        assert (await approve(api, prop, result["id"], headers)).status_code == 409


async def test_normalized_policy_is_not_silently_lost(monkeypatch):
    async with client() as api:
        pid, headers, ref = await seed(api)
        prop = await propose(api, monkeypatch, pid, headers, ref)
        replies = scripts()
        replies["normalizer"][0]["norm_rules"][0]["policies"] = ["Consider consequences."]
        result = await prepare(api, monkeypatch, prop, headers, replies)
        assert not result["report"]["valid"] and "subjective" in result["report"]["error"]
        assert (await approve(api, prop, result["id"], headers)).status_code == 409
