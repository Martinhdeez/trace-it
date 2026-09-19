"""The three proposal channels behind one contract. Every channel keeps its own workflow:
accepting a proposal calls it (resolve an instance, review a chat draft, adopt a learned
norm, stage a version draft), so this module decides nothing by itself."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.proposals.model import ManagerProposal
from app.features.proposals.schemas import ManagerProposalOut

# Fields of a chat plan and the kind of change each one is. They share the draft's
# `setup` review, which is staged once every proposal on it is accepted.
SETUP = {
    "name": "context",
    "description": "context",
    "decision_types": "context",
    "decision_review": "context",
    "symbols": "input",
}
ITEMS = (
    ("rules", "rule", "rule"),
    ("guidance", "rule", "guidance"),
    ("sources", "source", "source"),
)


def out(row: ManagerProposal) -> ManagerProposalOut:
    return ManagerProposalOut.model_validate(row, from_attributes=True)


def settle(row: ManagerProposal, status: str, author: str, outcome: dict | None = None) -> None:
    row.status, row.resolved_by, row.resolved_at = status, author, datetime.now(UTC)
    row.outcome = outcome


async def supersede(session: AsyncSession, cause: str, *where) -> list[int]:
    """Close every open proposal matching `where` as `superseded` with `outcome.cause`, in
    the caller's transaction, and record one `expire_proposal` event for them. A proposal
    the manager rejected is `rejected`; one nobody settled ends here (ADR 0035). Causes:
    `ignored` (the manager resolved another case), `version_published`, `case_changed`
    (the case got a new decision), `superseded` (a newer proposal of the same kind)."""
    rows = list(
        await session.scalars(
            select(ManagerProposal).where(ManagerProposal.status == "open", *where)
        )
    )
    for row in rows:
        settle(row, "superseded", row.author, {"cause": cause})
    if rows:
        instances = {r.instance_id for r in rows}
        events.record(
            session,
            "expire_proposal",
            process_id=rows[0].process_id,
            instance_id=instances.pop() if len(instances) == 1 else None,
            data={"proposal_ids": [r.id for r in rows], "cause": cause},
        )
    return [r.id for r in rows]


async def list_for(session: AsyncSession, process_id: int, status: str | None):
    query = select(ManagerProposal).where(ManagerProposal.process_id == process_id)
    if status:
        query = query.where(ManagerProposal.status == status)
    return [out(r) for r in await session.scalars(query.order_by(ManagerProposal.id.desc()))]


async def get(session: AsyncSession, proposal_id: int, *, lock: bool = False) -> ManagerProposal:
    row = await session.get(
        ManagerProposal, proposal_id, with_for_update=lock, populate_existing=True
    )
    if row is None:
        raise NotFoundError(f"Proposal {proposal_id} does not exist")
    return row


async def _unchanged(session: AsyncSession, instance, asked):
    """R04: the model answered about decision `asked`; if the case got another decision
    while it ran (a resolution, a reprocess), the answer is stale and nothing is stored."""
    from app.features.decisions.service import latest_decisions

    latest = (await latest_decisions(session, [instance])).get(instance.id)
    if asked is None or latest is None or latest.id != asked.id:
        raise ConflictError(
            "El caso ha cambiado mientras el asistente respondía; pide una nueva sugerencia"
        )
    return latest


# Channel 1: the assistant on an escalated instance.
async def propose_decision(session: AsyncSession, instance_id: int) -> ManagerProposalOut:
    from app.features.agents import assistant
    from app.features.decisions.service import latest_decisions
    from app.features.ingestion.model import Instance

    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    with events.span(
        "propose_decision", process_id=instance.process_id, instance_id=instance_id
    ) as span:
        asked = (await latest_decisions(session, [instance])).get(instance.id)
        suggestion = await assistant.suggest(session, instance_id)
        latest = await _unchanged(session, instance, asked)
        await supersede(
            session,
            "superseded",
            ManagerProposal.instance_id == instance_id,
            ManagerProposal.kind == "decision",
        )
        row = ManagerProposal(
            process_id=instance.process_id,
            instance_id=instance_id,
            channel="escalation",
            kind="decision",
            summary=f"{suggestion.decision} for {instance.name}",
            rationale=suggestion.reasoning,
            evidence=suggestion.evidence,
            payload={
                "proposed": suggestion.decision,
                "why": suggestion.why,
                "options": [o.model_dump() for o in suggestion.options],
                "decision_id": latest.id,  # the escalation this answers
                "escalated_as": latest.decision,
                "escalation_reason": latest.reason,
                "fired_rules": [r["rule_id"] for r in latest.results if r.get("fires")],
                "proposed_rule": {
                    "text": suggestion.proposed_rule,
                    "type": suggestion.proposed_type,
                },
            },
            status="open",
            author="assistant",
        )
        session.add(row)
        await session.commit()
        span.set(proposal_id=row.id, proposed=suggestion.decision)
    return out(row)


# Channel 1b: after a resolution, amend the escalation rule that fired (ADR 0035). The
# engine's own escalation codes come from data or infrastructure, never from a rule that an
# exception could fix: {code: why not, in Spanish for the manager}.
NOT_LEARNABLE = {
    "MISSING_DATA": "Faltaba un dato obligatorio ({}): ninguna regla puede suplir un dato.",
    "UNVERIFIED_DATA": "Es un escaneo y no se pudo confirmar {}: ninguna regla puede "
    "confirmar un dato.",
    "SOURCE_UNAVAILABLE": "No se pudo consultar {}: es un fallo temporal, vuelve a ejecutar "
    "cuando responda.",
    "RULE_CONFLICT": "Dos reglas con la misma prioridad pedían decisiones distintas: se "
    "corrige en Definición → Normas, no con una excepción.",
    "SCAN_REVIEW": "Las reglas lo rechazaban, pero es un escaneo y podría ser un error de "
    "lectura: no hay regla de escalado que enmendar.",
}
RULE_FAILED = "Una regla no pudo evaluarse ({}): es un fallo técnico, no un criterio que aprender."


def learnable(
    reason: str,
    results: list[dict],
    rule_decisions: dict[int, str],
    outcomes,
    human: set[str],
    resolved_as: str,
) -> tuple[int | None, str]:
    """Pure gate before any model call: can amending one rule turn this engine escalation
    into the person's decision `resolved_as`? Returns (the rule to amend, "") or (None, why
    not, in Spanish). Only a rule-based escalation qualifies, with exactly one escalation
    rule fired, and the other fired rules (or the default when none) giving `resolved_as`:
    an exception to that rule is then exactly what would have decided the case."""
    head = (reason or "").split(" | ", 1)[0]
    code, _, detail = head.partition(": ")
    if code in NOT_LEARNABLE:
        return None, NOT_LEARNABLE[code].format(detail)
    failed = [r["reason"].split(" ", 1)[0] for r in results if r.get("fires") is None]
    if failed:
        return None, RULE_FAILED.format(", ".join(sorted(set(failed))))
    fired = [r["rule_id"] for r in results if r.get("fires")]
    escalating = [i for i in fired if rule_decisions.get(i) in human]
    if not escalating:
        return None, "Ninguna regla de escalado se disparó en este caso: no hay regla que enmendar."
    if len(escalating) > 1:
        ids = ", ".join(str(i) for i in escalating)
        return None, f"Se dispararon varias reglas de escalado ({ids}): una enmienda no basta."
    others = {rule_decisions[i] for i in fired if i not in escalating}
    top = max((outcomes.priorities[d] for d in others), default=None)
    without = sorted(d for d in others if outcomes.priorities[d] == top) or [outcomes.default]
    if without != [resolved_as]:
        return None, (
            f"Sin la regla {escalating[0]} el motor decidiría {' o '.join(without)}, no "
            f"{resolved_as}: hace falta una regla nueva (Definición → Normas)."
        )
    return escalating[0], ""


async def propose_rule(session: AsyncSession, instance_id: int) -> ManagerProposalOut:
    """The assistant amends the escalation rule that fired on a resolved case so that
    similar cases get the person's decision. Gated by `learnable` first: a case it cannot
    help is a 409 with the reason, and no model is called."""
    from app.features.agents import assistant
    from app.features.decisions.model import ENGINE, Decision
    from app.features.ingestion.model import Instance
    from app.features.versions import configuration as config
    from app.features.versions.model import ProcessVersion

    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    with events.span(
        "suggest_rule", process_id=instance.process_id, instance_id=instance_id
    ) as span:
        history = list(
            await session.scalars(
                select(Decision).where(Decision.instance_id == instance_id).order_by(Decision.id)
            )
        )
        resolution = history[-1] if history and history[-1].author != ENGINE else None
        engine = next((d for d in reversed(history) if d.author == ENGINE), None)
        if resolution is None:
            raise ConflictError("Resuelve el caso antes de pedir una regla.")
        if engine is None or engine.version_id is None:
            raise ConflictError("El motor no decidió este caso: no hay regla que enmendar.")
        snapshot = (await session.get(ProcessVersion, engine.version_id)).snapshot
        human = {t["name"] for t in snapshot["process"]["decision_types"] if t["requires_human"]}
        if engine.decision not in human:
            raise ConflictError("El motor no escaló este caso: no hay regla que enmendar.")
        if resolution.decision in human:
            raise ConflictError("Resuelve el caso con una decisión final antes de pedir una regla.")
        replaces, why = learnable(
            engine.reason,
            engine.results,
            {r.id: r.decision for r in config.rules(snapshot)},
            config.outcomes(snapshot),
            human,
            resolution.decision,
        )
        span.set(learnable=replaces is not None, replaces=replaces, why=why or None)
        if replaces is None:
            raise ConflictError(why)
        suggestion = await assistant.suggest_rule(session, instance, engine, resolution, replaces)
        await _unchanged(session, instance, resolution)
        await supersede(
            session,
            "superseded",
            ManagerProposal.instance_id == instance_id,
            ManagerProposal.kind == "rule",
        )
        decision = next(r.decision for r in config.rules(snapshot) if r.id == replaces)
        row = ManagerProposal(
            process_id=instance.process_id,
            instance_id=instance_id,
            channel="escalation",
            kind="rule",
            summary=suggestion.summary[:500],
            rationale=suggestion.rationale,
            evidence=suggestion.evidence,
            payload={
                "decision_id": resolution.id,  # the resolution it generalises
                "engine_decision_id": engine.id,
                "replaces": replaces,
                "text": suggestion.text,
                "summary": suggestion.summary,
                "type": suggestion.type,
                "decision": decision,
                "resolved_as": resolution.decision,
                "version_id": engine.version_id,
            },
            status="open",
            author="assistant",
        )
        session.add(row)
        await session.commit()
        span.set(proposal_id=row.id)
    return out(row)


async def _amend(session, row, user, background, text: str | None = None) -> dict:
    """Stage the amended rule in the draft in place of the one it replaces; it compiles in
    the background. Publishing stays validate + publish of the process draft. `text` is the
    manager's edit of `payload.text`; the payload stays as the agent wrote it."""
    from app.features.rules import service as rules
    from app.features.rules.schemas import RuleIn
    from app.features.versions.model import ProcessDraft

    p = row.payload
    with events.span("save_rule", process_id=row.process_id, author=user.name) as span:
        rule = await rules.create(
            session,
            row.process_id,
            RuleIn(
                text=text or p["text"], summary=p["summary"], type=p["type"], decision=p["decision"]
            ),
        )  # commits the settlement too
        span.set(rule_id=rule.id, proposal_id=row.id)
    await rules.retire(session, p["replaces"], user.name)
    if background is not None:
        background.add_task(rules.compile_all_in_background, [rule.id], events.current())
    draft = await session.get(ProcessDraft, row.process_id, populate_existing=True)
    return {"rule_id": rule.id, "retired": p["replaces"], "draft_revision": draft.revision}


