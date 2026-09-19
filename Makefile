# trace-it: quick start. See docs/team-guide.md.
.PHONY: setup ocr-models ocr-check compile activate load-frozen demo trace-decision erp erp-sync backup export-batch check-outcomes test test-db test-e2e eval-compiler eval-norm demo-llm-down check down reset-db

LOAD = docker compose exec -T backend python -m app.cli load /processes/invoice-payment.json
DEMO_ARGS ?=

setup:
	test -f .env || cp .env.example .env
	$(MAKE) ocr-models ocr-check
	docker compose up -d --build --wait
	docker compose exec -T backend alembic upgrade head
	$(LOAD)
	@echo "Ready: API at http://localhost:$${BACKEND_PORT:-8000}/docs"

ocr-models:
	uv run --project backend --locked python -m app.features.ingestion.tools.download_models --profile v5-latin --output .models

ocr-check:
	uv run --project backend --locked --env-file .env python -m app.features.ingestion.quality

compile:  # needs LLM keys in .env
	$(LOAD) --compile

activate:  # MANAGER_ID=<id>: explicitly approve the validated pack draft
	test -n "$(MANAGER_ID)"
	$(LOAD) --activate --manager-id $(MANAGER_ID)

# MANAGER_ID=<id>: the rule set compiled from Norma_Pagos_v3 and frozen for delivery, as its
# own process (`Invoice payment - frozen 2026-09-19`), loaded and published with no LLM. The
# first load only makes sure the use case exists; its hand-written rules stay unpublished.
FROZEN = ../processes/invoice-payment/frozen/2026-09-19/invoice-payment.json
load-frozen:
	test -n "$(MANAGER_ID)"
	cd backend && uv run python -m app.cli load ../processes/invoice-payment.json
	cd backend && uv run python -m app.cli load $(FROZEN) --activate --manager-id $(MANAGER_ID)

# The whole process over the challenge corpus -> output/outcomes.jsonl. Needs `make erp`
# running in another terminal, `make setup` and downloaded OCR weights.
demo:
	test -f .env || cp .env.example .env
	test -d .context/500-sombras-de-alberto/facturas || git submodule update --init .context/500-sombras-de-alberto
	uv run --project backend --locked --env-file .env python tools/demo_run.py $(DEMO_ARGS)

# FILE=<file_id> [PROCESS=<id>]: follow one invoice through the running API, as text: state,
# decisions (author, reason, process version, rules hash), evidence, latency, errors, retries
# and pending work (tools/trace_decision.py). Uses BACKEND_PORT like `make setup`.
trace-decision:
	test -n "$(FILE)"
	python3 tools/trace_decision.py "$(FILE)" $(if $(PROCESS),--process $(PROCESS))

erp:  # ERP_PORT=<port> if 8009 is taken; start `make setup` with the same ERP_PORT
	test -f .context/500-sombras-de-alberto/alberto_erp.py || git submodule update --init .context/500-sombras-de-alberto
	cd .context/500-sombras-de-alberto && python3 alberto_erp.py --puerto $${ERP_PORT:-8009}

erp-sync:  # needs `make erp` running; writes a new erp snapshot (docs/sources-http.md)
	cd backend && uv run python -m app.cli sources sync ../processes/invoice-payment.json

# Saturday's batch 2 (docs/runbook-batch2.md). The live database runs in the compose `db`
# container; its name depends on the folder compose was started from.
DB_CONTAINER ?= trace-pay-db-1
DB_NAME ?= trace
PACK = ../processes/invoice-payment.json

backup:  # pg_dump of the live database -> backups/<db>-<time>.dump (restore: the runbook)
	mkdir -p backups
	docker exec $(DB_CONTAINER) pg_dump -U trace -Fc $(DB_NAME) > backups/$(DB_NAME)-$$(date +%Y%m%d-%H%M%S).dump
	@ls -l backups | tail -1

export-batch:  # FILES=<folder of PDFs> OUT=<file>: outcomes of those files only, then checked
	cd backend && uv run python -m app.cli export $(PACK) --files $(abspath $(FILES)) --output $(abspath $(OUT))

check-outcomes:  # OUT=<file> FILES=<folder of PDFs>: one line per file, valid results
	cd backend && uv run python -m app.cli check-outcomes $(abspath $(OUT)) --files $(abspath $(FILES))

# Tests use their own database (recreated each run), never the one `make setup` fills.
TEST_DB_URL ?= postgresql+psycopg://trace:trace@localhost:$${DB_PORT:-5432}/trace_test
PREPARE_DB = cd backend && TRACE_DATABASE_URL=$(TEST_DB_URL) uv run python -m tests.support.prepare_db
PYTEST = cd backend && TRACE_DATABASE_URL=$(TEST_DB_URL) uv run pytest -rs

test-db:
	$(PREPARE_DB) || (docker compose up db -d --wait && $(PREPARE_DB))
	cd backend && TRACE_DATABASE_URL=$(TEST_DB_URL) uv run alembic upgrade head

test: test-db  # fast unit tests
	$(PYTEST) -m "not e2e and not llm"

test-e2e: test-db  # golden outcomes of batch 1 + API flow (needs the challenge submodule)
	test -d .context/500-sombras-de-alberto/facturas || git submodule update --init .context/500-sombras-de-alberto
	$(PYTEST) -m "e2e and not llm"

eval-compiler:  # opt-in, calls real LLMs (keys in .env); writes backend/evals/reports/
	cd backend && uv run python -m evals.eval_compiler

eval-norm:  # opt-in, real LLMs: the client's norm -> rules -> code -> batch 1 vs golden
	cd backend && uv run python -u -m evals.eval_norm

demo-llm-down:  # real LLMs: the primary model's provider is unreachable, a fallback answers (ADR 0019)
	cd backend && OPENAI_BASE_URL=http://127.0.0.1:9/v1 OPENAI_API_KEY=unreachable PYDANTIC_AI_NO_BANNER=1 \
		uv run --env-file ../.env python ../tools/demo_llm_down.py

check:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd tools && uv run --project ../backend ruff check . && uv run --project ../backend ruff format --check .
	$(MAKE) test test-e2e

down:
	docker compose down

reset-db:
	@echo "WARNING: deletes the database (processes, rules, decisions, users). Then: make setup"
	docker compose down -v
