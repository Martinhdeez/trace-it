"""On-demand learning, isolated preparation, and explicit manager adoption."""

import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.agents import compiler, learner, llm
from app.features.decisions.model import Finding
from app.features.ingestion.model import Instance
from app.features.learning import evidence, validation
from app.features.learning.model import Adoption, Analysis, Proposal, Validation
from app.features.learning.schemas import AdoptionOut, AnalysisOut, ProposalOut, ValidationOut
from app.features.processes.model import Process
from app.features.rules.model import NormRule, Rule


def out(schema, row):
    return schema.model_validate(row, from_attributes=True)


async def proposal(session: AsyncSession, proposal_id: int, *, lock: bool = False) -> Proposal:
    query = select(Proposal).where(Proposal.id == proposal_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = await session.scalar(query)
    if row is None:
        raise NotFoundError(f"Proposal {proposal_id} does not exist")
    return row


async def unresolved(session: AsyncSession, proposal_id: int) -> Proposal:
    row = await proposal(session, proposal_id, lock=True)
    if await session.scalar(select(Adoption.id).where(Adoption.proposal_id == proposal_id)):
        raise ConflictError("This proposal already has a manager resolution")
    return row


async def get_proposal(session: AsyncSession, proposal_id: int) -> ProposalOut:
    row = await proposal(session, proposal_id)
    result = out(ProposalOut, row)
    result.validations = [
        out(ValidationOut, v)
        for v in await session.scalars(
            select(Validation).where(Validation.proposal_id == row.id).order_by(Validation.id)
        )
    ]
    adopted = await session.scalar(select(Adoption).where(Adoption.proposal_id == row.id))
    result.adoption = out(AdoptionOut, adopted) if adopted else None
    return result


async def get(session: AsyncSession, analysis_id: int) -> AnalysisOut:
    row = await session.get(Analysis, analysis_id)
    if row is None:
        raise NotFoundError(f"Analysis {analysis_id} does not exist")
    result = out(AnalysisOut, row)
    ids = await session.scalars(
        select(Proposal.id).where(Proposal.analysis_id == row.id).order_by(Proposal.id)
    )
    result.proposals = [await get_proposal(session, key) for key in ids]
    return result


async def list_all(session: AsyncSession, process_id: int, limit: int) -> list[AnalysisOut]:
    if await session.get(Process, process_id) is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    ids = await session.scalars(
        select(Analysis.id)
        .where(Analysis.process_id == process_id)
        .order_by(Analysis.id.desc())
        .limit(limit)
    )
    return [await get(session, key) for key in ids]


async def analyze(
    session: AsyncSession, process_id: int, case_limit: int, author: str
) -> AnalysisOut:
    with events.span("learn_norms", process_id=process_id, author=author) as span:
        snapshot = await evidence.capture(session, process_id)
        context = await evidence.context(session, snapshot, case_limit)
        prior = list(
            await session.scalars(
                select(Proposal.text)
                .join(Analysis)
                .where(Analysis.process_id == process_id)
                .order_by(Proposal.id)
            )
        )
        context["previous_proposals"] = prior[-100:]
        context["previous_proposal_count"] = len(prior)
        existing = {
            t.casefold().strip()
            for t in [
                *prior,
                *snapshot["guidance"].values(),
                *(r["text"] for r in snapshot["rules"]),
            ]
        }
        setup = validation.setups(snapshot).get("learner")
        try:
            async with asyncio.timeout(120):
                result, trace = await llm.run(
                    learner.learner,
                    "learner",
                    json.dumps(context, default=str),
                    instructions=llm.prompt("learner"),
                    setup=setup,
                    deps=learner.Deps(set(context["evidence"]), existing),
                )
        except (TimeoutError, ValueError) as error:
            raise llm.AgentError(f"Learning analysis failed: {error}") from error
        row = Analysis(
            process_id=process_id,
            author=author,
            reasoning=result.reasoning,
            snapshot={
                "context": context,
                "agent": snapshot["agents"].get("learner"),
                "instructions": snapshot["prompts"]["learner"],
                "model": trace.model,
            },
        )
        session.add(row)
        await session.flush()
        session.add_all([Proposal(analysis_id=row.id, **p.model_dump()) for p in result.proposals])
        await session.commit()
        span.set(analysis_id=row.id, proposals=len(result.proposals))
    return await get(session, row.id)


async def validate(session: AsyncSession, proposal_id: int, author: str) -> ValidationOut:
    row = await unresolved(session, proposal_id)
    analysis = await session.get(Analysis, row.analysis_id)
    with events.span(
        "validate_norm", process_id=analysis.process_id, proposal_id=row.id, author=author
    ) as span:
        snapshot = await evidence.capture(session, analysis.process_id)
        try:
            # One bounded operation, with no background job or effect on live rules.
            async with asyncio.timeout(300):
                report = await (
                    validation.deterministic(row.text, snapshot)
                    if row.kind == "deterministic"
                    else validation.subjective(row.text, snapshot)
                )
        except (llm.AgentError, compiler.CompilationError, TimeoutError, ValueError) as error:
            report = {"valid": False, "error": f"{type(error).__name__}: {error}"}
        record = Validation(
            proposal_id=row.id,
            author=author,
            baseline=evidence.digest(snapshot),
            snapshot=snapshot,
            report=report,
        )
        session.add(record)
        await session.commit()
        span.set(validation_id=record.id, valid=report["valid"])
    return out(ValidationOut, record)


async def approve(
    session: AsyncSession, proposal_id: int, validation_id: int, reason: str, author: str
) -> AdoptionOut:
    row = await unresolved(session, proposal_id)
    analysis = await session.get(Analysis, row.analysis_id)
    from copy import deepcopy

    from app.features.versions import configuration as version_config
    from app.features.versions import service as versions

    process = await versions.lock(session, analysis.process_id)
    # Runs and human resolutions lock instances too. Hold these through publication
    # so the conflict check cannot race a person's decision. No model runs under these locks.
    await session.scalars(
        select(Instance)
        .where(Instance.process_id == analysis.process_id)
        .order_by(Instance.id)
        .with_for_update()
    )
    # Serialize adoptions; the next proposal must preview this adoption too.
    await session.get(Process, analysis.process_id, with_for_update=True)
    await session.scalars(
        select(Rule)
        .where(Rule.process_id == analysis.process_id)
        .order_by(Rule.id)
        .with_for_update()
    )
    prepared = await session.scalar(
        select(Validation)
        .where(Validation.proposal_id == row.id)
        .order_by(Validation.id.desc())
        .limit(1)
    )
    if prepared is None or prepared.id != validation_id or not prepared.report.get("valid"):
        raise ConflictError("Approve the latest successful validation of this proposal")
    snapshot = await evidence.capture(session, analysis.process_id)
    if evidence.digest(snapshot) != prepared.baseline:
        raise ConflictError("The process or its evidence changed; validate the proposal again")
    with events.span(
        "adopt_norm",
        process_id=analysis.process_id,
        proposal_id=row.id,
        validation_id=prepared.id,
        author=author,
    ) as span:
        rule_ids = []
        if row.kind == "deterministic":
            norm = NormRule(process_id=analysis.process_id, number=1, text=row.text, policies=[])
            session.add(norm)
            await session.flush()
            for artifact in prepared.report["rules"]:
                compiled = Rule(
                    process_id=analysis.process_id,
                    norm_rule_id=norm.id,
                    **{
                        k: artifact[k]
                        for k in ("text", "type", "decision", "code", "tests", "hash")
                    },
                    status="active",
                    activated_at=datetime.now(UTC),
                    report={
                        **artifact["report"],
                        "norm": artifact["interpretation"],
                        "learning": {
                            "proposal_id": row.id,
                            "validation_id": prepared.id,
                            "author": author,
                        },
                    },
                )
                session.add(compiled)
                await session.flush()
                rule_ids.append(compiled.id)
            human = {
                t["name"] for t in snapshot["process"]["decision_types"] if t["requires_human"]
            }
            for change in prepared.report["impact"]["changes"]:
                if change["before"] not in human:
                    session.add(
                        Finding(
                            decision_id=change["decision_id"],
                            rule_id=rule_ids[0] if len(rule_ids) == 1 else None,
                            type="different_decision",
                            detail=(
                                f"Norm proposal {row.id}: {change['before']} -> "
                                f"{change['after']}: {change['reason']}"
                            ),
                        )
                    )
        adopted = Adoption(
            proposal_id=row.id,
            validation_id=prepared.id,
            approved=True,
            author=author,
            reason=reason,
            snapshot={
                "baseline": prepared.baseline,
                "rule_ids": rule_ids,
                "norm": {"kind": row.kind, "text": row.text},
            },
        )
        session.add(adopted)
        await session.flush()
        # Extend only the published configuration, never an unrelated draft.
        previous = await versions.active(session, analysis.process_id)
        candidate = deepcopy(previous.snapshot)
        for key in rule_ids:
            candidate["rules"].append(version_config.artifact(await session.get(Rule, key)))
        if row.kind == "guidance":
            candidate["guidance"][f"norm:{adopted.id}"] = row.text
        published = await versions.publish_snapshot(
            session,
            process,
            candidate,
            author,
            reason,
            {
                "valid": True,
                "learning_validation_id": prepared.id,
                "inputs_hash": prepared.baseline,
            },
        )
        adopted.snapshot = {**adopted.snapshot, **candidate, "version_id": published.id}
        await session.commit()
        span.set(adoption_id=adopted.id, rule_ids=rule_ids)
    return out(AdoptionOut, adopted)


async def reject(session: AsyncSession, proposal_id: int, reason: str, author: str) -> AdoptionOut:
    row = await unresolved(session, proposal_id)
    analysis = await session.get(Analysis, row.analysis_id)
    with events.span(
        "reject_norm", process_id=analysis.process_id, proposal_id=row.id, author=author
    ):
        record = Adoption(
            proposal_id=row.id,
            validation_id=None,
            approved=False,
            author=author,
            reason=reason,
            snapshot={},
        )
        session.add(record)
        await session.commit()
    return out(AdoptionOut, record)
