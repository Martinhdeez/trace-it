"""Release integrity, incremental semantics and the restricted SSH protocol."""

import importlib.util
import os
import shutil
import subprocess

import pytest
from release import HERE, prepare


def test_active_release_is_the_adopted_lote2(tmp_path):
    manifest = prepare(tmp_path / "bundle", "lote2")
    assert manifest["id"] == "lote2"
    assert manifest["expected_rows"] == 556
    assert (
        manifest["sha256"]["alberto_erp.py"]
        == "38087d8e2537f19a6537b799ca7a522024c97bbad8a024c358fe180626aa0fb6"
    )


def test_changed_data_without_updated_hash_is_rejected(tmp_path):
    root = tmp_path / "erp"
    shutil.copytree(HERE, root, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "releases/lote2/erp_export_lote2.csv").write_text("changed")
    with pytest.raises(ValueError, match="Checksum"):
        prepare(tmp_path / "bundle", root=root)
    assert not (tmp_path / "bundle").exists()


@pytest.mark.parametrize("name", ["../lote2", "a/b", "", "$(id)"])
def test_release_names_cannot_escape_catalog(tmp_path, name):
    if not name:
        name = ".."
    with pytest.raises(ValueError, match="Invalid release name"):
        prepare(tmp_path / "bundle", name)


def test_incremental_update_keeps_old_entries_and_upserts_without_duplicates(tmp_path):
    bundle = tmp_path / "bundle"
    prepare(bundle, "lote2")
    spec = importlib.util.spec_from_file_location("lote2", bundle / "alberto_erp.py")
    erp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(erp)
    state = erp.EstadoERP(erp._cargar_asientos_embebidos(), 0)
    initial_ids = set(state.por_id)
    updates = erp._cargar_asientos_csv(str(bundle / "erp_export_lote2.csv"))
    assert state.cargar_lote2(updates) == (40, 0)
    assert initial_ids <= set(state.por_id)
    assert state.cargar_lote2(updates) == (0, 40)
    assert len(state.asientos) == len(state.por_id) == 556
    changed = {**state.asientos[0], "estado": "PAGADO"}
    assert state.cargar_lote2([changed]) == (0, 1)
    assert state.por_id[changed["asiento_id"]]["estado"] == "PAGADO"
    assert len(state.asientos) == 556


@pytest.mark.parametrize("action", ["deploy", "deploy-erp"])
def test_receiver_accepts_only_exact_digest_protocol(tmp_path, action):
    sudo = tmp_path / "sudo"
    sudo.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    sudo.chmod(0o755)
    args = [action, "a" * 40, "sha256:" + "b" * 64]
    if action == "deploy":
        args.append("sha256:" + "c" * 64)
    args.append("github-actions[bot]")
    env = {**os.environ, "PATH": str(tmp_path) + ":" + os.environ["PATH"]}

    def run(command):
        return subprocess.run(
            ["bash", str(HERE.parent / "receive.sh")],
            env={**env, "SSH_ORIGINAL_COMMAND": command},
            check=False,
            capture_output=True,
            text=True,
        )

    result = run(" ".join(args))
    assert result.returncode == 0
    assert (
        "trace-it-erp-deploy" if action == "deploy-erp" else "trace-it-deploy"
    ) in result.stdout
    for command in [
        " ".join(args) + " extra",
        " ".join(args).replace("sha256:", "latest:"),
        " ".join(args) + "; id",
        "deploy-erp",
        "",
    ]:
        assert run(command).returncode != 0
