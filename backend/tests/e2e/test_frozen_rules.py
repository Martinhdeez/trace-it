"""The rule set frozen from the norm reloads without any model and decides batch 1 as the
golden says.

`processes/invoice-payment/frozen/2026-09-19/` holds the checks the normalizer and the
compiler wrote from `Norma_Pagos_v3` in the run adopted for delivery. It loads like any
hand-written pack (`make load-frozen`); this test loads it into a fresh process with the real
loader, validates and publishes that draft, and runs the engine over the 471 text PDFs with
the published version's rules.
"""

import json
import uuid

import pytest

from app.core.database import session_factory
from app.features.agents import sandbox
from app.features.decisions.engine import decide
from app.features.processes.definition import Definition, load_definition
from app.features.use_cases import service as use_cases
from app.features.versions import configuration as version_config
from app.features.versions import service as versions
from tests.golden import golden
from tests.support import challenge, pack

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not challenge.available(), reason="challenge submodule not checked out"),
]

FROZEN = pack.PACK / "invoice-payment" / "frozen" / "2026-09-19"


def patient(code: str, instances: list, sources: dict, population: list) -> list:
    return sandbox.run_dataset(code, instances, sources, population, timeout_s=120)


async def test_frozen_set_reloads_and_matches_the_golden() -> None:
    manifest = json.loads((FROZEN / "manifest.json").read_text(encoding="utf-8"))
    data = Definition.model_validate_json((FROZEN / "invoice-payment.json").read_text("utf-8"))
    data.name += f" {uuid.uuid4().hex[:8]}"
    async with session_factory() as session:
        await use_cases.load(session, use_cases.read_file(pack.USE_CASE_FILE))
        process_id = (await load_definition(session, data, FROZEN)).process.id
        draft = await versions.validate(session, process_id)
        assert draft.validation["valid"], draft.validation
        version = await versions.publish(
            session, process_id, draft.revision, draft.validation["hash"], "test", "frozen set"
        )
    active = version_config.rules(version.snapshot)
    assert sorted(r.hash for r in active) == sorted(r["hash"] for r in manifest["rules"])

    instances = golden.symbols()
    dataset = [(s["file_id"], s) for s in instances]
    population = [(s["file_id"], {**s, "_instance": s["file_id"]}) for s in instances]
    verdicts = decide(
        active,
        version_config.outcomes(version.snapshot),
        dataset,
        challenge.sources(),
        population,
        patient,
    )
    expected = golden.expected()
    wrong = [
        (s["file_id"], expected[s["file_id"]]["expected"], v.decision, v.reason)
        for s, v in zip(instances, verdicts, strict=True)
        if v.decision != expected[s["file_id"]]["expected"]
    ]
    assert not wrong, f"{len(wrong)} of {len(instances)} differ from the golden: {wrong}"
    assert len(verdicts) == 471
