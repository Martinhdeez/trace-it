"""Exercise the deployment transaction with isolated command fakes, never the VPS."""

import json
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    "failure", ["none", "unchanged", "canary", "promote", "public"]
)
def test_deploy_failure_keeps_previous_image_and_success_records_release(
    tmp_path, failure
):
    root = tmp_path / "app"
    erp = root / "erp"
    erp.mkdir(parents=True)
    (root / "DEPLOY_ENABLED").touch()
    (erp / "compose.release.yml").touch()
    previous = "TRACE_ERP_IMAGE=sha256:" + "c" * 64 + "\n"
    (erp / "current.env").write_text(previous)
    manifest = json.loads((HERE / "releases/lote2/release.json").read_text())
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "fake"
    fake.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys
cmd = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
root = pathlib.Path(os.environ["TEST_ROOT"])
failure = os.environ["TEST_FAILURE"]
with (root / "calls").open("a") as f:
    f.write(json.dumps([cmd, args, os.environ.get("TRACE_ERP_IMAGE")]) + "\\n")
manifest = json.loads((root / "manifest.json").read_text())
if cmd == "df":
    print("Available\\n999999999")
elif cmd == "curl":
    if failure == "public": sys.exit(22)
    print(json.dumps({**manifest, "rows": manifest["expected_rows"]}))
elif args[:2] == ["image", "inspect"]:
    if "revision" in args[3]: print("a" * 40)
    else: print(("c" if failure == "unchanged" or args[-1].startswith("sha256:") else "b") * 64)
elif args[0] == "run":
    print("canary-id")
elif args[:3] == ["exec", "canary-id", "cat"]:
    print(json.dumps(manifest))
elif args[:4] == ["exec", "canary-id", "python", "smoke.py"] and failure == "canary":
    sys.exit(1)
elif args[0] == "compose" and "up" in args and failure == "promote" and os.environ.get("TRACE_ERP_IMAGE"):
    sys.exit(1)
""")
    fake.chmod(0o755)
    for name in ["docker", "curl", "df"]:
        (bindir / name).symlink_to(fake)
    # Only host paths/root guard are substituted; execute the real transaction body.
    script = (HERE / "deploy.sh").read_text()
    script = script.replace('[[ "$EUID" == 0 && "$#" == 3 ]]', '[[ "$#" == 3 ]]')
    script = script.replace(
        "export PATH=/usr/sbin:/usr/bin:/sbin:/bin",
        f"export PATH={bindir}:/usr/bin:/bin",
    )
    script = script.replace("/opt/trace-it", str(root))
    script = script.replace("/run/lock/trace-it-deploy.lock", str(tmp_path / "lock"))
    script = script.replace("/run/trace-it-erp-docker.", str(tmp_path / "docker."))
    target = tmp_path / "deploy.sh"
    target.write_text(script)
    result = subprocess.run(
        ["bash", str(target), "a" * 40, "sha256:" + "b" * 64, "actor"],
        input="fake-token",
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "TEST_ROOT": str(tmp_path), "TEST_FAILURE": failure},
    )
    calls = [json.loads(line) for line in (tmp_path / "calls").read_text().splitlines()]
    promotions = [
        call
        for call in calls
        if call[0] == "docker" and call[1][0] == "compose" and "up" in call[1]
    ]
    assert "fake-token" not in result.stdout + result.stderr
    if failure == "unchanged":
        assert result.returncode == 0, result.stderr
        assert not promotions
        assert (erp / "current.env").read_text() == previous
        assert not any(call[1][0] == "run" for call in calls)
        return
    if failure == "none":
        assert result.returncode == 0, result.stderr
        assert (
            "ghcr.io/martinhdeez/trace-it/erp@sha256:"
            in (erp / "current.env").read_text()
        )
        assert (erp / "previous.env").read_text() == previous
        assert len(promotions) == 1
    else:
        assert result.returncode != 0
        assert (erp / "current.env").read_text() == previous
        if failure == "canary":
            assert promotions == []
        else:
            assert len(promotions) == 2
            assert promotions[-1][2] is None  # rollback resolves the old env-file image
    assert any(call[1][:2] == ["rm", "-f"] for call in calls)
