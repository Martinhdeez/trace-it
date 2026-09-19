"""Use cases and the versioned configuration of their agents (ADR 0011).

Loading a use case never overrides what was decided at runtime: a role without any version
gets the file's config as version 1, active; a file config that differs from every stored
version enters as a new, inactive version for a person to activate.
"""

from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.agents import llm
from app.features.use_cases.model import AgentConfig, UseCase
from app.features.use_cases.schemas import (
    ROLES,
    AgentConfigOut,
    AgentSettings,
    UseCaseDefinition,
    UseCaseDetail,
    UseCaseOut,
)

PACK_AUTHOR = "pack"
FILE = "use-case.json"


def read_file(path: Path) -> UseCaseDefinition:
    """A use case file with each example's `code` path (relative to the file) replaced by
    the code it names."""
    data = UseCaseDefinition.model_validate_json(path.read_text(encoding="utf-8"))
    for settings in data.agents.values():
        for example in settings.examples:
            example.code = (path.parent / example.code).read_text(encoding="utf-8")
    return data


async def _use_case(session: AsyncSession, use_case_id: int) -> UseCase:
    use_case = await session.get(UseCase, use_case_id)
    if use_case is None:
        raise NotFoundError(f"Use case {use_case_id} does not exist")
    return use_case


async def ensure(session: AsyncSession, name: str, description: str | None) -> UseCase:
    """The use case called `name`, created if missing. `description`, when given, replaces
    the stored one."""
    use_case = await session.scalar(select(UseCase).where(UseCase.name == name))
    if use_case is None:
        use_case = UseCase(name=name)
        session.add(use_case)
    if description is not None:
        use_case.description = description
    await session.flush()
    return use_case


async def load(session: AsyncSession, data: UseCaseDefinition) -> UseCase:
    """Create or update a use case from its definition (idempotent)."""
    with events.span("load_use_case", name=data.name, author=PACK_AUTHOR) as span:
        use_case = await ensure(session, data.name, data.description)
        added = await _load_agents(session, use_case, data)
        span.set(use_case_id=use_case.id, added=added)
    return use_case


async def _load_agents(session: AsyncSession, use_case: UseCase, data: UseCaseDefinition) -> list:
    """Each role's file config not stored yet, as a new version: `[{role, version, active}]`."""
    added = []
    for role, settings in data.agents.items():
        versions = list(
            await session.scalars(
                select(AgentConfig).where(
                    AgentConfig.use_case_id == use_case.id, AgentConfig.role == role
                )
            )
        )
        if any(AgentSettings.model_validate(v.config) == settings for v in versions):
            continue
        note = "loaded from the pack"
        row = await _add(
            session, use_case.id, role, settings, PACK_AUTHOR, note, activate=not versions
        )
        added.append({"role": role, "version": row.version, "active": row.active})
    return added


async def _add(
    session: AsyncSession,
    use_case_id: int,
    role: str,
    settings: AgentSettings,
    author: str,
    note: str | None,
    activate: bool,
) -> AgentConfig:
    last = await session.scalar(
        select(func.max(AgentConfig.version)).where(
            AgentConfig.use_case_id == use_case_id, AgentConfig.role == role
        )
    )
    if activate:
        await _deactivate(session, use_case_id, role)
    row = AgentConfig(
        use_case_id=use_case_id,
        role=role,
        version=(last or 0) + 1,
        config=settings.model_dump(mode="json"),
        active=activate,
        author=author,
        note=note,
    )
    session.add(row)
    await session.flush()
    return row


async def _deactivate(session: AsyncSession, use_case_id: int, role: str) -> None:
    await session.execute(
        update(AgentConfig)
        .where(AgentConfig.use_case_id == use_case_id, AgentConfig.role == role)
        .values(active=False)
    )
    await session.flush()


async def setups(session: AsyncSession, use_case_id: int) -> dict[str, llm.Setup]:
    """How each configured role runs in the use case, for `llm.run`."""
    return {
        role: llm.Setup(AgentSettings.model_validate(row.config), row.id)
        for role, row in (await active(session, use_case_id)).items()
    }


async def active(session: AsyncSession, use_case_id: int) -> dict[str, AgentConfig]:
    """The active configuration of each configured role."""
    rows = await session.scalars(
        select(AgentConfig).where(AgentConfig.use_case_id == use_case_id, AgentConfig.active)
    )
    return {r.role: r for r in rows}


def _out(row: AgentConfig) -> AgentConfigOut:
    return AgentConfigOut.model_validate(row, from_attributes=True)


async def list_all(session: AsyncSession) -> list[UseCaseOut]:
    rows = await session.scalars(select(UseCase).order_by(UseCase.id))
    return [UseCaseOut.model_validate(u, from_attributes=True) for u in rows]


async def get(session: AsyncSession, use_case_id: int) -> UseCaseDetail:
    use_case = await _use_case(session, use_case_id)
    configs = await active(session, use_case_id)
    return UseCaseDetail(
        id=use_case.id,
        name=use_case.name,
        description=use_case.description,
        agents=[_out(configs[r]) for r in ROLES if r in configs],
    )


async def versions(session: AsyncSession, use_case_id: int, role: str) -> list[AgentConfigOut]:
    await _use_case(session, use_case_id)
    rows = await session.scalars(
        select(AgentConfig)
        .where(AgentConfig.use_case_id == use_case_id, AgentConfig.role == role)
        .order_by(AgentConfig.version)
    )
    return [_out(r) for r in rows]


async def configure(
    session: AsyncSession,
    use_case_id: int,
    role: str,
    settings: AgentSettings,
    author: str,
    note: str | None,
) -> AgentConfigOut:
    """A new version of `role`'s configuration, active from now on. The span says who
    changed what: the version it replaces and the new one (in the process feeds)."""
    await _use_case(session, use_case_id)
    links = {"use_case_id": use_case_id, "role": role, "author": author, "note": note}
    with events.span("configure_agent", **links) as span:
        before = (await active(session, use_case_id)).get(role)
        row = await _add(session, use_case_id, role, settings, author, note, activate=True)
        await session.commit()
        span.set(
            before_version=before.version if before else None,
            after_version=row.version,
            config_id=row.id,
            config=row.config,
        )
    return _out(row)


async def activate(session: AsyncSession, config_id: int, author: str) -> AgentConfigOut:
    """Make an existing version the active one (rollback or adopting a loaded version)."""
    row = await session.get(AgentConfig, config_id)
    if row is None:
        raise NotFoundError(f"Agent config {config_id} does not exist")
    links = {"use_case_id": row.use_case_id, "role": row.role, "author": author}
    with events.span("activate_agent_config", config_id=config_id, **links) as span:
        before = (await active(session, row.use_case_id)).get(row.role)
        span.set(before_version=before.version if before else None, after_version=row.version)
        if row.active:
            raise ConflictError(f"Version {row.version} of {row.role} is already active")
        await _deactivate(session, row.use_case_id, row.role)
        row.active = True
        await session.commit()
    return _out(row)
