"""The first registry-service release can restore an older application image."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("had_registry", [False, True])
def test_rollback_restores_app_and_only_a_preexisting_registry(tmp_path, had_registry):
    script = (Path(__file__).resolve().parents[1] / "deploy.sh").read_text()
    rollback = script[
        script.index("rollback() {") : script.index("\ntrap rollback ERR")
    ]
    (tmp_path / "current.env").write_text("TRACE_BACKEND_IMAGE=old-image\n")
    # Execute the real rollback function with an isolated Compose function. A previous
    # backend image does not necessarily contain the new criminal-records executable.
    harness = (
        """set -Eeuo pipefail
fake_compose() { printf '%s|%s\\n' "$TRACE_BACKEND_IMAGE" "$*" >> calls; }
compose=(fake_compose)
backup=backups/test
previous_criminal=$PREVIOUS_CRIMINAL
TRACE_BACKEND_IMAGE=new-image
"""
        + rollback
        + "\nrollback\n"
    )
    result = subprocess.run(
        ["bash", "-c", harness],
        cwd=tmp_path,
        env={
            **os.environ,
            "PREVIOUS_CRIMINAL": "registry-container" if had_registry else "",
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    calls = (tmp_path / "calls").read_text().splitlines()
    assert calls[0] == "old-image|up -d --wait --wait-timeout 180 backend frontend"
    if had_registry:
        assert calls[1] == "old-image|up -d --wait --wait-timeout 120 criminal-records"
    else:
        assert calls[1] == "old-image|stop criminal-records"
    assert "Database is NEVER restored automatically" in result.stderr
