# Versioned challenge ERP and automatic delivery

Production UI: <https://gex-dashboard.hopto.org/nexia/erp/>. Trace-it connects to
`http://erp:8009` on `trace-it_default`. Synthetic challenge login:
`alberto` / `FACTURAS2009`.

## One evolving ledger, explicit scenarios

The challenge describes one ERP receiving incremental data, not independent
companies whose ledgers should be concatenated. The upstream loader merges CSV
rows by `asiento_id`: existing entries change, new entries append. Preserve that
behavior, including the original latency, ORA-00600, rate limit and session expiry.

`releases/initial/` preserves the original 516-entry ERP. `releases/lote2/` contains
an exact byte copy of the ERP and CSV running on the VPS on September 19: 556
entries (40 additions). The deployed Python file differs from upstream only in
line endings. Each manifest records upstream provenance, file hashes, expected
row count and **ordered** incremental CSVs. The wrapper does not change the
upstream ledger implementation.

`active.json` selects `lote2`. Every catalog scenario is built and probed in CI;
only the selected scenario is published/deployed. Retained scenarios and immutable
images are available for reproduction, without placing several containers behind
the same `erp` DNS alias. The original 500 invoices and new 40 invoices do not mean
there must be exactly 500/540 ERP entries.

## Add or activate a release

1. Create `releases/<new-id>/` on a branch from `dev`. Copy the intended upstream
   `alberto_erp.py` and all incremental CSVs needed by that scenario. Never edit a
   retained scenario to represent a different historical ledger.
2. Add `release.json`, following the existing manifests: unique `id`, upstream
   repository/revision, `updates` in application order, `expected_rows`, and
   `sha256` for the Python source and each CSV. Use `sha256sum` on the exact bytes.
   With a cumulative CSV, include it once; with deltas, include each once in order.
3. Set `active.json` to `{"release": "<new-id>"}` to request promotion. Merely adding
   a directory tests and retains that scenario; it does not make it active.
4. Run `uv run --project backend pytest deploy/erp -q` and
   `bash deploy/erp/ci.sh`. Open a PR into `dev`, then promote the reviewed change
   to `main`. Do not pull upstream at container startup or use floating ERP tags.

Build one scenario locally without changing production:

```sh
python3 deploy/erp/release.py --release lote2 --output /tmp/erp-lote2-build
# The output directory must not already exist.
docker build --build-arg REVISION="$(git rev-parse HEAD)" \
  -t trace-it-erp:local /tmp/erp-lote2-build
# Isolated reproduction: no production alias, no published port.
docker run --rm --network none trace-it-erp:local
```

If two independent ERPs really need to run simultaneously, give each a separate
Compose project, network alias and public route, and configure each process's
connector explicitly. Do not give both the production alias `erp`, merge their
responses, or switch between them randomly. This delivery intentionally keeps one
active ledger for the invoice-payment process.

## CI/CD and first-time server adoption

The main CI workflow tests backend, mail, browser integration, application stack
and all ERP scenarios. The ERP job publishes the **tested active image** to
`ghcr.io/martinhdeez/trace-it/erp` only on `main`. After all gates pass, the deploy
job sends the immutable digest through the existing restricted SSH identity.
The same `TRACE_DEPLOY_ENABLED` repository variable and VPS marker govern delivery.

The application deploys first, followed by the ERP. Each has its own rollback;
if ERP delivery fails, the application remains at its successful release and the
ERP returns to its previous image. This is not a cross-service atomic release.
The `deploy-erp` receiver accepts only a revision, digest and actor, never shell
commands, build paths or arbitrary registry names. ERP deployment shares the
application lock, checks image revision, probes an isolated candidate, switches
only `trace-it-erp`, checks real login/XML/HTML and verifies public release metadata.
It retains image and manifest records in `/opt/trace-it/erp/releases/`.

For an existing installation, review and run once as root:

```sh
bash deploy/erp/install-cd.sh
```

This adopts the running image as the rollback baseline and installs the receiver,
ERP deployment script, release Compose file and scoped sudo permission. It does
not restart services, edit Caddy or change the active ERP. Future script/protocol
or Compose changes need another reviewed root installation; application images
cannot rewrite the root-owned deployment controls.

The `prepare.py` / `install.sh` bundle remains first-install tooling for the
workbook/provider bootstrap. Its explicit `compose.update.yml` overlay and
`TRACE_ERP_UPDATE` CSV option remain available for manual installations; see
[Batch 2 compatibility](../../docs/batch2-compatibility.md) for the cumulative
reference workbook and input review. Versioned CD images reject external CSV
overrides: their ordered updates must be declared in `release.json`, so the
running ledger matches its release evidence. Do not run the bootstrap installer
to update an existing production ledger.

## Evidence, impact and reprocessing

Deployment changes the ERP service, not historical Trace-it sources, rules or
outcomes. `GET /nexia/erp/healthz` reports the release manifest and actual row count;
legacy endpoints keep the original challenge faults. The compatibility health
check in Compose uses `/erp/estado` so the adopted legacy image can roll back.

After promotion, synchronize the process's `erp` source in Trace-it (or let its
configured `sync_before_run` do so). A complete successful fetch creates a new
snapshot; failures keep history and mark the attempted source unavailable. Use
`GET /api/processes/{id}/sources/erp/diff` to compare against the previous snapshot.
Changes to existing entries identify decisions requiring impact review; additions
may also change absence/duplicate rules, so review those dependencies as well.
Reprocess affected cases explicitly to append new decisions, preserving their
original snapshot/rule evidence. Do not replace old outcomes silently.

Supplier and order CSVs and new business rules are separate reference inputs;
deploying an ERP does not import them or publish rules. Import/review those changes
through the corresponding source and rule flows before validating both invoice
lots. The two delivery JSONL files still require one accepted outcome per PDF;
this pipeline does not certify the private functional reference.

## Operations and recovery

```sh
cd /opt/trace-it
# Inspect only the ERP service:
docker compose --env-file erp/current.env -p trace-it-erp \
  -f erp/compose.release.yml ps
curl --fail https://gex-dashboard.hopto.org/nexia/erp/healthz
```

To roll back manually, acquire `/run/lock/trace-it-deploy.lock`, retain a copy of
`erp/current.env`, start the image from `erp/previous.env` with this exact Compose
project, verify its legacy API, then copy that env file to `erp/current.env`.
The first adopted image predates `/healthz`; probe `/erp/estado` for that baseline.
Never remove the shared network or restore the application database as part of an
ERP image rollback. In-memory ERP sessions reset on restart; ledger data is
reconstructed deterministically from the image. Database snapshots remain stored.
