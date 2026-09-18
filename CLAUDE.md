# Repository context

Trace Pay is the team's application for the "500 Sombras de Alberto" hackathon.
It is a reusable, configurable decision system. Invoice payment is its first
configured process, not logic that belongs in the core.

Read `docs/adr/0001-configurable-decision-process.md` before changing product or
architecture documentation. It is the accepted design decision and wins when a
draft document disagrees with it. `docs/plano-aplicacion.md` and files under
`.artifacts/` are working material, not authority.

Keep deterministic rule findings, system recommendations, and final decisions
separate. Published process versions and historical decisions are immutable.
LLMs may draft, extract, explain, and propose. They may not change published
rules or finalize escalated cases without manager approval.

The challenge inputs live in the `.context/500-sombras-de-alberto` submodule.
Do not modify supplied invoices, the workbook, or recovered ERP documentation.

Backend code lives under `backend/`. Run backend checks from that directory with
`uv run ruff check .` and `uv run pytest`.