def _content(item: dict | None) -> dict:
    """What a change changes: a restated evidence or explanation alone is no proposal."""
    return {k: v for k, v in (item or {}).items() if k not in {"evidence", "explanation"}}


# Channel 2: a process-chat revision. Called before the revision is saved, same commit.
async def from_chat(session: AsyncSession, draft, data: dict, revision: int) -> None:
    await supersede(
        session,
        "superseded",
        ManagerProposal.channel == "chat",
        ManagerProposal.payload["draft_id"].as_integer() == draft.id,
    )
    before, after = data["base_plan"], data["plan"]
    changes = []  # (kind, review key, summary, evidence, before, after)
    for kind in ("context", "input"):
        fields = [f for f, k in SETUP.items() if k == kind and after.get(f) != before.get(f)]
        if fields:
            old, new = ({f: plan.get(f) for f in fields} for plan in (before, after))
            changes.append((kind, "setup", f"Change {', '.join(fields)}", [], old, new))
    for field, kind, prefix in ITEMS:
        old = {i["name"]: i for i in before.get(field, [])}
        for item in after.get(field, []):
            previous = old.get(item["name"])
            if previous is None or _content(previous) != _content(item):
                summary = item.get("text") or item.get("explanation") or item["name"]
                key = f"{prefix}:{item['name']}"
                changes.append((kind, key, summary, item["evidence"], previous, item))
    for kind, key, summary, evidence, old, new in changes:
        session.add(
            ManagerProposal(
                process_id=draft.process_id,
                channel="chat",
                kind=kind,
                summary=summary[:500],
                rationale="; ".join(e["explanation"] for e in evidence) or after["summary"],
                evidence=[e["reference"] for e in evidence],
                payload={
                    "draft_id": draft.id,
                    "revision": revision,
                    "review_key": key,
                    "before": old,
                    "after": new,
                },
                status="open",
                author="discovery",
            )
        )


