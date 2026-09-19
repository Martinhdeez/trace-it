"""Deployment identity must follow build inputs rather than unrelated commits."""

import importlib.util
import subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "component_hash", Path(__file__).with_name("component-hash.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_component_inputs_are_independent_and_follow_actual_bytes(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    paths = [
        "backend/app/main.py",
        "frontend/src/App.tsx",
        "docs/other.md",
        "processes/hiring-screening/criminal_records_erp.py",
    ]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    before = {name: module.fingerprint(name, tmp_path) for name in module.INPUTS}
    (tmp_path / "frontend/src/App.tsx").write_text("frontend change")
    after = {name: module.fingerprint(name, tmp_path) for name in module.INPUTS}
    assert before["frontend"] != after["frontend"]
    assert before["backend"] == after["backend"]
    assert before["criminal"] == after["criminal"]
    (tmp_path / "docs/other.md").write_text("unrelated change")
    assert after == {name: module.fingerprint(name, tmp_path) for name in module.INPUTS}
    (tmp_path / "backend/app/main.py").write_text("backend change")
    assert after["backend"] != module.fingerprint("backend", tmp_path)
    assert after["criminal"] == module.fingerprint("criminal", tmp_path)
