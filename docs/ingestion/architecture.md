# Integration with dev

The feature follows the [team API](../team-guide.md) and [conventions](../CONVENTIONS.md).
The feature branch is `feat/ingestion`, targeting `dev`.

Ingestion owns uploads, PDF/OCR readers, field readings and local jobs.
`features/sources/excel.py` owns workbook reading. Dev's HTTP source service remains
intact; ingestion imports the workbook reader directly. Shared evidence and normalization
live in `app/common/`.

`app.main` mounts ingestion alongside users, processes, rules, decisions, agents, LLM
configuration and sources. A lifespan manages extraction workers and the local directory lock.
The existing health and error contracts remain intact.

## Persistence and workflow

- PostgreSQL `files`: immutable bytes and extracted text, keyed by SHA-256.
- PostgreSQL `instances`: existing process/name/file identity and lifecycle.
- PostgreSQL `events`: full extraction response and uploader identity.
- SQLite/local objects: extraction cache, standalone results, batch queue and provider journals.

No schema migration is introduced. New uploads create `PENDING` instances with
`symbols=None`. Missing fields never trigger review. Re-upload preserves existing
symbols and decisions. Process retrieval reads PostgreSQL independently of the local cache.

Invoice readings do not replace configurable process symbols. The generic double-extraction
stage remains separate. No expected workbook data, audit answers or filename-specific
exceptions are supplied to production readers.

One service process per data directory; this is not a distributed queue. Provider delivery
journals prevent uncertain automatic retries. See [committee](committee.md) and
[audit](corpus-audit.md).
