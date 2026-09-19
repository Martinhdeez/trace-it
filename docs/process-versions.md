# Process versions and replay

A process runs one immutable published configuration. Loading a pack, compiling a rule,
or editing a draft cannot change that configuration. Every publication requires a manager.
The backend implements this flow; no frontend changes are included.

A version contains outcome definitions and priorities, symbols, description, exact rule
code and tests, optional reviewer configuration, approved guidance, and agent settings with
configuration references and resolved default models. Provider credentials stay in the environment. Changing
shared use-case settings does not change published processes: explicitly refresh the draft's
agent settings and publish it. Source data is separate from configuration.

## Prepare and publish

All draft operations and replay require a manager's `X-User-Id`.

1. `POST /processes/definition` loads a pack into the authoring workspace and prepares a
   draft. An existing published process keeps running. A conflicting existing draft must
   be edited or discarded first. A new process cannot run before its first publication.
2. Compile rule text using the existing rule endpoints. Compilation always leaves a draft,
   including when required data is missing. Compilation never activates a rule.
3. `PUT /processes/{id}/draft` starts from the active version or edits the existing draft.
   Supply `expected_revision` when editing. Optional fields are `description`,
   `decision_types`, `symbols`, `decision_review`, `rule_ids`, `guidance`,
   `refresh_agents` and `restore_version_id`. Omitted fields retain their values;
   `decision_review: null` disables review. `rule_ids` selects the complete candidate set.
4. `POST /processes/{id}/draft/validate` checks configuration, stored tests and impact on
   decided cases. It compares the candidate with each case's last engine decision and
   returns the draft with `validation.valid`, changes, review conflicts, runtime errors,
   and a validation hash. A case a person resolved never blocks: if the engine outcome
   would change, it is listed in `resolved_by_person` and the person's decision stays.
   It never calls a model or changes cases.
5. `POST /processes/{id}/draft/publish` with `revision`, `validation_hash` and a nonblank
   `reason` approves that exact candidate. Changed evidence or configuration requires
   another validation. Publication atomically creates a version, switches the active
   reference, retains the approved validation report, records findings and consumes the draft.

The old `/rules/{id}/activate` and `/retire` endpoints now only stage inclusion/removal in
the process draft. Their returned rule status still describes the published/workspace rule;
fetch the draft to see the proposed configuration. They never publish by themselves.

`GET /processes/{id}/draft` reads the candidate. `DELETE /processes/{id}/draft?revision=N`
discards it with a revision check. `GET /processes/{id}/versions` lists publication history;
`GET /process-versions/{id}` reads one immutable snapshot.

An approved learning proposal publishes through the same module in its adoption transaction.
It extends the active configuration, never an unrelated draft. A draft based on an older
version must explicitly restore the current version and reapply its edits before validation.
Learning retains its existing validation and human-conflict protections; there is no second
approval step.

## Execution and replay

Each batch captures the published version, source snapshot IDs, case symbols and the full
comparison population. Decisions reference that execution and version. Case/source writes
and publication serialize with execution on the process lock. The lock is held through
optional review, so publication may wait for a running batch. This deliberately favors
simple, consistent behavior at current volumes.

`POST /decisions/{id}/replay` evaluates one engine decision using captured inputs and saved
rule code in the sandbox. It returns the reproduced outcome, findings and a `matches` flag.
It writes no decisions and calls no LLM. Replay assumes the current engine/sandbox contract;
it does not preserve a Python runtime or executable environment. The optional LLM review
is retained as evidence, not rerun with a claim of reproducibility.

Source refreshes do not create process versions. New executions use the latest snapshots.
Historical queue classification and allowed human resolutions use the decision's original
version. A publication does not automatically reprocess old cases or change export results.
Use the existing explicit reprocess operation when that is intended.

Rollback prepares a draft with `restore_version_id`, validates its impact against current
evidence, and publishes it as a new version. Review conflicts still prevent publication.

## Migration and CLI

Migration 0011 captures each existing process's current configuration as version 1. This is
an explicitly labeled migration baseline, not a claim that historical cases used it. Old
decisions retain null version/execution references and cannot be replayed through this
endpoint. New decisions have both references; human resolutions inherit their case's version.

`python -m app.cli load <pack> --compile` prepares artifacts. Explicit
`--activate --manager-id <id>` validates and approves the complete draft as that manager,
prints the impact report, and publishes once. `make activate MANAGER_ID=<id>` uses this path.
`make demo` no longer activates configuration implicitly; publish before running it.

There is one draft per process, no version branches, no event-sourced reconstruction and no
new worker framework. Snapshots duplicate small configuration and batch inputs intentionally.
Large populations will eventually need storage/retention work; that is outside this change.
