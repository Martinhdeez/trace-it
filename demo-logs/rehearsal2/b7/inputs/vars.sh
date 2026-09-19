# B7 rehearsal: host API on the restored copy (never the live database).
export BACKEND_PORT=8050 ERP_PORT=8051
export TRACE_ERP_URL=http://127.0.0.1:8051
export TRACE_DATABASE_URL=postgresql+psycopg://trace:trace@localhost:5432/trace_rehearsal2_test
export TRACEPAY_DATA_DIR=/private/tmp/claude-501/-Users-apple-orca-workspaces-trace-pay-pelican/81951f95-6768-4335-9ebf-6930a2d5a39b/scratchpad/b8b7/data
# Section 0 of the runbook
API=http://localhost:${BACKEND_PORT:-8000}
L2=/private/tmp/claude-501/-Users-apple-orca-workspaces-trace-pay-pelican/81951f95-6768-4335-9ebf-6930a2d5a39b/scratchpad/b8b7/lote_2_sorpresa
B1=.context/500-sombras-de-alberto/facturas
MANAGER='X-User-Id: 1'
FROZEN=../processes/invoice-payment/frozen/2026-09-19/invoice-payment.json
LOG=demo-logs/rehearsal2/b7
