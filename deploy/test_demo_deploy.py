"""Execute the installed deployment protocol with fake infrastructure commands."""

import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "failure", ["none", "backup", "reset", "seed-run", "mail-check"]
)
def test_demo_deployment_order_and_failure(tmp_path, failure):
    root = tmp_path / "app"
    (root / "secrets").mkdir(parents=True)
    for name in ["DEPLOY_ENABLED", "DEMO_RESET_ENABLED", "INITIALIZED"]:
        (root / name).touch()
    for name in ["reset-demo.py", "demo-seed.json"]:
        (root / name).write_text("fixture")
    for name in ["runtime.env", "htpasswd", "curl.conf"]:
        (root / "secrets" / name).touch()
    (root / "secrets/compose.env").write_text("POSTGRES_PASSWORD=test\n")
    (root / "secrets/mail-compose.env").write_text("TRACE_MAIL_IMAGE=old-mail\n")
    (root / "activate-route.py").write_text("")
    previous = "TRACE_BACKEND_IMAGE=old-backend\nTRACE_FRONTEND_IMAGE=old-frontend\n"
    (root / "current.env").write_text(previous)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "fake"
    fake.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys, tarfile
args = sys.argv[1:]
cmd = pathlib.Path(sys.argv[0]).name
with open(os.environ["CALLS"], "a") as f:
    f.write(json.dumps([cmd, args, os.environ.get("TRACE_MAIL_IMAGE")]) + "\\n")
failure = os.environ["FAILURE"]
if cmd == "df": print("Available\\n999999999")
elif cmd == "docker":
    if args[:2] == ["image", "inspect"]: print("a" * 40)
    if args[:2] == ["ps", "-q"]: print("mail-id" if "mail-ingestion" in " ".join(args) else "registry-id")
    if "pg_dump" in args:
        if failure == "backup": sys.exit(1)
        print("dump")
    if any("tarfile.open" in a for a in args):
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"): pass
    if "--confirm-demo-reset" in args and failure == "reset": sys.exit(1)
    if "app.features.decisions.demo_seed" in args and failure == "seed-run": sys.exit(1)
    if "check" in args and failure == "mail-check": sys.exit(1)
""")
    fake.chmod(0o755)
    for name in ["docker", "curl", "df"]:
        (bindir / name).symlink_to(fake)
    script = Path(__file__).with_name("deploy.sh").read_text()
    script = script.replace('[[ "$EUID" == 0 && "$#" == 4 ]]', '[[ "$#" == 4 ]]')
    script = script.replace(
        "export PATH=/usr/sbin:/usr/bin:/sbin:/bin",
        f"export PATH={bindir}:/usr/bin:/bin",
    )
    script = script.replace("/opt/trace-it", str(root))
    script = script.replace("/run/lock/trace-it-deploy.lock", str(tmp_path / "lock"))
    script = script.replace("/run/trace-it-docker.", str(tmp_path / "docker."))
    target = tmp_path / "deploy.sh"
    target.write_text(script)
    result = subprocess.run(
        [
            "bash",
            str(target),
            "a" * 40,
            "sha256:" + "b" * 64,
            "sha256:" + "c" * 64,
            "actor",
        ],
        input="test-token",
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "CALLS": str(tmp_path / "calls"), "FAILURE": failure},
    )
    calls = [json.loads(line) for line in (tmp_path / "calls").read_text().splitlines()]
    args = [call[1] for call in calls]
    resets = [i for i, a in enumerate(args) if "--confirm-demo-reset" in a]
    seed_runs = [
        i for i, a in enumerate(args) if "app.features.decisions.demo_seed" in a
    ]
    if failure == "backup":
        assert not resets
    else:
        assert len(resets) == 1
        assert next(i for i, a in enumerate(args) if "pg_dump" in a) < resets[0]
        assert next(i for i, a in enumerate(args) if "pg_restore" in a) < resets[0]
        assert (
            next(i for i, a in enumerate(args) if "stop" in a and "frontend" in a)
            < resets[0]
        )
    if failure in {"backup", "reset"}:
        assert not seed_runs
    else:
        assert len(seed_runs) == 1
        assert resets[0] < seed_runs[0]
    assert not any("initialize" in a for a in args)
    if failure == "none":
        assert result.returncode == 0, result.stderr
        assert (root / "previous.env").read_text() == previous
        mail = [c for c in calls if "up" in c[1] and "mail-ingestion" in c[1]]
        assert len(mail) == 1
        assert mail[0][2].endswith("b" * 64)
        assert "b" * 64 in (root / "secrets/mail-compose.env").read_text()
    else:
        assert result.returncode != 0
        assert (root / "current.env").read_text() == previous
        assert (
            root / "secrets/mail-compose.env"
        ).read_text() == "TRACE_MAIL_IMAGE=old-mail\n"
        assert not any("up" in a and "mail-ingestion" in a for a in args)
