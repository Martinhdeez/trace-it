# Validation record — 2026-09-19

Candidate prepared against local `main`, commit
`710d4212b2c7477857dca3aca094d8040bea6ce4` (latest `origin/main` at the initial fetch).
This record covers the candidate published on `ci/vps-trace-it`, before integration
with subsequent changes to `main`. It has not been merged into the release branch.
No production image has been published and no VPS deployment has been activated.

## Verified

- Production backend and frontend Docker images build successfully.
- Frontend TypeScript/build and lint pass (four existing lint warnings).
- Ruff passes; shell scripts pass ShellCheck; workflow passes actionlint.
- Production Compose starts an isolated local PostgreSQL, API and nginx gateway;
  all three health checks pass. Only the CI gateway binds `127.0.0.1:18174`.
- Real PostgreSQL dump/restore recovers a sentinel row into an isolated database.
- `make check` executed in Linux/Python 3.12 against an isolated test database:
  292 unit/integration tests passed; 7 golden/API/evaluation tests passed;
  3 new frontend-contract tests failed. Two OCR tests need weights; one existing
  parameterized test is skipped because there is no known golden mismatch.
- All 471 text invoice outcomes match the golden reference. The corpus contains
  500 invoices; this does not certify extraction/decisions for the 29 scans.
- Chromium: 3 passing tests (access protection; assets/deep links; no mock fallback),
  2 failing tests (real process cannot render; PDF does not reach the engine).
  Despite the latter soft assertion, persisted PDF evidence, human resolution,
  append-only history and JSONL export assertions complete successfully.
- Existing Windows checkout JSONL files were normalized to LF and `*.jsonl` now
  has an explicit LF rule. The golden regeneration check passes under Linux.

## Release blockers, intentionally not fixed in this change

1. The live client calls 29 route/method combinations absent from OpenAPI.
2. It sends `X-Usuario-Id` instead of `X-User-Id`.
3. It assumes `nombre`/`rol` while the API returns `name`/`role`.
4. PDF ingestion persists evidence with unapproved symbols; `/run` leaves the
   instance pending. Add a real approved-symbol handoff, not a test-only bypass.

No failing check uses `xfail`, `continue-on-error` or retries to permit deployment.

## VPS and GitHub state

- SSH as `kripta` works. Existing `github-kripta` identity authenticates as
  `Kripta-Studios`; neither its private key nor other services' credentials were copied.
- `kripta` cannot access the Docker socket; `sudo -n` requires a password.
- Caddy owns HTTPS. The Hub at `/nexia/` and its applications already exist.
  Port 18173 was free. Host had 7.6 GiB RAM and about 12 GiB free disk at inspection.
- Source `.env` copied by SCP to
  `/home/kripta/trace-it-staging/secrets/runtime.env`, mode 600, matching SHA256.
  Secret values were not printed or added to the repository.
- Root bootstrap bundle is in `/home/kripta/trace-it-staging/bootstrap`, with
  `SHA256SUMS`. It prepares trace-it only and leaves both activation switches off.
- Caddy candidate adapts successfully. Comparison finds exactly two added trace-it
  routes and preserves existing handler content after normalizing generated group
  IDs, configuration hide paths and route ordering. This is configuration inspection,
  not a live routing test; the original Caddyfile was not changed or reloaded.
- GitHub repository secrets `TRACE_SSH_KEY` and `TRACE_SSH_KNOWN_HOSTS` are set.
  The former is a new dedicated identity for the forced deployment command; the
  latter is pinned from the host key read over the existing trusted SSH connection.
- Repository variable `TRACE_DEPLOY_ENABLED=false`.
- Creating environment `trace-it-production` returned HTTP 403: repository admin
  rights are required. Current account has `WRITE`, not `ADMIN`. A VPS root shell
  alone cannot grant GitHub permissions. Exact admin commands are in `README.md`.

The deployment script's privileged execution and public HTTPS activation remain
untested until a root operator installs the bundle and the application gates pass.
Local OCR weights, live ERP connectivity, real provider evaluations and offsite
backup storage remain explicit deployment prerequisites/operational work.
