# trace-it deployment

Target: **https://gex-dashboard.hopto.org/nexia/trace-it/**.

For the challenge ERP frontend at `/nexia/erp/`, versioned scenarios and automatic
delivery, see [ERP releases and CI/CD](erp/README.md).

## Release policy

`main` is the deployment source. PRs to `dev`/`main`, pushes to both branches and
manual runs execute the CI workflow. Only a successful run on `main` may deploy.
Deployment requires backend, mail, end-to-end integration, the production stack
with Chromium, and all versioned ERP scenarios to pass.

The release includes the frontend/API adapters and versioned extraction contract
from the September 19 application release. Contract tests audit the actual wire
types and routes; browser tests verify user mapping, real database content and the
published extraction-to-decision flow. Missing integrations block deployment.

The CI build sets the Vite public base, React Router basename and API URL together.
Production uses `live` mode. The default development workflow is unchanged.

## Pipeline

1. Backend: locked Python dependencies, Ruff, unit tests, golden decisions and API
   tests (`make check`), plus the frontend route/header/schema contract audit.
2. Frontend: locked Node dependencies, lint, TypeScript and production build.
3. Containers: production Dockerfiles, an isolated Compose project `trace-it-ci`,
   an empty PostgreSQL volume and real migrations. A dump/restore round trip checks
   a sentinel row in a separate database. No developer/production keys.
4. Chromium: credential-free console access, Bearer boundaries, assets, deep links,
   real database content rendered in the console, no silent mocks, and real HTTP PDF upload/evidence/decision/human
   resolution/export. Existing golden tests check decision correctness separately.
5. On successful `main`, push the exact tested images to GHCR. Deploy by immutable
   digest and verify their revision labels. A failed backend job also blocks CD.
6. A restricted SSH key invokes one root-owned deployment script. The job token is
   sent on stdin for temporary registry login, then removed. Existing VPS GitHub
   keys are not exported or changed. No self-hosted runner executes PR code on the VPS.
7. Compare component input hashes with the images currently deployed. Keep unchanged
   services on their existing digests. For a backend change, stop only the writers,
   verify the database/ingestion backup, migrate and start with health checks.
   Keep the frontend serving requests and resume any previously active mail worker.
   Check HTTPS and record the selected digests, including retained older images.

This is a short maintenance deployment, not zero downtime. With the existing
single-process ingestion lock and 7.6 GiB VPS, running two competing workers against
one ingestion directory would be unsafe. Failed releases restart the previous
images; **database restore/downgrade is never automatic**. All migrations must be
backward compatible with the preceding release, otherwise use an explicit
maintenance/restore procedure. Backups are retained locally and count against disk;
the deployment refuses to proceed below 6 GiB free. No global Docker prune is used.

## VPS isolation

- New Compose project: `trace-it`; new database and ingestion volumes.
- Only `127.0.0.1:18173` is published. PostgreSQL and backend publish no host ports.
- No changes to firewall, mail, existing containers, Hub or other domain routes.
- Limits: API 2 GiB/1 CPU, DB 512 MiB/0.5 CPU, gateway 128 MiB/0.25 CPU;
  three bounded extraction workers, one OCR thread and one concurrent compiler.
  Existing installations must update their installed Compose configuration to
  adopt the worker default; image replacement alone does not change it. See
  [API OCR performance and verification](../docs/ingestion/performance.md).
- API/frontend run without privileges; root filesystem is read-only; logs rotate.
- Provider keys are in `/opt/trace-it/secrets/runtime.env`, never in GHCR, Git or
  frontend `VITE_*` variables. The source `.env` is transferred by SCP, mode 600.
- The operator has made this demo public: the console and its business API do not
  require HTTP Basic credentials. The console selects the seeded manager automatically.
  Email/header identity is attribution, not secure authentication. Database administration
  still requires the API Bearer token, and mail ingestion requires its mailbox token.
- OCR weights are installed under `/opt/trace-it/models`, with verified hashes.
  Production keeps the verified OCR profile and can call paid providers. CI uses
  the explicit experimental profile with native PDFs and no provider keys.
  `smoke-providers.py` makes real paid calls on one synthetic scan; never run it
  automatically on every commit. The challenge ERP is managed by its own versioned
  release image and CD script; its connector uses `http://erp:8009`.
- Real provider evaluations remain explicit opt-in; deterministic CI uses scripted
  models and never incurs provider charges. CI passing does not certify external
  provider availability or the accuracy of every scanned document.

