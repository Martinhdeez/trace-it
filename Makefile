# trace-it: arranque rápido. Ver docs/guia-equipo.md.
.PHONY: setup compilar erp test down reset-db

CARGAR = docker compose exec -T backend python -m app.cli cargar /procesos/pago-facturas.json

setup:
	test -f .env || cp .env.example .env
	docker compose up -d --build --wait
	docker compose exec -T backend alembic upgrade head
	$(CARGAR)
	@echo "Listo: API en http://localhost:$${BACKEND_PORT:-8000}/docs"

compilar:  # needs LLM keys in .env
	$(CARGAR) --compilar

erp:
	test -f .context/500-sombras-de-alberto/alberto_erp.py || git submodule update --init .context/500-sombras-de-alberto
	cd .context/500-sombras-de-alberto && python3 alberto_erp.py

test:
	docker compose up db -d --wait
	cd backend && uv run alembic upgrade head && uv run pytest

down:
	docker compose down

reset-db:
	@echo "AVISO: borra la base de datos (procesos, reglas, decisiones, usuarios). Luego: make setup"
	docker compose down -v
