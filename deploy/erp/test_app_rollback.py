"""A backend-only rollback must leave the independent registry service running."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "component_deploy_tests",
    Path(__file__).resolve().parents[1] / "test_demo_deploy.py",
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_backend_rollback_preserves_registry_and_frontend(tmp_path):
    _, result, calls = helper.deployment(
        tmp_path, changed="backend", failure="migration"
    )
    assert result.returncode != 0
    assert [call[1][-1] for call in helper.promotions(calls)] == [
        "backend",
        "mail-ingestion",
    ]
    assert helper.promotions(calls)[0][2]["TRACE_BACKEND_IMAGE"] == "old-backend"
    assert not any("stop" in call[1] and "frontend" in call[1] for call in calls)
