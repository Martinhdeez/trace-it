# trace-it: quick start. See docs/team-guide.md.
.PHONY: setup compile erp erp-sync test test-db test-e2e eval-compiler check down reset-db

LOAD = docker compose exec -T backend python -m app.cli load /processes/invoice-payment.json

setup:
	test -f .env || cp .env.example .env
	docker compose up -d --build --wait
	docker compose exec -T backend alembic upgrade head
	$(LOAD)
	@echo "Ready: API at http://localhost:$${BACKEND_PORT:-8000}/docs"

compile:  # needs LLM keys in .env
	$(LOAD) --compile

erp:
	test -f .context/500-sombras-de-alberto/alberto_erp.py || git submodule update --init .context/500-sombras-de-alberto
	cd .context/500-sombras-de-alberto && python3 alberto_erp.py

erp-sync:  # needs `make erp` running; writes a new erp snapshot (docs/sources-http.md)
	cd backend && uv run python -m app.cli sources sync ../processes/invoice-payment.json


# Tests use their own database (recreated each run), never the one `make setup` fills.
TEST_DB_URL ?= postgresql+psycopg://trace:trace@localhost:5432/trace_test
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

check:
	cd backend && uv run ruff check . && uv run ruff format --check .
	$(MAKE) test test-e2e

down:
	docker compose down

reset-db:
	@echo "WARNING: deletes the database (processes, rules, decisions, users). Then: make setup"
	docker compose down -v
