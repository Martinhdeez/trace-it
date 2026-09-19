"""The single publication path for configuration, rules and learned norms."""

from copy import deepcopy

from sqlalchemy import select

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.agents import compiler, sandbox
from app.features.decisions.model import Finding
from app.features.processes.model import Process
from app.features.processes.schemas import ProcessDetail
from app.features.rules.model import Rule
from app.features.versions import configuration as config
from app.features.versions import execution
from app.features.versions.model import ProcessDraft, ProcessVersion
from app.features.versions.schemas import DraftIn


async def lock(session, process_id: int) -> Process:
    row = await session.scalar(
        select(Process)
        .where(Process.id == process_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    return row


async def active(session, process_id: int, *, required: bool = True) -> ProcessVersion | None:
    process = await session.get(Process, process_id)
    if process is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    version = (
        await session.get(ProcessVersion, process.active_version_id)
        if process.active_version_id
        else None
    )
    if required and version is None:
        raise ConflictError("Publish an approved process version before running cases")
    return version


async def get_draft(session, process_id: int) -> ProcessDraft:
    draft = await session.get(ProcessDraft, process_id, populate_existing=True)
    if draft is None:
        raise NotFoundError("This process has no draft")
    return draft


async def stage(session, process_id: int, snapshot: dict, author: str) -> ProcessDraft:
    process = await lock(session, process_id)
    draft = await session.get(ProcessDraft, process_id, populate_existing=True)
    if draft is None:
        draft = ProcessDraft(
            process_id=process_id, revision=0, base_version_id=process.active_version_id
        )
        session.add(draft)
    draft.revision += 1
    draft.snapshot = deepcopy(snapshot)
    draft.snapshot["process"].pop("active_version_id", None)
    draft.author = author
    draft.validation = None
    await session.flush()
    return draft


async def edit(session, process_id: int, body: DraftIn, author: str) -> ProcessDraft:
    process = await lock(session, process_id)
    draft = await session.get(ProcessDraft, process_id, populate_existing=True)
    if not draft and body.expected_revision is not None:
        raise ConflictError("The previous draft was published or discarded; start a new draft")
    if draft and body.expected_revision != draft.revision:
        raise ConflictError("Supply the current expected_revision to edit this draft")
    if draft and draft.base_version_id != process.active_version_id:
        if body.restore_version_id != process.active_version_id:
            raise ConflictError(
                "The active version changed; restore its version into the draft and reapply edits"
            )
        draft.base_version_id = process.active_version_id
    version = await active(session, process_id, required=False)
    snapshot = deepcopy(
        draft.snapshot
        if draft
        else version.snapshot
        if version
        else await config.workspace(session, process_id)
    )
    if body.restore_version_id is not None:
        old = await session.get(ProcessVersion, body.restore_version_id)
        if old is None or old.process_id != process_id:
            raise NotFoundError("Version does not belong to this process")
        snapshot = deepcopy(old.snapshot)
    for name in ("description", "decision_types", "symbols", "decision_review"):
        if name in body.model_fields_set:
            if getattr(body, name) is None and name != "decision_review":
                raise ConflictError(f"{name} cannot be null")
            snapshot["process"][name] = body.model_dump(mode="json")[name]
    if body.rule_ids is not None:
        rows = list(
            await session.scalars(
                select(Rule)
                .where(Rule.process_id == process_id, Rule.id.in_(body.rule_ids))
                .order_by(Rule.id)
            )
        )
        if len(rows) != len(set(body.rule_ids)):
            raise ConflictError("Every selected rule must belong to this process")
        snapshot["rules"] = [config.artifact(r) for r in rows]
    if body.guidance is not None:
        if any(not key.strip() or not value.strip() for key, value in body.guidance.items()):
            raise ConflictError("Guidance references and text must be nonempty")
        snapshot["guidance"] = body.guidance
    if body.refresh_agents:
        snapshot["agents"] = await config.agents(session, snapshot["process"]["use_case_id"])
    result = await stage(session, process_id, snapshot, author)
    await session.commit()
    return result


def check_configuration(snapshot: dict) -> None:
    detail = ProcessDetail.model_validate(snapshot["process"])
    types = detail.decision_types
    names = {t.name for t in types}
    if len(names) != len(types) or len({t.priority for t in types}) != len(types):
        raise ValueError("Decision names and priorities must be unique")
    if (
        sum(t.is_default for t in types) != 1
        or any(t.is_default and t.requires_human for t in types)
        or not any(t.requires_human for t in types)
    ):
        raise ValueError("Exactly one automatic default and a human escalation type are required")
    symbols = {s.name for s in detail.symbols}
    if len(symbols) != len(detail.symbols):
        raise ValueError("Symbol names must be unique")
    if len({r["id"] for r in snapshot["rules"]}) != len(snapshot["rules"]):
        raise ValueError("Rule IDs must be unique")
    for rule in snapshot["rules"]:
        if rule["decision"] not in names:
            raise ValueError(f"Rule {rule['id']} refers to an unknown decision type")
        if not rule["code"] or not (rule["report"] or {}).get("valid"):
            raise ValueError(f"Rule {rule['id']} has no validated code")
        sandbox.check(rule["code"])
        unknown, _ = compiler.read_keys(rule["code"])
        if unknown - symbols:
            raise ValueError(f"Rule {rule['id']} reads removed or unknown symbols")
        if rule["tests"] and not all(
            t["passed"] for t in compiler.run_tests(rule["code"], rule["tests"])
        ):
            raise ValueError(f"Rule {rule['id']} fails its stored tests")
    config.setups(snapshot)


async def inspect(session, snapshot: dict, inputs: dict) -> dict:
    # Validate artifacts even if the process has no past cases.
    import asyncio

    try:
        await asyncio.to_thread(check_configuration, snapshot)
    except (ValueError, sandbox.SandboxError) as error:
        return {"valid": False, "error": str(error)}
    selected = [i for i in inputs["instances"] if i["decision"] and i["symbols"] is not None]
    verdicts = await execution.evaluate(session, snapshot, inputs, [i["id"] for i in selected])
    changes, conflicts, errors = [], [], []
    unchanged = 0
    for instance in selected:
        previous = instance["decision"]
        verdict = verdicts[instance["id"]]
        if any(r.fires is None for r in verdict.results):
            errors.append({"instance_id": instance["id"], "reason": verdict.reason})
        if previous["decision"] == verdict.decision:
            unchanged += 1
            continue
        change = {
            "instance_id": instance["id"],
            "decision_id": previous["id"],
            "name": instance["name"],
            "before": previous["decision"],
            "after": verdict.decision,
            "reason": verdict.reason,
        }
        (
            conflicts if previous["author"] != "engine" or previous["pending_review"] else changes
        ).append(change)
    return {
        "valid": not conflicts and not errors,
        "unchanged": unchanged,
        "changes": changes,
        "conflicts": conflicts,
        "errors": errors,
    }


async def validate(session, process_id: int) -> ProcessDraft:
    process = await lock(session, process_id)
    draft = await get_draft(session, process_id)
    if draft.base_version_id != process.active_version_id:
        raise ConflictError("The active version changed; rebase the draft before validation")
    inputs = await execution.capture(session, process_id)
    report = await inspect(session, draft.snapshot, inputs)
    draft.validation = {
        **report,
        "inputs_hash": config.digest(inputs),
        "snapshot_hash": config.digest(draft.snapshot),
        "revision": draft.revision,
    }
    draft.validation = {**draft.validation, "hash": config.digest(draft.validation)}
    await session.commit()
    return draft


async def publish_snapshot(
    session, process: Process, snapshot: dict, author: str, reason: str, report: dict
) -> ProcessVersion:
    """Caller holds the process lock and has validated this exact candidate and evidence."""
    previous = await active(session, process.id, required=False)
    row = ProcessVersion(
        process_id=process.id,
        number=previous.number + 1 if previous else 1,
        parent_id=previous.id if previous else None,
        snapshot=deepcopy(snapshot),
        content_hash=config.digest(snapshot),
        validation=deepcopy(report),
        author=author,
        reason=reason,
    )
    session.add(row)
    await session.flush()
    process.active_version_id = row.id
    process.use_case_id = snapshot["process"]["use_case_id"]
    selected = {r["id"]: r for r in snapshot["rules"]}
    for rule in await session.scalars(select(Rule).where(Rule.process_id == process.id)):
        if rule.id in selected:
            for key in config.RULE_FIELDS:
                if key not in ("id", "status"):
                    setattr(rule, key, deepcopy(selected[rule.id][key]))
            rule.status = selected[rule.id]["status"]
            rule.activated_at = row.created_at
        elif rule.status in ("active", "blocked"):
            rule.status = "retired"
    from app.features.decisions.model import Decision

    for change in report.get("changes", []):
        decision = await session.get(Decision, change["decision_id"])
        historical = (
            await session.get(ProcessVersion, decision.version_id)
            if decision.version_id
            else previous
        )
        human = (
            {
                t["name"]
                for t in historical.snapshot["process"]["decision_types"]
                if t["requires_human"]
            }
            if historical
            else set()
        )
        if change["before"] in human:
            continue
        session.add(
            Finding(
                decision_id=change["decision_id"],
                rule_id=None,
                type="different_decision",
                detail=(
                    f"Process version {row.number}: "
                    f"{change['before']} -> {change['after']}: {change['reason']}"
                ),
            )
        )
    events.record(
        session,
        "publish_process_version",
        process_id=process.id,
        data={"version_id": row.id, "parent_id": row.parent_id, "author": author, "reason": reason},
    )
    return row


async def publish(
    session, process_id: int, revision: int, validation_hash: str, author: str, reason: str
) -> ProcessVersion:
    process = await lock(session, process_id)
    draft = await get_draft(session, process_id)
    validation = draft.validation or {}
    if (
        draft.revision != revision
        or validation.get("hash") != validation_hash
        or not validation.get("valid")
    ):
        raise ConflictError("Approve the latest successful validation of this exact draft revision")
    if (
        process.active_version_id != draft.base_version_id
        or validation["snapshot_hash"] != config.digest(draft.snapshot)
        or validation["inputs_hash"] != config.digest(await execution.capture(session, process_id))
    ):
        raise ConflictError("Configuration or execution evidence changed; validate again")
    row = await publish_snapshot(session, process, draft.snapshot, author, reason, validation)
    await session.delete(draft)
    await session.commit()
    return row