## Commands for the root agent

The prepared bundle and `.env` are under `/home/kripta/trace-it-staging`. First
review `bootstrap/install.sh`, `bootstrap/deploy.sh`, `bootstrap/receive.sh`,
`bootstrap/compose.yml` and `bootstrap/activate-route.py`; their SHA256 hashes are
listed in `bootstrap/SHA256SUMS`.

```bash
cd /home/kripta/trace-it-staging/bootstrap
sha256sum -c SHA256SUMS
sudo bash /home/kripta/trace-it-staging/bootstrap/install.sh
```

This installs only trace-it's files, its restricted CI public key and one sudoers
entry. It does **not** start containers, reload Caddy or enable deployments. Do not
add `kripta` to the Docker group or grant unrestricted passwordless sudo.

Once the integration has been repaired, all CI jobs pass on `main`, and the
operator has checked disk/model/ERP requirements:

```bash
sudo touch /opt/trace-it/DEPLOY_ENABLED
```

Then enable repository variable `TRACE_DEPLOY_ENABLED=true` and run CI on `main`.
Until then leave both switches off. The first successful release validates the
candidate Caddyfile before a graceful reload. Existing `/nexia/*` routes remain.

GitHub configuration (a repository administrator must enforce the branch policy):

- Environment `trace-it-production`, deployment branch restricted to `main`.
- Secrets `TRACE_SSH_KEY`, `TRACE_SSH_KNOWN_HOSTS` (a dedicated key and pinned host key).
- Required PR checks: `backend`, `production-stack`; keep existing ingestion checks.
- Variable `TRACE_DEPLOY_ENABLED`, initially `false`.
- GHCR packages inherit access from `Martinhdeez/trace-it`. If package access has
  been detached, grant that repository Actions access before enabling deployment.

The workflow creates `trace-it-production` automatically on first deployment if
absent. This permits release with repository WRITE access; it does not create
protection rules. The workflow restricts deployment to successful `main` runs and
checks the revision is still current. A repository administrator can additionally
enforce the environment branch policy with:

```bash
gh api --method PUT repos/Martinhdeez/trace-it/environments/trace-it-production --input admin-environment.json
gh api --method POST repos/Martinhdeez/trace-it/environments/trace-it-production/deployment-branch-policies --input admin-main-policy.json
```

If the environment already exists, inspect its rules first and preserve existing
reviewer requirements and restrictions before changing it. Add
the required CI checks to the existing main branch rules without replacing unrelated
branch protection. Repository-level SSH secrets are already prepared; move them to
the restricted environment when the administrator configures its protection rules.

For the already installed September 19 bootstrap, `prepare-release.sh` installs
staged OCR weights, updates the deploy script with first-release seeding and enables
the VPS marker. It refuses existing releases, unexpected script hashes or trace-it
containers. Review the staged bundle/checksums before running it as root. It starts
no service and leaves Caddy unchanged.

## Local verification

Run in Bash from the repository root with Docker, Node 24 and uv installed:

```bash
git submodule update --init --recursive
make check
docker build -f deploy/backend.Dockerfile -t trace-it-backend:ci .
docker build -f deploy/frontend.Dockerfile -t trace-it-frontend:ci .
bash deploy/ci-stack.sh up
bash deploy/ci-stack.sh backup-check
cd frontend
npm ci
npx playwright install chromium
npx playwright test
cd ..
bash deploy/ci-stack.sh down
```

`ci-stack.sh` deletes volumes only for the hardcoded disposable `trace-it-ci`
project. Playwright refuses non-local targets, so it cannot write test invoices to
the public VPS. Reports and traces are uploaded even when a gate fails.

## Operations and recovery

Bearer access and the restricted `trace_app` runtime role are documented in the
[production API guide](../docs/production-api.md). Set `TRACE_API_TOKEN` only in the private
runtime environment; set `TRACE_DATABASE_USER` and `TRACE_DATABASE_PASSWORD` in the private
Compose environment after provisioning the role. The deploy script uses the owner only
for one-off migrations and grant refreshes. The console, business API and API documentation
are public; `/db` always requires Bearer.

Disable future deployment: set `TRACE_DEPLOY_ENABLED=false` and remove
`/opt/trace-it/DEPLOY_ENABLED` as root. This does not stop the running app.

Inspect only this stack (root shell):

