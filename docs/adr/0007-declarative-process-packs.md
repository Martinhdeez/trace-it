---
status: accepted  # policies and sources.json: proposed
---

# Keep all domain knowledge in declarative process packs

## Context
ADR 0001 makes invoice payment the first configured process, not logic in the core. The
application must serve a second use case without code changes, and a setup must be
reproducible on any machine with one command. At the same time the manager changes rules
and configuration at runtime, and those changes must never be lost by reloading files.

## Alternatives considered
- **Domain logic in code (invoice module).**
  - Pros: fastest path to batch 1.
  - Cons: contradicts ADR 0001; every new process is a code change.
- **Everything only in the database, edited through the UI.**
  - Pros: one source of truth at runtime.
  - Cons: not reproducible from git; a fresh machine starts empty; no review via PRs.
- **YAML files as the runtime source.** Discarded in `.artifacts/specs/2026-09-18-reglas-sistema.md`
  §6: runtime changes would mean editing files.
- **Pack files for bootstrap + database for runtime, with export back (chosen).**
  - Pros: reproducible and reviewable; runtime changes without restarts; round trip.
  - Cons: two places to look; the loader must define who wins.

## Decision
- A **process pack** is a folder `processes/<pack>/` with `process.json` (today one file
  per process: `procesos/pago-facturas.json`, `procesos/gastos-viaje.json`):
  - `name`, `description`: the description states the domain conventions every rule
    inherits (normalisation, units, tolerances, missing values). Compilers and the
    assistant receive it as shared context.
  - `decision_types`: `[{name, priority, is_default, requires_human}]`, exactly one default,
    and the default cannot require a human. No decision name is hardcoded.
  - `symbols`: `[{name, type, description}]`; `rules`: `[{text, kind, decision}]`;
    optional `users` with roles.
  - `policies` (**proposed**): `exported_decision` (`engine` | `final`),
    `unresolved_review` (`block` | a decision type), `unresolved_escalation` (`keep`).
    Invoice pack: `engine`, `block`, `keep` (ADR 0009).
  - `sources.json` (**proposed**): connectors per source, credentials by `.env` name only.
- **Loader contract:** validate the whole pack first and reject it whole if invalid;
  idempotent; adds what is missing; a rule whose text changed enters as a new **draft**;
  active rules are never modified or removed by a load.
- **Export** returns the current process (and agent configuration) as pack JSON so a change
  made in the app can be committed.

## Consequences
- New process = new pack; a new kind of source is the only code to write.
- The loader today still overwrites decision types, symbols and the description with the
  file's values (`session.merge`). That contradicts "loading never overrides runtime
  decisions" once those become editable in the app; they should be versioned like rules.
- Export and `make load PROCESS=<pack>` are not implemented yet.

## Evidence
- Loader and validation: `procesos/definicion.py` (`Definicion._coherente`,
  `cargar_definicion`); 3 tests in `procesos/tests/test_definicion.py`.
- Invoice pack: 16 rules, 12 symbols, 3 decision types (ESCALAR 3 requires human,
  NO_PAGAR 2, PAGAR 1 default). A quick parser over the 471 text PDFs gave 433 PAGAR,
  36 NO_PAGAR, 2 ESCALAR, consistent with the trap analysis
  (`.artifacts/specs/2026-09-18-analisis-caja-v3.md`); 29 scans pending.
- `make setup` loads the invoice pack; `gastos-viaje.json` loads with the same code.

## Related
ADR 0001, 0003, 0009, 0011. Plan P11, P12, P19; `docs/process-packs.md`.
