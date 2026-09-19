"""Loading a use case file, against the local database (`make test-db`)."""

import uuid

from app.core.database import session_factory
from app.features.use_cases import service
from app.features.use_cases.schemas import AgentSettings, UseCaseDefinition
from tests.support import pack


def _definition(instructions: str = "Amounts in cents.") -> UseCaseDefinition:
    return UseCaseDefinition(
        name=f"use case {uuid.uuid4().hex[:8]}",
        description="Conventions",
        agents={"compiler": AgentSettings(instructions=instructions)},
    )


async def _versions(data: UseCaseDefinition) -> list[tuple[int, str, bool]]:
    async with session_factory() as session:
        use_case = await service.load(session, data)
        await session.commit()
        rows = await service.versions(session, use_case.id, "compiler")
    return [(r.version, r.config.instructions, r.active) for r in rows]


async def test_loading_twice_is_idempotent() -> None:
    data = _definition()
    first = await _versions(data)
    assert first == [(1, "Amounts in cents.", True)]
    assert await _versions(data) == first


async def test_a_changed_file_config_enters_inactive() -> None:
    data = _definition()
    await _versions(data)
    changed = data.model_copy(update={"agents": {"compiler": AgentSettings(instructions="New")}})

    assert await _versions(changed) == [(1, "Amounts in cents.", True), (2, "New", False)]


def test_example_code_paths_are_read_into_code() -> None:
    examples = pack.use_case().agents["compiler"].examples
    assert examples and all("def evaluate(" in e.code for e in examples)
