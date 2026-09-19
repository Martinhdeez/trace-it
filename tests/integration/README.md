# Frontend-backend check

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
1. Sign in as the manager.
2. The process panel shows the frozen process.
3. Upload two text PDFs on the same order and run: both end ESCALAR (`DUPLICATE_PO` in the golden).
4. Upload a scan and run: it ends ESCALAR with `MISSING_DATA`.
5. The review queue lists the three.
6. Open one, and resolve it as PAGAR as the manager.
7. The trace view shows both decisions, and the other case's reason equals `GET /instances/{id}`.

A step waiting for a frontend package is `test.fixme('pkg n')`. The PR that lands package n
turns it on.

Debug a failure: `cd tests/integration && npx playwright show-trace test-results/<test>/trace.zip`.

CI runs it on every PR into `integration` (`e2e-integration` job in `.github/workflows/ci.yml`),
with the OCR weights cached.