async def _chat(session, row, accepted, reason, user) -> dict:
    from app.features.processes import drafts
    from app.features.processes.draft_schemas import ReviewIn

    draft, _ = await drafts.read(session, row.payload["draft_id"])
    key = row.payload["review_key"]
    blocking = await session.scalar(
        select(ManagerProposal.id).where(
            ManagerProposal.id != row.id,
            ManagerProposal.channel == "chat",
            ManagerProposal.payload["draft_id"].as_integer() == draft.id,
            ManagerProposal.payload["review_key"].astext == key,
            ManagerProposal.status.in_(["open", "rejected"]),
        )
    )
    if accepted and blocking:  # a sibling on the same review must be accepted too
        return {"draft_id": draft.id, "review_key": key, "staged": False}
    reviewed = await drafts.review(
        session,
        draft.id,
        ReviewIn(
            revision=draft.revision,
            proposal=key,
            disposition="accepted" if accepted else "rejected",
            explanation=f"Proposal {row.id}. {reason}".strip(),
        ),
        user,
    )
    return {"draft_id": draft.id, "review_key": key, "staged": True, "revision": reviewed.revision}


# Channel 3: learning. Norms keep their validate/approve flow; definition changes stage.
def from_learning(analysis, norms, changes) -> list[ManagerProposal]:
    rows = [
        ManagerProposal(
            process_id=analysis.process_id,
            channel="learning",
            kind="rule",
            summary=n.text[:500],
            rationale=n.reasoning,
            evidence=n.evidence,
            payload={
                "analysis_id": analysis.id,
                "norm_proposal_id": n.id,
                "norm_kind": n.kind,
                "counterexamples": n.counterexamples,
                "limitations": n.limitations,
            },
            status="open",
            author="learner",
        )
        for n in norms
    ]
    rows += [
        ManagerProposal(
            process_id=analysis.process_id,
            channel="learning",
            kind=c.kind,
            summary=c.text[:500],
            rationale=c.reasoning,
            evidence=c.evidence,
            payload={"analysis_id": analysis.id, **c.model_dump(exclude={"reasoning", "evidence"})},
            status="open",
            author="learner",
        )
        for c in changes
    ]
    return rows


