# demo-logs

Disposable local run logs and a throwaway dashboard, kept so the team can follow the program
flow. Not part of the product: nothing here is loaded, tested or maintained. Some reports are
in Spanish.

The dashboard (`dashboard/`) starts with `dashboard/run.sh`, serves on port 8020 and needs
the API running on :8010.

## Main reports

- `INFORME-MANANA.md`: overnight report: from Alberto's original rule text to decisions, 471/471 against the golden set.
- `REPORT-integrated-run.md`: one integrated run with real models, what ran and how to inspect its traces in the dashboard.
- `REPORT-trazabilidad.md`: per-module traceability: spans, fields, real trace trees, metrics, curl audit guide (Spanish).
- `PRUEBA-EN-VIVO.md`: live test guide: URLs, how to start a demo run and what to look at.
- `coverage/SUMMARY.txt`: audit spans per step (ok/error) for the API coverage run whose captures are in `coverage/`.
- `delivery/`: the submitted plan (`albertitos_plan.*`) and the architecture diagram.

Raw logs (`api*.log`, `erp.log`, `monitor.log`) and captured outputs (`integrated/`,
`outcomes*.jsonl`) are as the runs left them.
The `outcomes*.jsonl` files here (`outcomes_norm.jsonl`, `outcomes_p3.jsonl`, `integrated/outcomes.jsonl`) are old run artifacts, not the delivery: the batch-1 candidates are `delivery/outcomes_system.jsonl` and `delivery/outcomes_mateo_review.jsonl` at the repository root (`delivery/README.md`).
