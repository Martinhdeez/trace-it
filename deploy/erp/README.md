# Challenge ERP on the VPS

The incident was missing `TRACE_ERP_USER` and three never-loaded workbook sources,
not an ERP outage. `scan_023.pdf` took 41.7 s: vision spent 30.8 s failing six times
with HTTP 429, including 28.8 s of retry sleeps. This bundle installs the real
challenge ERP, removes Gemini/Google keys from the active runtime environment,
selects Helmcode Qwen 3.6 and caps provider retry sleeps at 2 s per call. It does not disable
OCR, corroboration, source freshness checks, or uncertainty escalation. Network
timeouts and OCR processing are separate costs, so this is not a 2 s upload SLA.

The original pinned `alberto_erp.py` is copied without edits. Its 120 ms latency,
periodic ORA-00600, rate limiting and expiring sessions stay enabled in HTML and XML.
The adapter only binds inside the container, prefixes public links/redirects, and
keeps session tokens out of logs. Batch two is not silently loaded.

For the explicit batch-two CSV mount and cumulative reference workbook, see
[Batch 2 compatibility](../../docs/batch2-compatibility.md). The optional overlay
loads 556 entries; the base compose configuration retains the original 516.

- Public frontend: `https://gex-dashboard.hopto.org/nexia/erp/`.
- Synthetic ERP login: `alberto` / `FACTURAS2009` (challenge manual).
- Internal API: `http://erp:8009`, on the existing `trace-it_default` network.
- Only loopback port 18009 is published; ERP uses 128 MiB and 0.25 CPU.
- ERP frontend uses its own challenge login. Trace-it keeps its existing Basic Auth.

## Prepare and install

From the repository with the challenge submodule initialized:

```sh
python deploy/erp/prepare.py --output .artifacts/erp-release
scp -r .artifacts/erp-release kripta:/home/kripta/trace-it-staging/
```

The root agent must review the bundle and run the following for the observed
invoice-payment process (1), an authorized user (1), and **batch one's explicit
cut-off date, 2026-09-18**. Verify those IDs before running against another database.

```sh
cd /home/kripta/trace-it-staging/erp-release
sha256sum -c SHA256SUMS
sudo bash install.sh 1 1 2026-09-18
```

No new application image is needed: the running application already supports the
ERP connector, workbook ingestion and retry-budget environment variable. The script
serializes with CI deployment, builds an isolated ERP service, backs up runtime.env,
sets the three ERP variables plus the Helmcode chain, experimental profile and
`TRACEPAY_PROVIDER_RETRY_MAX_WAIT_S=2`, recreates
backend and frontend using their current images, loads the workbook through the API,
syncs ERP, verifies all four sources, publishes an extraction-only version with
`helmcode:qwen3.6` if Gemini is still pinned, and adds only the ERP route to Caddy. Caddy is
validated before reload. No Docker pruning, database reset, changes to the rule set or
automatic rerun of old decisions. A runtime failure restores the prior environment;
appended sources are never rolled back. Existing complete workbook sources are
preserved; partial ones cause a stop for review. A pre-existing version draft is
also preserved and stops the reader migration. Helmcode requires an existing
`HELMCODE_API_KEY`; it is never printed. Historical provider adapters and traces
remain readable; Gemini is no longer in the active chain. The experimental profile
does not claim the old Gemini benchmark applies to Helmcode.

The historical ESCALAR decision remains valid for its original missing sources.
After installation, explicitly rerun the case from the UI to obtain a new decision.
The process's published rules and extraction settings still determine the result.

## Verification and recovery

```sh
docker compose -p trace-it-erp -f /opt/trace-it/erp/compose.yml ps
curl --fail https://gex-dashboard.hopto.org/nexia/erp/
curl --config /opt/trace-it/secrets/curl.conf --fail \
  https://gex-dashboard.hopto.org/nexia/trace-it/api/processes/1/sources
```

Check all four sources have rows and ERP status `ok`. Open the ERP frontend and
check login, next-page navigation and search remain under `/nexia/erp/`. A periodic
ORA-00600 is expected; refresh to recover. Future CI application releases retain
runtime.env and the independently managed ERP service. Do not delete the shared
Docker network. To stop ERP, use its exact Compose project; restoring the runtime
backup and recreating backend/frontend restores the former integration settings.
Remove only the marked ERP block if retiring its public route.

Routing follows [Caddy handle](https://caddyserver.com/docs/caddyfile/directives/handle)
and [Docker external networks](https://docs.docker.com/reference/compose-file/networks/).
