"""ERP update startup uses the original bridge loader and preserves both entry IDs."""

from pathlib import Path

import pytest
from test_erp import server


def test_load_real_update():
    update = (
        Path(__file__).resolve().parents[2]
        / ".context/500-sombras-de-alberto/erp_export_lote2.csv"
    )
    if not update.is_file():
        pytest.skip("Batch 2 material required")
    state = server.load_state(str(update))
    assert len(state.asientos) == 556
    assert state.lote2_cargado
    assert {r["estado"] for r in state.asientos if r["pedido"] == "PO-2026-0071"} == {
        "PAGADA",
        "PENDIENTE",
    }


def test_requested_missing_update_fails_startup(tmp_path):
    with pytest.raises(FileNotFoundError):
        server.load_state(str(tmp_path / "missing.csv"))


def test_versioned_release_rejects_untracked_csv_override(tmp_path, monkeypatch):
    from release import prepare

    bundle = tmp_path / "bundle"
    prepare(bundle, "lote2")
    monkeypatch.setenv("TRACE_ERP_UPDATE", str(bundle / "erp_export_lote2.csv"))
    with pytest.raises(ValueError, match="must declare updates"):
        server.initialize(bundle)


def test_manual_install_retains_explicit_csv_overlay(tmp_path, monkeypatch):
    update = Path(__file__).resolve().parent / "releases/lote2/erp_export_lote2.csv"
    monkeypatch.setenv("TRACE_ERP_UPDATE", str(update))
    server.initialize(tmp_path)
    assert len(server.erp.ESTADO.asientos) == 556
    assert server.RELEASE is None
