# trace-it

Configurable decision processes with document evidence, compiled rules and an audit trail.
See the [team guide](docs/team-guide.md), [blueprint](docs/application-blueprint.md)
and [conventions](docs/CONVENTIONS.md).

## Run

Use `make setup` for the team's Docker setup. For local development, configure PostgreSQL
in `.env` and run from `backend/`:

```powershell
uv sync --locked --group dev
uv run alembic upgrade head
uv run python -m app.features.ingestion.tools.download_models
uv run uvicorn app.main:app --env-file ../.env --host 127.0.0.1 --port 8000 --workers 1
```

Open <http://127.0.0.1:8000/docs>. Use `POST /login` to obtain `X-User-Id`.
Native PDF and Excel reading do not require downloaded OCR weights.

The main API includes extraction and process uploads alongside the existing ERP, rules
and decisions. Extraction returns available field readings and evidence. Missing fields
do not cause an error or a document review state.

- [Ingestion guide](docs/ingestion/README.md)
- [API contract](docs/ingestion/api.md)
- [Integration](docs/ingestion/architecture.md)
- [Full corpus audit](docs/ingestion/corpus-audit.md)
- [Contributing](CONTRIBUTING.md)

The challenge submodule remains unmodified. Credentials, model weights, provider journals
and local results are excluded from Git.
