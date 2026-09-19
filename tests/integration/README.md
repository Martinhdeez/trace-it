# Integration tests

Two Playwright suites against the real API and console: the demo path
(`make e2e-integration`, `playwright.config.ts`) and mail ingestion (`make e2e-mail`, `mail.config.ts`).

## Demo path

The demo path, walked through the real console against the real API in Chromium
(`docs/backend-plan.md`, B0). It is the done check for every backend item and every frontend
package in `docs/frontend-handoff.md`.

```bash
make e2e-integration
```

What it does:
- Recreates `trace_e2e_test` on the Docker Postgres (`E2E_DB_URL` overrides it), migrates, and
  publishes the frozen pack with no LLM (`load-frozen` with manager 1, `martin@trace-it.local`).
- Downloads the OCR weights once (`make ocr-models`, 98 MB) and installs Chromium for Playwright.
- `playwright.config.ts` starts the challenge ERP, the API and the console (`npm run dev`) on
  three free ports, with the mock off, and stops them when the run ends.
- No LLM key: every model call fails before it is made, as 502 `llm_error`. The
  assistant's proposal is not part of the path (D4). The OCR runs locally.

The path (`demo-path.spec.ts`), with a MOCK DATA badge and an `ErrorNotice` failing every step:
0. Before any step, as `make demo` does: load the client's workbook with `cut_off_date` 2026-09-18 and sync the ERP. A source a rule reads but that was never loaded would escalate `SOURCE_UNAVAILABLE` (B11).
1. Sign in as the manager.
2. The process panel shows the frozen process.
3. Upload two text PDFs on the same order and run: both end ESCALAR with "Same order as: <the other>" (`DUPLICATE_PO` in the golden).
4. Upload a scan and run: it ends ESCALAR with `MISSING_DATA`.
5. The review queue lists the three.
6. Open one, and resolve it as PAGAR as the manager.
7. The trace view shows both decisions, and the other case's reason equals `GET /instances/{id}`.

A step waiting for a frontend package is `test.fixme('pkg n')`. The PR that lands package n
turns it on.

Debug a failure: `cd tests/integration && npx playwright show-trace test-results/<test>/trace.zip`.

CI runs it on every PR into `dev` and every push to `dev` and `main` (`e2e-integration` job in
`.github/workflows/ci.yml`), with the OCR weights cached. The deploy needs it green.

A console change that moves or rewords what a step reads updates that step in the same PR, and
the PR is not merged while this job is red. A step is fixed in `dev` only, never in a PR into
`main`: two fixes on two branches conflict when `main` is merged back.

## Mail ingestion

Run `make e2e-mail` with local PostgreSQL available. Install backend and frontend
dependencies first (`uv sync --locked` and `npm ci` in their respective folders).
The target prepares only `trace_mail_browser_test`, applies migrations and starts
Playwright with `mail.config.ts`.

The test assigns the supported gathering email in process settings, starts a worker
against a loopback TLS IMAP fixture, delivers synthetic PDF attachments, and verifies
automatic PAGAR / NO_PAGAR / ESCALAR decisions and provenance in the browser. It does
not press Run, mock API responses, contact production mail or consume real providers.

Use `MAIL_TEST_DB_URL` to override the isolated test database URL. All mailbox secrets,
certificates and documents are generated for the test. See `docs/mail-ingestion.md`
for protocol, recovery tests and the separate future operator runbook.
