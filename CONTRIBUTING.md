# Contributing

Follow the [team guide](docs/team-guide.md) and [conventions](docs/CONVENTIONS.md).
Use feature branches and pull requests into `dev`; no direct pushes to shared branches
or force-pushing published history. Use English code, documentation and Conventional
Commits. Original document text remains in its source language.

Keep routers separate from services and tests beside their feature. Preserve original
evidence. Do not reconstruct identifiers from expected source values. Document changes
to contracts, configuration and evaluation results.

From `backend/`, run `uv sync --locked --group dev`, `uv run ruff check .`,
`uv run ruff format --check .` and `uv run pytest -q`.
The full suite needs migrated PostgreSQL and the challenge submodule. Use an isolated
test database; enable ingestion database tests with `TRACEPAY_TEST_POSTGRES=1`.
On Windows, Psycopg async tests require a Selector event loop and Poppler output needs UTF-8.

For extraction checks without PostgreSQL or OCR weights:

```powershell
uv run pytest -q app/features/ingestion/tests app/features/sources/tests --ignore=app/features/sources/tests/test_erp_sync.py -m "not ocr and not integration"
```

CI checks formatting and extraction on Windows/Linux and process ingestion on PostgreSQL.
Real OCR needs weights; remote experiments may incur charges. Keep secrets and reports
out of Git. Do not reformat unrelated files.
