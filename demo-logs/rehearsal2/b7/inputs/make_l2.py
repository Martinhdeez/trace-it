"""Simulated Saturday delivery: 10 batch-1 PDFs under new names with changed bytes,
an ERP update CSV and a one-sentence norm v4."""

from pathlib import Path

ROOT = Path("/Users/apple/orca/projects/trace-pay/.claude/worktrees/agent-adafdc763e2a934c0")
B1 = ROOT / ".context/500-sombras-de-alberto/facturas"
L2 = Path(__file__).parent / "lote_2_sorpresa"
(L2 / "facturas").mkdir(parents=True, exist_ok=True)

text = sorted(p for p in B1.glob("*.pdf") if not p.name.startswith(("scan_", "fax_")))
picked = text[5:500:70][:7] + [B1 / "scan_005.pdf", B1 / "scan_021.pdf", B1 / "scan_025.pdf"]
for p in picked:
    (L2 / "facturas" / f"lote2_{p.name}").write_bytes(p.read_bytes() + b"\n% lote2 rehearsal copy\n")

(L2 / "erp_export_lote2.csv").write_text(
    "asiento_id,fecha_registro,proveedor_id,nif,pedido,importe_esperado,estado\n"
    "AS-00476,2026-03-28,P002,A41220987,PO-2026-0476,2551.64,PENDIENTE\n"
    "AS-00601,2026-09-19,P001,B46102331,PO-2026-0601,1210.00,PENDIENTE\n"
)
(L2 / "norma_v4.txt").write_text(
    "An invoice whose total is above 10,000 EUR is reviewed by a person before it is paid.\n"
)
print("\n".join(sorted(p.name for p in (L2 / "facturas").iterdir())))
