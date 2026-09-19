"""A whole process as data: one JSON file under `processes/` (see `processes/README.md`).

Loading is idempotent, so the same file can be loaded again after editing it.

A rule is text; the compiler turns it into code. A rule may also point at a file holding
code already written, which is how a process runs before any model is configured, and what
a compiled rule can be compared against.
"""

from pathlib import Path
from typing import Self

from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.core import events
from app.features.agents import sandbox
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.processes.schemas import ProcessDetail, ProcessIn
from app.features.processes.service import get
from app.features.rules.model import Rule
from app.features.rules.schemas import RuleIn
from app.features.rules.service import rule_hash
from app.features.use_cases import service as use_cases
from app.features.use_cases.model import UseCase
from app.features.users.model import User
from app.features.users.schemas import UserIn


class RuleDefinition(RuleIn):
    # Path to a file with the rule's code, relative to the definition file. The file must
    # define `evaluate(instance, sources, others)` and pass the sandbox's static check.
    code: str | None = None


class Definition(ProcessIn):
    rules: list[RuleDefinition] = []
    users: list[UserIn] = []

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        types = {t.name for t in self.decision_types}
        if len(types) != len(self.decision_types):
            raise ValueError("Duplicate decision types")
        if len({t.priority for t in self.decision_types}) != len(self.decision_types):
            # Two types firing together at the same priority cannot be ranked.
            raise ValueError("Two decision types share a priority")
        if sum(t.is_default for t in self.decision_types) != 1:
            raise ValueError("There must be exactly one default decision type")
        if any(t.is_default and t.requires_human for t in self.decision_types):
            raise ValueError("The default decision type cannot require a human")
        if not any(t.requires_human for t in self.decision_types):
            # Where a case goes when a rule cannot be evaluated: always a person.
            raise ValueError("At least one decision type must require a human")
        if len({s.name for s in self.symbols}) != len(self.symbols):
            raise ValueError("Duplicate symbols")
        if len({r.text for r in self.rules}) != len(self.rules):
            raise ValueError("Several rules have the same text")
        for r in self.rules:
            if r.decision not in types:
                raise ValueError(f"{r.decision!r} is not a decision type: {r.text[:60]}")
        if self.use_case and self.description is not None:
            raise ValueError("The description belongs to the use case: give one or the other")
        return self


class LoadResult(BaseModel):
    process: ProcessDetail
    new_rules: int
    new_users: int


def _rule(data: RuleDefinition, process_id: int, base: Path | None) -> Rule:
    """A rule with code arrives ready to activate; one without it waits for the compiler."""
    rule = Rule(process_id=process_id, **data.model_dump(exclude={"code"}))
    if data.code:
        if base is None:
            # `code` names a file next to the definition, so it only means something when
            # the definition is being read from disk. Resolving a client-supplied path
            # server-side would hand out any file the backend can read.
            raise ConflictError(
                f"Rule {data.text[:40]!r} carries its code in a file ({data.code}): "
                f"load it with `python -m app.cli load`, not over HTTP"
            )
        code = (base / data.code).read_text(encoding="utf-8")
        sandbox.check(code)
        rule.code = code
        rule.hash = rule_hash(rule.text, code)
        # Nothing to cross-check: one text, one implementation, written by a person.
        rule.report = {"valid": True, "origin": "hand-written", "file": data.code}
    return rule


async def load_definition(
    session: AsyncSession, data: Definition, base: Path | None = None
) -> LoadResult:
    """`_load` in a span: what the definition added to which process."""
    with events.span("load_definition", name=data.name) as span:
        result = await _load(session, data, base)
        p = result.process
        span.set(
            process_id=p.id,
            use_case_id=p.use_case_id,
            decision_types=len(p.decision_types),
            symbols=len(p.symbols),
            new_rules=result.new_rules,
            new_users=result.new_users,
        )
        return result


async def _load(session: AsyncSession, data: Definition, base: Path | None) -> LoadResult:
    """Create the process if missing (by name), upsert its decision types and symbols, add each
    rule as a draft unless the process already has one with the same text, and create missing
    users by email. Existing rules are never touched. `base` is the folder a rule's `code`
    path is resolved from; without it, a rule that names a code file is refused."""
    if data.use_case:
        use_case = await session.scalar(select(UseCase).where(UseCase.name == data.use_case))
        if use_case is None:
            raise ConflictError(f"Use case {data.use_case!r} does not exist: load it first")
    else:
        use_case = await use_cases.ensure(session, data.name, data.description or "")
    process = await session.scalar(select(Process).where(Process.name == data.name))
    if process is None:
        process = Process(name=data.name, use_case_id=use_case.id)
        session.add(process)
    process.use_case_id = use_case.id
    await session.flush()

    for t in data.decision_types:
        await session.merge(DecisionType(process_id=process.id, **t.model_dump()))
    for s in data.symbols:
        await session.merge(Symbol(process_id=process.id, **s.model_dump()))

    texts = set(await session.scalars(select(Rule.text).where(Rule.process_id == process.id)))
    rules = [r for r in data.rules if r.text not in texts]
    session.add_all(_rule(r, process.id, base) for r in rules)

    emails = set(await session.scalars(select(User.email)))
    users = [u for u in data.users if u.email not in emails]
    session.add_all(User(**u.model_dump()) for u in users)

    await session.commit()
    return LoadResult(
        process=await get(session, process.id),
        new_rules=len(rules),
        new_users=len(users),
    )


async def load_pack(session: AsyncSession, file: Path) -> LoadResult:
    """What `python -m app.cli load` does: the pack's use case (`<pack>/use-case.json`), if
    it has one, then the process with its rules' code files."""
    use_case_file = file.with_suffix("") / use_cases.FILE
    if use_case_file.exists():
        await use_cases.load(session, use_cases.read_file(use_case_file))
    data = Definition.model_validate_json(file.read_text(encoding="utf-8"))
    return await load_definition(session, data, file.parent)
