"""Execute component deployment and explicit demo maintenance with isolated command fakes."""

import json
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PREVIOUS = (
    "TRACE_BACKEND_IMAGE=old-backend\nTRACE_FRONTEND_IMAGE=old-frontend\n"
    "TRACE_CRIMINAL_RECORDS_IMAGE=old-criminal\n"
)


def deployment(
    tmp_path, *, changed="all", failure="none", reset=False, version=4, mail=True
):
    root = tmp_path / "app"
    (root / "secrets").mkdir(parents=True)
    # The obsolete marker must not cause an automatic reset.
    for name in ["DEPLOY_ENABLED", "DEMO_RESET_ENABLED", "INITIALIZED"]:
        (root / name).touch()
    for name in ["reset-demo.py", "run-seed.py", "seed_cache.py"]:
        (root / name).write_text("fixture")
    (root / "demo-seed.json").write_text(json.dumps({"version": version}))
    for name in ["runtime.env", "htpasswd", "curl.conf"]:
        (root / "secrets" / name).touch()
    (root / "secrets/compose.env").write_text("POSTGRES_PASSWORD=test\n")
    (root / "secrets/mail-compose.env").write_text("TRACE_MAIL_IMAGE=old-mail\n")
    (root / "current.env").write_text(PREVIOUS)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "fake"
    fake.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys, tarfile
args = sys.argv[1:]
cmd = pathlib.Path(sys.argv[0]).name
with open(os.environ["CALLS"], "a") as f:
    f.write(json.dumps([cmd, args, {k: os.environ.get(k) for k in
        ["TRACE_MAIL_IMAGE", "TRACE_BACKEND_IMAGE", "TRACE_FRONTEND_IMAGE", "TRACE_CRIMINAL_RECORDS_IMAGE"]}]) + "\\n")
failure = os.environ["FAILURE"]
changed = os.environ["CHANGED"].split(",")
if cmd == "df": print("Available\\n999999999")
elif cmd == "docker":
    if args[:2] == ["image", "inspect"]:
        if "revision" in args[3]: print("a" * 40)
        else:
            kind = "criminal" if "criminal-hash" in args[3] else ("frontend" if "frontend" in args[-1] else "backend")
            new = not args[-1].startswith("old-")
            if failure == "label" and new: print("invalid")
            elif changed == ["legacy"] and not new: print("<no value>")
            else: print(("b" if new and (kind in changed or changed == ["all"]) else "c") * 64)
    if args[:2] == ["ps", "-q"] and os.environ["MAIL"] == "1": print("mail-id")
    if args[0] == "pull" and failure == "pull": sys.exit(1)
    if "nginx" in args and failure == "nginx": sys.exit(1)
    if "heads" in args and failure == "migration-preflight": sys.exit(1)
    if "pg_dump" in args:
        if failure == "backup": sys.exit(1)
        print("dump")
    if any("tarfile.open" in a for a in args):
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"): pass
    if "upgrade" in args and failure == "migration": sys.exit(1)
    if "--confirm-demo-reset" in args and failure == "reset": sys.exit(1)
    if "app.features.decisions.demo_seed" in args and failure == "seed-run": sys.exit(1)
    if "verify-cache" in args and failure == "cache": sys.exit(1)
    if "/srv/run-seed.py" in args and args[-3] == "run" and failure == "seed-run": sys.exit(1)
    if "check" in args and failure == "mail-check": sys.exit(1)
    if "up" in args and args[-1] == failure.removesuffix("-up"):
        image = os.environ.get("TRACE_" + args[-1].upper() + "_IMAGE", "")
        if not image.startswith("old-"): sys.exit(1)
