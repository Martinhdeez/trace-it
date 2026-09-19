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
