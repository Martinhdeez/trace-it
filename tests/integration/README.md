# Mail ingestion integration

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