```bash
cd /opt/trace-it
set -a
. ./current.env
set +a
docker compose --env-file secrets/compose.env -p trace-it -f compose.yml ps
docker compose --env-file secrets/compose.env -p trace-it -f compose.yml logs --tail=100
```

For code rollback, use the same commands after sourcing `previous.env`, then
`docker compose --env-file secrets/compose.env -p trace-it -f compose.yml up -d --wait`.
Review migration compatibility first. Restore data only into an isolated recovery
database and verify it before any production replacement; a restore can discard
decisions made since the backup. Copy backups off the VPS before treating them as
disaster recovery. Monitor disk, backup age, container health and public HTTPS.

Configuration files/scripts are root-owned. Changes to the deployment protocol or
Compose file need a reviewed root installation; application releases only change
image digests. Never overwrite Caddy with a stale full configuration copy.

References: [Vite public base](https://vite.dev/guide/build#public-base-path),
[Compose readiness](https://docs.docker.com/compose/how-tos/startup-order/),
[GitHub registry authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry),
[Caddy handle](https://caddyserver.com/docs/caddyfile/directives/handle),
[Playwright API tests](https://playwright.dev/docs/api-testing).


## Explicit demo reset, independent of application deployment

Normal deployments preserve the demo data. The old `DEMO_RESET_ENABLED` marker is ignored.
An operator can explicitly request a backed-up refresh, using the currently deployed images:

```bash
sudo /usr/local/sbin/trace-it-deploy --reset-demo
```

This is a local root command; the restricted CI SSH receiver cannot request it. It verifies
the fixture/cache before stopping writers, then backs up, resets and runs the seed, restarts
the backend and resumes any previously active mail worker. It keeps the frontend running
and leaves the selected release unchanged. It never runs automatically from CI.

The version-4 private `/opt/trace-it/demo-seed.json` contains all 500 PDFs from
`facturas/`, all 40 from `facturas_primin/`, their original bytes and SHA256 values,
accepted application symbols, extraction evidence and the cached extraction trace trees.
It is built from the pinned original `ikurotime/500-sombras-de-alberto` checkout and
saved application readings, never from hand-reviewed delivery outcomes. It also contains
41 of the 44 hiring CVs. `cv-002.pdf`, `cv-021.pdf` and `cv-024.pdf` stay out of the seed as
one live `INTERVIEW`, `REJECT` and `REVIEW` upload.

The seed run report includes `metrics.planes` read from the same audit breakdown as the
console, across all history. Restored OCR traces retain their original dates, durations,
tokens and price snapshots. `imported_spans` identifies these historical measurements;
restoring them does not incur the cost again. Engine timings come from the new execution.
No compilation calls or missing tariffs are fabricated. A process with no recorded agent
activity should show no recorded activity, rather than a fictional compilation bill.

Both invoice batches belong to `Invoice payment`. The seed first runs the 500 invoices with
v1 and the original 516-entry ERP. It then appends the updated suppliers, orders, ERP and
cut-off snapshots, records v2 with the same rules, runs the 40 new invoices, and reprocesses
the first 500. Automatic live ERP synchronization is disabled in these demo versions so a
later decision cannot silently replace the pinned scenario. Manual source changes remain
possible for a demo, and the next explicit reset restores the same history.
Hiring follows the same pattern: an explicit reset restores the 23-row criminal-records snapshot
without contacting the service. Normal runs still use the published connector. An exact,
case-insensitive full-name match rejects the candidate; `cv-001.pdf` (Ana Molina) is the
fixture's checked match for `CR-00001`.

Explicit reset stops application and mail writers, validates a database dump and ingestion
archive, checks the extraction-cache identity, and transactionally restores the complete
fixture. Instance IDs remain monotonic. Deleting the previous population before restoring
it prevents repeated resets from creating duplicate documents. Real duplicate orders
within the original documents still escalate normally. Users and mailbox UID cursors are
preserved; no old email is replayed.

`run-seed.py` captures each process population and pinned sources, evaluates the published
rules with the application's deterministic engine, and appends normal decisions, findings,
execution and rule traces. It does not invoke source synchronization, OCR, compilers or the
optional LLM reviewer. Every restored case ends decided, including legitimate escalations.
The original extraction trees retain their timestamps and are explicitly marked
`cached_replay`, with `source_trace_id` and zero provider calls in this reset. They are
historical evidence, not newly billed calls. Engine decisions are recomputed; human-reviewed
JSONL labels are never injected into the engine.

The seed caches the code/dependency fingerprint, extraction settings and symbol schemas.
Unrelated frontend or business-rule changes do not invalidate extraction. Changes to the
extraction implementation, models, schema or locked dependencies stop the reset before
reset, with a message to refresh the seed once. The initial single-reader-to-two-reader
upgrade explicitly records its previous settings in `adopt_from`; the fixture then pins
the settings used for its readings. Unexpected configurations are rejected. A partial OCR
reading stays partial with its warnings and unverified fields; restoring it never promotes
proposed values to accepted facts.

Build a replacement only after processing the original PDF bytes with the intended OCR
version and exporting the resulting application readings and trace trees:

```sh
python deploy/build-challenge-seed.py \
  --challenge .context/500-sombras-de-alberto \
  --base-seed /private/previous-demo-seed.json \
  --readings /private/application-readings.json \
  --cache /private/ocr-cache-identity.json \
  --output /private/new-demo-seed.json

python deploy/build-hiring-seed.py \
  --pack processes/hiring-screening \
  --base-seed /private/new-demo-seed.json \
  --readings /private/application-readings.json \
  --output /private/complete-demo-seed.json
```

The builder checks every PDF hash against its saved reading and requires the exact 500/40
populations. It reads workbook/CSV source data and the ERP's embedded export from the
original repository. It does not call any API. Keep the fixture and all extraction artifacts
outside Git; they are installation data, not code.

Install `reset-demo.py`, `run-seed.py` and `seed_cache.py` under `/opt/trace-it`, the fixture
as root:10001 mode 0640, and `deploy.sh` as `/usr/local/sbin/trace-it-deploy`. Install the
matching Compose worker configuration too: image updates alone do not change the installed
worker count. Version-3 six-example fixtures remain supported for other installations.
A failed reset rolls back SQL and quarantined files. A failed deployment restarts the
previous images; it never automatically restores the database. The previous fixture,
configuration and database backup remain available for explicit recovery.

Validation covers missing/duplicate/corrupt PDFs, wrong ERP populations, OCR identity
changes, deployment ordering and backup/cache/reset/replay failures. The full private
fixture is additionally restored twice against an isolated production database copy with
HTTP clients blocked: identical document counts and results, no duplicate rows, zero
provider calls, preserved extraction traces, and a separate ERP per batch. Each explicit reset
records `demo-cache-check.json`, `demo-reset.json` and `demo-seed-run.json` in its backup.

## Component deployment upgrade

CD waits for `backend`, `e2e-integration`, `production-stack` and `erp` to pass.
All components are built and tested together; the VPS replaces only components whose
`org.trace-it.source-hash` differs from the installed image. Criminal records has its own
hash and pinned image. A frontend-only release does not stop backend, mail, database or ERP,
and does not back up/reset/migrate the database. Unrelated documentation changes retain all
running services. A missing old hash causes one initial replacement.

Input hashes cover tracked files copied by the production Dockerfiles and their configuration.
To deliberately refresh an upstream base image, update/pin its `FROM` reference so that the
component hash changes too. Retained images keep their own revision labels; release records
list the actual immutable digests selected for each service.

Before stopping writers, the receiver pulls and verifies candidate images, validates Compose,
checks migration discovery, checks nginx configuration and validates an active mail worker.
Backups remain inside the write pause to keep the database and ingestion archive consistent.
The gateway serves assets and structured 503 responses with `Retry-After` while the backend
is unavailable. Docker DNS refresh handles backend replacement without a gateway restart.
No Caddy change is required. Code rollback restores only touched services and resumes mail;
it never restores the database automatically.

For an existing initialized VPS, install the reviewed `deploy/deploy.sh` and
`deploy/erp/deploy.sh` as the existing root-owned receivers. Update `/opt/trace-it/compose.yml`
with the new criminal-records image selection while preserving installation-specific settings.
Do this under `/run/lock/trace-it-deploy.lock`, between releases, never over an active deploy.
Deploy the new labeled images through CI. The first upgrade also replaces the gateway to
support backend replacement without a restart. This receiver requires an initialized
installation and existing routes; it does not bootstrap Caddy.

Validation: `pytest deploy` exercises component selection, preflight failures, rollback/mail
recovery and explicit reset. `deploy/ci-stack.sh maintenance-check` stops and recreates only
the disposable CI backend, checking the console/503 response, API recovery and unchanged
frontend container ID. Never run that destructive test against production.
