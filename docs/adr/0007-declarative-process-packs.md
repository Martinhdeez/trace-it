---
status: accepted
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
- **YAML files as the runtime source.** Discarded in `.artifacts/archive/2026-09-18-reglas-sistema.md`
  §6: runtime changes would mean editing files.
- **Pack files for bootstrap + database for runtime, with export back (chosen).**
  - Pros: reproducible and reviewable; runtime changes without restarts; round trip.
  - Cons: two places to look; the loader must define who wins.

## Decision
- A **process pack** is `processes/<name>.json` plus an optional folder `processes/<name>/`
  for what does not fit in it (`sources.json`, hand-written rule code):
  - `name`, `description`: the description states the domain conventions every rule
    inherits (normalisation, units, tolerances, missing values). Compilers and the
    assistant receive it as shared context.
  - `decision_types`: `[{name, priority, is_default, requires_human}]`: exactly one default,
    which cannot require a human; distinct priorities; at least one type that requires a
    human, where the engine sends what it cannot decide (ADR 0016). No decision name is
    hardcoded.
  - `symbols`: `[{name, type, description}]`; `rules`: `[{text, type, decision, code?}]`,
    where `code` names a file with hand-written `evaluate` code, so a process runs before any
    model is configured; optional `users` with roles `manager` (resolves escalations,
    approves rule changes) and `operator`.
  - `<name>/sources.json`: one HTTP connector per source (ADR 0013), credentials by `.env`
    variable name only. Read on every sync.
  - Export policies (`exported_decision: engine | final`) were designed in ADR 0009 and not
    implemented: the export is the engine's decision (ADR 0016).
- **Loader contract:** validate the whole pack first and reject it whole if invalid;
  idempotent; adds what is missing; a rule whose text changed enters as a new **draft**;
  active rules are never modified or removed by a load. Changes to decision types, symbols
  or the description go into a new draft process version, never into the active one
  (ADR 0015).
- **Export** returns the current process (and agent configuration) as pack JSON so a change
  made in the app can be committed.

## Consequences
- New process = new pack; a new kind of source is the only code to write.
- **Known gap:** the loader still overwrites decision types, symbols and the description
  with the file's values (`session.merge`). That contradicts "loading never overrides
  runtime decisions"; ADR 0015 (proposed) versions them with the whole process.
- Export back to pack JSON is not implemented.

## Evidence
- Loader and validation: `processes/definition.py` (`Definition._consistent`,
  `load_definition`); 5 tests in `processes/tests/test_definition.py`, 4 in `test_api.py`.
- Invoice pack: 16 rules with hand-written code, 12 symbols, 3 decision types (ESCALAR 3
  requires human, NO_PAGAR 2, PAGAR 1 default). `make demo` over the 500 files of batch 1:
  433 PAGAR, 36 NO_PAGAR, 31 ESCALAR (29 of them scans without a text layer), identical to
  the golden reference on all 471 text PDFs.
- `make setup` loads the invoice pack; `travel-expenses.json` loads with the same code.

## Related
ADR 0001, 0003, 0013, 0014, 0015, 0016. `processes/README.md`.
