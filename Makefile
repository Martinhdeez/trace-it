# trace-it: quick start. See docs/guia-equipo.md.
.PHONY: setup compile erp test down reset-db

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

test:
	docker compose up db -d --wait
	cd backend && uv run alembic upgrade head && uv run pytest

down:
	docker compose down

reset-db:
	@echo "WARNING: deletes the database (processes, rules, decisions, users). Then: make setup"
	docker compose down -v