async def settle_norm(session, norm_id: int, status: str, author: str, outcome: dict) -> None:
    """A learned norm adopted or rejected, through this contract or /norm-proposals."""
    row = await session.scalar(
        select(ManagerProposal).where(
            ManagerProposal.status == "open",
            ManagerProposal.payload["norm_proposal_id"].as_integer() == norm_id,
        )
    )
    if row:
        settle(row, status, author, outcome)


async def _stage(session, row, user) -> dict:
    """Context and input changes go into the process's version draft; publishing it
    (`/processes/{id}/draft/validate`, `/publish`) stays a separate manager action."""
    from app.features.processes.schemas import SymbolIO
    from app.features.versions import service as versions
    from app.features.versions.model import ProcessDraft
    from app.features.versions.schemas import DraftIn

    current = await session.get(ProcessDraft, row.process_id, populate_existing=True)
    snapshot = (
        current.snapshot if current else (await versions.active(session, row.process_id)).snapshot
    )
    process = snapshot["process"]
    body = DraftIn(expected_revision=current.revision if current else None)
    if row.kind == "context":
        body.description = f"{process.get('description') or ''}\n{row.payload['text']}".strip()
    else:
        if any(s["name"] == row.payload["name"] for s in process["symbols"]):
            raise ConflictError(f"Symbol {row.payload['name']!r} already exists")
        body.symbols = [
            *[SymbolIO.model_validate(s) for s in process["symbols"]],
            SymbolIO(
                name=row.payload["name"],
                type=row.payload["type"],
                description=row.payload["text"],
            ),
        ]
    staged = await versions.edit(session, row.process_id, body, user.name)
    return {"process_draft_revision": staged.revision}