elif cmd == "curl" and failure == "public": sys.exit(22)
""")
    fake.chmod(0o755)
    for name in ["docker", "curl", "df"]:
        (bindir / name).symlink_to(fake)
    script = (HERE / "deploy.sh").read_text().replace('[[ "$EUID" == 0 ]]', "true")
    script = script.replace(
        "export PATH=/usr/sbin:/usr/bin:/sbin:/bin",
        f"export PATH={bindir}:/usr/bin:/bin",
    )
    script = script.replace("/opt/trace-it", str(root))
    script = script.replace("/run/lock/trace-it-deploy.lock", str(tmp_path / "lock"))
    script = script.replace("/run/trace-it-docker.", str(tmp_path / "docker."))
    target = tmp_path / "deploy.sh"
    target.write_text(script)
    arguments = (
        ["--reset-demo"]
        if reset
        else ["a" * 40, "sha256:" + "b" * 64, "sha256:" + "c" * 64, "actor"]
    )
    result = subprocess.run(
        ["bash", str(target), *arguments],
        input="test-token",
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "CALLS": str(tmp_path / "calls"),
            "FAILURE": failure,
            "CHANGED": changed,
            "MAIL": "1" if mail else "0",
        },
    )
    calls = [json.loads(line) for line in (tmp_path / "calls").read_text().splitlines()]
    assert "test-token" not in result.stdout + result.stderr
    return root, result, calls


def promotions(calls):
    return [call for call in calls if call[0] == "docker" and "up" in call[1]]


@pytest.mark.parametrize(
    "changed", ["none", "frontend", "backend", "criminal", "all", "legacy"]
)
def test_only_changed_components_are_replaced_without_reset(tmp_path, changed):
    root, result, calls = deployment(tmp_path, changed=changed)
    assert result.returncode == 0, result.stderr
    args = [c[1] for c in calls]
    all_changed = changed in {"all", "legacy"}
    expected = set()
    if changed == "backend" or all_changed:
        expected.update(["backend", "mail-ingestion"])
    if changed == "frontend" or all_changed:
        expected.add("frontend")
    if changed == "criminal" or all_changed:
        expected.add("criminal-records")
    assert {call[1][-1] for call in promotions(calls)} == expected
    assert all("--no-deps" in call[1] for call in promotions(calls))
    assert not any("stop" in a and "frontend" in a for a in args)
    assert not any("--confirm-demo-reset" in a or "verify-cache" in a for a in args)
    assert not any("activate-route.py" in " ".join(a) for a in args)
    if "backend" not in expected:
        assert not any("pg_dump" in a or "upgrade" in a or "stop" in a for a in args)
        assert (
            root / "secrets/mail-compose.env"
        ).read_text() == "TRACE_MAIL_IMAGE=old-mail\n"
    else:
        stopped = next(i for i, a in enumerate(args) if "stop" in a)
        for i, a in enumerate(args):
            if "pull" in a or "check" in a or "heads" in a or "nginx" in a:
                assert i < stopped
        assert "b" * 64 in (root / "secrets/mail-compose.env").read_text()
    selected = (root / "current.env").read_text()
    if "backend" not in expected:
        assert "TRACE_BACKEND_IMAGE=old-backend" in selected
    if "frontend" not in expected:
        assert "TRACE_FRONTEND_IMAGE=old-frontend" in selected
    assert (root / "previous.env").read_text() == PREVIOUS


@pytest.mark.parametrize(
    "failure", ["pull", "label", "nginx", "migration-preflight", "mail-check"]
)
def test_preflight_failures_do_not_stop_any_service(tmp_path, failure):
    root, result, calls = deployment(tmp_path, failure=failure)
    assert result.returncode != 0
    assert not promotions(calls)
    assert not any("stop" in c[1] for c in calls)
    assert (root / "current.env").read_text() == PREVIOUS


@pytest.mark.parametrize(
    "failure", ["backup", "migration", "backend-up", "frontend-up", "public"]
)
def test_failure_restores_touched_components_and_mail(tmp_path, failure):
    root, result, calls = deployment(tmp_path, failure=failure)
    assert result.returncode != 0
    assert (root / "current.env").read_text() == PREVIOUS
    assert (
        root / "secrets/mail-compose.env"
    ).read_text() == "TRACE_MAIL_IMAGE=old-mail\n"
    restored = promotions(calls)[-1]
    assert restored[1][-1] == "mail-ingestion"
    assert restored[2]["TRACE_MAIL_IMAGE"] == "old-mail"
    assert "Database is NEVER restored automatically" in result.stderr


def test_frontend_failure_does_not_touch_backend_or_mail(tmp_path):
    _, result, calls = deployment(tmp_path, changed="frontend", failure="frontend-up")
    assert result.returncode != 0
    assert [c[1][-1] for c in promotions(calls)] == ["frontend", "frontend"]
    assert promotions(calls)[-1][2]["TRACE_FRONTEND_IMAGE"] == "old-frontend"
    assert not any("stop" in c[1] for c in calls)


@pytest.mark.parametrize("version", [3, 4])
@pytest.mark.parametrize("failure", ["none", "backup", "reset", "seed-run", "cache"])
def test_explicit_reset_is_separate_and_backed_up(tmp_path, version, failure):
    if version == 3 and failure == "cache":
        pytest.skip("Version 3 has no full cache")
    root, result, calls = deployment(
        tmp_path, reset=True, version=version, failure=failure
    )
    args = [c[1] for c in calls]
    assert (root / "current.env").read_text() == PREVIOUS
    assert not (root / "previous.env").exists()
    assert not any("pull" in a or "login" in a or "upgrade" in a for a in args)
    assert not any("stop" in a and "frontend" in a for a in args)
    resets = [i for i, a in enumerate(args) if "--confirm-demo-reset" in a]
    if failure in {"backup", "cache"}:
        assert not resets
    else:
        assert len(resets) == 1
        for operation in ["pg_dump", "pg_restore", "stop"]:
            assert next(i for i, a in enumerate(args) if operation in a) < resets[0]
    assert result.returncode == (0 if failure == "none" else 1), result.stderr
    if failure == "cache":
        assert not any("stop" in a for a in args)
    else:
        assert promotions(calls)[-1][1][-1] == "mail-ingestion"
    assert not any("initialize" in a for a in args)


def test_stopped_mail_stays_stopped(tmp_path):
    _, result, calls = deployment(tmp_path, changed="backend", mail=False)
    assert result.returncode == 0, result.stderr
    assert [c[1][-1] for c in promotions(calls)] == ["backend"]
