import os
import uuid

import pytest

from app.core.database import session_factory
from app.features.decisions.model import ENGINE, Decision
from app.features.ingestion.model import File, Instance
from app.features.processes.model import Process
from app.features.versions.model import Execution, ProcessVersion
from tests.support.users import manager_client

pytestmark = pytest.mark.skipif(
    os.getenv("TRACEPAY_TEST_POSTGRES") != "1", reason="Requires test PostgreSQL"
)


@pytest.mark.asyncio
async def test_preview_schedules_oldest_without_splitting_and_explains_missing_due_date() -> None:
    async with manager_client() as api:
        suffix = uuid.uuid4().hex[:8]
        definition = {
            "name": f"treasury-{suffix}",
            "decision_types": [
                {"name": "ESCALAR", "priority": 2, "requires_human": True},
                {"name": "PAGAR", "priority": 1, "is_default": True},
            ],
            "symbols": [
                {"name": "total", "type": "number"},
                {"name": "issuer_name", "type": "text"},
                {"name": "due_date", "type": "date"},
                {"name": "currency", "type": "text"},
            ],
        }
        response = await api.post("/processes/definition", json=definition)
        assert response.status_code == 200, response.text
        process_id = response.json()["process"]["id"]
        process_detail = (await api.get(f"/processes/{process_id}")).json()
        rows = [
            (
                "old.pdf",
                {
                    "total": "60.00",
                    "issuer_name": "Old",
                    "due_date": "2026-01-01",
                    "currency": "EUR",
                },
            ),
            (
                "new.pdf",
                {
                    "total": "60.00",
                    "issuer_name": "New",
                    "due_date": "2026-01-02",
                    "currency": "EUR",
                },
            ),
            ("missing.pdf", {"total": "20.00", "issuer_name": "Missing", "currency": "EUR"}),
            (
                "legacy.pdf",
                {
                    "total": "15.00",
                    "issuer_name": "Legacy",
                    "due_date": "2026-01-03",
                    "currency": "EUR",
                },
            ),
        ]
        async with session_factory() as session:
            process = await session.get(Process, process_id)
            version = ProcessVersion(
                process_id=process_id,
                number=1,
                parent_id=None,
                snapshot={"process": process_detail},
                validation={"valid": True},
                content_hash=f"treasury-test-{suffix}",
                author="test",
                reason="treasury API fixture",
            )
            session.add(version)
            await session.flush()
            process.active_version_id = version.id

            async def add_record(
                name: str,
                values: dict[str, str],
                *,
                author: str,
                with_execution: bool = True,
                instance: Instance | None = None,
            ) -> tuple[Instance, Decision]:
                if instance is None:
                    file_hash = uuid.uuid4().hex
                    session.add(File(hash=file_hash, name=name, content=b"%PDF", text=""))
                    instance = Instance(
                        process_id=process_id,
                        file_hash=file_hash,
                        name=name,
                        status="DECIDED",
                        symbols={
                            key: {"value": value, "origin": "document:test"}
                            for key, value in values.items()
                        },
                    )
                    session.add(instance)
                    await session.flush()
                else:
                    file_hash = instance.file_hash
                execution_id = None
                if with_execution:
                    execution = Execution(
                        process_id=process_id,
                        version_id=version.id,
                        inputs={
                            "instances": [
                                {
                                    "id": instance.id,
                                    "file_hash": file_hash,
                                    "symbols": instance.symbols,
                                }
                            ],
                            "source_ids": [],
                        },
                    )
                    session.add(execution)
                    await session.flush()
                    execution_id = execution.id
                decision = Decision(
                    instance_id=instance.id,
                    decision="PAGAR",
                    results=[],
                    rules_hash="test",
                    author=author,
                    reason="approved",
                    version_id=version.id if with_execution else None,
                    execution_id=execution_id,
                )
                session.add(decision)
                await session.flush()
                return instance, decision

            for name, values in rows:
                if name == "old.pdf":
                    # The human approval has a distinct immutable execution snapshot from
                    # the latest engine decision. Treasury must use the selected human row.
                    old_instance, _ = await add_record(name, values, author=ENGINE)
                    _, approval = await add_record(
                        name, values, author="Ana", instance=old_instance
                    )
                    human_execution_id = approval.execution_id
                    human_decision_id = approval.id
                elif name == "legacy.pdf":
                    # Historical rows without an execution snapshot remain visible in
                    # decision history but cannot be used as payment evidence.
                    await add_record(name, values, author="Ana", with_execution=False)
                else:
                    await add_record(name, values, author="Ana")
            await session.commit()

        response = await api.post(
            f"/processes/{process_id}/treasury/preview",
            json={"as_of": "2026-01-01", "weekly_budget": "100.00", "horizon_weeks": 2},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert [row["name"] for row in body["rows"]] == ["old.pdf", "new.pdf"]
        assert [row["week_index"] for row in body["rows"]] == [0, 1]
        assert body["weeks"][0]["total"] == "60.00"
        assert body["weeks"][1]["total"] == "60.00"
        assert body["totals"]["scheduled_amount"] == "120.00"
        assert body["rows"][0]["decision_id"] == human_decision_id
        assert body["rows"][0]["provenance"]["execution_id"] == human_execution_id
        exclusions = {item["name"]: item for item in body["exclusions"]}
        assert exclusions["missing.pdf"]["reason_code"] == "missing_data"
        assert exclusions["legacy.pdf"]["reason_code"] == "stale"
        assert exclusions["legacy.pdf"]["reason"] == "Decision execution snapshot is missing"