async def accept(
    session: AsyncSession, proposal_id: int, reason: str, user, background=None, text=None
) -> ManagerProposalOut:
    """`background` (FastAPI's BackgroundTasks): where an accepted rule is compiled. `text`:
    the manager's edit of an escalation rule suggestion, compiled instead of `payload.text`."""
    row = await get(session, proposal_id, lock=True)
    if row.status != "open":
        raise ConflictError(f"Proposal {proposal_id} is {row.status}")
    reason = reason or f"Accepted proposal {row.id}"
    with events.span(
        "accept_proposal",
        process_id=row.process_id,
        proposal_id=row.id,
        channel=row.channel,
        kind=row.kind,
        author=user.name,
    ) as span:
        if row.channel == "escalation" and row.kind == "rule":
            original = row.payload["text"]
            edit = (text or "").strip()
            changed = bool(edit) and edit != original
            edited = {"edited": True, "original_text": original} if changed else {}
            span.set(edited=changed, **({"original_text": original} if changed else {}))
            settle(row, "accepted", user.name, {"reason": reason, **edited})
            amended = await _amend(session, row, user, background, edit if edited else None)
            row.outcome = {**row.outcome, **amended}
        elif row.channel == "escalation":
            from app.features.decisions import service as decisions
            from app.features.decisions.schemas import ResolveIn

            await decisions.resolve(
                session,
                row.instance_id,
                ResolveIn(decision=row.payload["proposed"], reason=reason, proposal_id=row.id),
                user,
            )  # settles the proposal in the resolution's transaction
        elif row.channel == "chat":
            settle(row, "accepted", user.name)
            row.outcome = await _chat(session, row, True, reason, user)
        elif row.kind == "rule":
            await _adopt(session, row, reason, user)  # settled by learning.approve
        else:
            settle(row, "accepted", user.name)
            row.outcome = (
                {"note": "Load the source through /processes/{id}/sources or a workbook"}
                if row.kind == "source"
                else await _stage(session, row, user)
            )
        await session.commit()
    return out(await get(session, proposal_id))


async def _adopt(session, row, reason, user) -> None:
    from app.features.learning import service as learning
    from app.features.learning.model import Validation

    norm_id = row.payload["norm_proposal_id"]
    latest = await session.scalar(
        select(Validation)
        .where(Validation.proposal_id == norm_id)
        .order_by(Validation.id.desc())
        .limit(1)
    )
    if latest is None or not latest.report.get("valid"):
        raise ConflictError(
            f"Validate it first: POST /norm-proposals/{norm_id}/validate (it compiles and "
            "tests the norm against past cases)"
        )
    await learning.approve(session, norm_id, latest.id, reason, user.name)


async def reject(session: AsyncSession, proposal_id: int, reason: str, user) -> ManagerProposalOut:
    row = await get(session, proposal_id, lock=True)
    if row.status != "open":
        raise ConflictError(f"Proposal {proposal_id} is {row.status}")
    reason = reason or f"Rejected proposal {row.id}"
    with events.span(
        "reject_proposal",
        process_id=row.process_id,
        proposal_id=row.id,
        channel=row.channel,
        kind=row.kind,
        author=user.name,
    ):
        if row.channel == "learning" and row.kind == "rule":
            from app.features.learning import service as learning

            await learning.reject(session, row.payload["norm_proposal_id"], reason, user.name)
        else:
            settle(row, "rejected", user.name, {"reason": reason})
            if row.channel == "chat":
                row.outcome = {**row.outcome, **await _chat(session, row, False, reason, user)}
        await session.commit()
    return out(await get(session, proposal_id))
