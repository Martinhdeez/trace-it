# Validation record — 2026-09-19

Release integration is based on `dev` ef3e079 and `main` 65bd45b (the same
application tree), with the gated VPS deployment from ci/vps-trace-it reapplied.
The old frontend/API blockers have been repaired by the application release.

## Local release evidence

- Production backend and frontend Docker images build; lint and TypeScript pass.
- Ruff, ShellCheck and actionlint pass.
- All three production containers become healthy on an isolated database after
  migrations 0001–0014. First-release use-case/user initialization succeeds.
- `make check` on Linux/Python 3.12: 601 unit/integration tests and 11 golden/API/
  evaluation tests pass. Two existing model-dependent OCR tests are skipped by
  keyless CI; one golden mismatch case is empty. No release failure is suppressed.
- All 471 text invoices match the golden reference; this is not a certification
  of all 29 scanned challenge invoices.
- Five Chromium tests pass: gateway authentication; assets/deep links under the
  deployment prefix; real process/user rendering and configuration screens;
  no mock fallback during API failure; published schema, PDF upload, persisted
  symbols/evidence, automatic decision, append-only human resolution and export.
- A PostgreSQL dump restores a sentinel row into a separate database.
- The production OCR profile validates the local model hashes and configured keys.
  A synthetic scan is correctly read by both local OCR models. A separate explicit
  paid smoke check calls real visual providers, verifies NIF/IBAN/order, and reports
  no extraction warnings. It records three provider attempts and two visual readers.
  The text judge is unnecessary when image readers agree, so this check does not
  certify its live availability. Paid calls remain enabled in production.

## Deployment prerequisites

- Source `.env` was copied by SCP, with matching SHA-256 and mode 600; no secret
  value is committed or printed. Provider keys stay server-side.
- Root installed the restricted SSH command/sudoers. The operator confirmed the
  release preparation script installed checked OCR weights and first-release
  initialization, and enabled `/opt/trace-it/DEPLOY_ENABLED`.
- The GitHub deploy switch remains off until CI is green. Repository SSH secrets
  use a dedicated restricted key and the host key pinned over trusted SSH.
- The workflow creates its environment on first deployment. Administrator-enforced
  environment/branch protection is additional hardening; current account is WRITE.
- Only loopback port 18173 is reserved. Existing Caddy routes, mail and containers
  remain outside this Compose project. Available disk at inspection: about 12 GiB.
- First release loads the invoice-payment use case and users, with rules as drafts.
  Managers explicitly validate/publish rules. No production invoice is auto-decided.

## Limits and operations

The challenge ERP is not provisioned in this stack; configure a reachable
`TRACE_ERP_URL` before live ERP synchronization. Provider availability can change.
Backups are local until an operator provisions offsite retention. See README.md
for disable/rollback commands. GitHub run and deployment evidence should be checked
on the actual release commit rather than inferred from these local results.
