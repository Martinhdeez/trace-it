# Integration with dev

The feature follows the [team API](../team-guide.md) and [conventions](../CONVENTIONS.md).
The integration targets the current `dev` use-case, process and event contracts.

Ingestion owns uploads, PDF/OCR readers, field readings and local jobs.
`features/sources/excel.py` owns workbook reading. Dev's HTTP source service remains
intact; ingestion imports the workbook reader directly. Shared evidence and normalization
live in `app/common/`.

`app.main` mounts ingestion alongside users, processes, rules, decisions, agents,
use cases with versioned agent configuration, and sources. A lifespan manages extraction
workers and the local directory lock.
The existing health and error contracts remain intact.

## Persistence and workflow

- PostgreSQL `files`: immutable bytes and extracted text, keyed by SHA-256.
- PostgreSQL `instances`: existing process/name/file identity and lifecycle.
- PostgreSQL `events`: full extraction response and uploader identity.
- SQLite/local objects: extraction cache, standalone results, batch queue and provider journals.

No schema migration is introduced. New uploads create `PENDING` instances. Processes
declaring the invoice-payment symbol schema receive stored document values and provenance;
generic processes keep `symbols=None`. Uncertain identifiers remain null so the process's
rules determine escalation. Re-upload preserves existing symbols and decisions.
Explicit re-extraction updates only pending instances, under the same row lock used by
the decision run. Process retrieval reads PostgreSQL independently of the local cache.

`process_extraction.py` connects the reader to declared symbols and the latest source
snapshots. `sources/workbook.py` loads supplier/order snapshots from the existing Excel
reader. The existing ERP connector, pure decision engine, sandbox and export endpoint
complete the flow. No production imports come from `tools/`, `evals/` or test fixtures.
No expected workbook values, audit answers or filename-specific exceptions are supplied
to production readers. See the [API flow](api.md).

One service process per data directory; this is not a distributed queue. Provider delivery
journals prevent uncertain automatic retries. See [committee](committee.md) and
[audit](corpus-audit.md).
