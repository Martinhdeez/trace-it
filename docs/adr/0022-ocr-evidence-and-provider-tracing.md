---
status: accepted
---

# Preserve OCR evidence and trace each provider operation

## Context

The production API already reads native PDFs, scanned invoices and workbooks, but
the original demo still bypassed this pipeline. Existing `vision`, `text_judge`
and `focused_read` spans showed stages without distinguishing a remote request
from a saved response. Re-uploading a document could also make the evidence API
display a new reading while the instance kept its original symbols.

ADR 0010 proposed two generic LLM readings. The implemented invoice adapter uses
local OCR and bounded visual checks instead. This ADR supersedes that proposal
and records the implemented contract, including its limits. ADR 0018 still owns
the shared event schema and OpenTelemetry export.

## Alternatives considered

- Two LLM calls for every document: a simple comparison, but unnecessary remote
  work for native PDFs and no guarantee of independent errors.
- A visual model's answer as the accepted reading: higher apparent coverage,
  but unsupported identifiers can reach payment rules.
- Stage timings alone, or hosted telemetry alone: insufficient to distinguish
  billable attempts from replay or to recover the audit without that service.
- Native parsing, two local OCR readers, selective visual checks, and our own
  provider journal and spans (chosen).

## Decision

1. Native text is used first. Pages requiring OCR use both pinned local readers.
   Missing or conflicting readings can invoke the configured visual reader;
   bounded crops and scale changes may recheck critical fields. Repeating one
   reader at another scale is not an independent vote. Gemini is used unless a
   complete generic visual endpoint/model pair is configured; partial generic
   settings must not block configured Gemini or mislabel its provenance.
2. The invoice-specific adapter stays in `features/ingestion`. NIF, IBAN and
   purchase-order `value` require the current native/corroboration policy;
   unconfirmed alternatives remain `proposed_value` and candidates. Other fields
   retain the documented best-reading policy and verification metadata. Jev
   recommends existing textual candidates and supplies no visual vote. Neither
   reader nor validator decides payment; the deterministic rules do.
3. Source mismatches select field names for at most one extra extraction. Expected
   master values are never supplied to the readers. Store both extraction IDs,
   candidates, coordinates, options, model manifests and source snapshot IDs.
4. Initial attachment and a stale pending-instance refresh apply readings to an
   instance. Upload and re-extraction check the request, sources and symbol schema;
   unchanged evidence is reused without another extraction event. A pending refresh
   appends `extract_document` and updates symbols together. Decided duplicates reuse
   their applied evidence; explicit re-extraction returns 409. The document endpoint
   excludes legacy non-applied duplicate extractions.
   Original events and decisions remain intact. See the
   [cache and refresh contract](../ingestion/cache-and-quality.md).
5. `make demo` uses the production workbook/PDF, ERP sync, run and export APIs.
   It keeps extraction evidence and uses the same decision export policy as the
   application, including optional human review. It does not write test symbols
   directly into the database.
6. Every production remote reader call goes through the content-addressed provider
   journal and a nested `provider_call` span. The span carries provider, model,
   operation, request fingerprint, inherited process/trace/parent links, duration,
   outcome and available usage. Image transcription and text selection remain
   separate operations. Parent spans retain page, reader and focused field.

   | Field | Meaning |
   |---|---|
   | `journal_hit` | An existing journal record was found, complete or uncertain |
   | `network_attempted` | Execution reached the outbound request; delivery or billing is not guaranteed |
   | `network_succeeded` | The request returned a usable response accepted by the reader |
   | `outcome` | `success`, `replay`, `error`, or `blocked_uncertain` |
   | `http_status_code` | HTTP response status when a response arrived, including rejected responses |
   | `input_tokens`, `output_tokens`, `total_tokens` | Nonnegative integer usage reported by the provider, when available |
   | `error_type`, `error` | Exception class and a fixed safe description, without provider bodies |

   A completed journal response is replayed without another request. An incomplete
   or uncertain record blocks automatic resubmission. A definite HTTP refusal (4xx or
   503, e.g. a 429 rate limit) delivered nothing: it is journaled `refused` and the next
   call tries again (2026-09-19, [resilience](../resilience.md)). A received response can
   report usage even if its content is subsequently rejected. Secrets, raw images,
   transcripts and request payloads do not enter these provider spans; the protected
   local journal and document evidence retain the material needed for reproduction.
7. Extraction-cache hits link `cached_from_extraction_id` to the original result.
   The extraction span records result ID, pipeline version, options, OCR manifests,
   warnings and per-request call counts. A cache hit does not create provider calls.
8. `GET /processes/{id}/metrics` adds `providers`, grouped by provider/model/operation:
   attempts, network requests, completed replays, errors and reported input/output
   tokens. Token totals include only network attempts, never replayed historical
   usage. Existing agent `llm` metrics remain separate. These are reported usage
   counters, not a complete invoice from the provider: unreported usage is unknown.
   `provider_call` belongs to the ingestion monitoring plane, including its health
   and live event stream. The ingestion plane exposes the same `providers` totals
   through its process and global endpoints; agent `llm_run` remains in `agents`.

## Consequences

- The instance trace now connects the PDF to local readers, remote requests or
  replay, stored readings, symbols and decisions. Decided evidence remains stable
  after a duplicate upload, even when it requests different extraction options;
  stale pending evidence refreshes together with its symbols.
- Pipeline `invoice-v2.2.0+xlsx-v1.3` fingerprints extraction dependencies and local
  reader inputs separately, so policy changes reuse compatible OCR transcripts
  while changed models or preprocessing trigger new readings. It retains the
  field-reading acceptance policy. Historical v2.1.4 corpus results
  in `docs/ingestion/focused-verification.md` remain historical measurements.
- No new schema migration, hosted observability dependency or model key is needed.
  Journal responses from older text-only generic visual calls remain readable.
- ADR 0018's limits still apply: an interrupted process can lose buffered spans,
  and an unavailable audit database can drop spans. The journal can survive that
  interruption, but this is not a transactional guarantee covering a remote call.
- Alternative fal.ai readers require their own adapter and measured evaluation;
  they are not enabled by this change (ADR 0023).

## Evidence

- `ingestion/tests/test_provider_tracing.py`: each production provider, replay,
  uncertain-delivery blocking, error redaction and token reporting with mocked HTTP.
- `ingestion/tests/test_process_api.py`: PostgreSQL-backed invoice journey with a
  mocked visual provider, cache and journal replay, immutable attached evidence.
- `ingestion/tests/test_payment_api.py`: both local reader interfaces, document
  symbols, sandboxed payment rules and export through the production API.
- `ingestion/tests/test_demo_run.py`: HTTP workflow, pending retry, preservation of
  decided instances, failed upload and reviewed decision metadata.
- `traces/tests/test_api.py`: provider aggregates count replay separately from
  network usage; decision review tests align instance traces with export.

No new paid model calls or claims of improved recognition accuracy support this
change. Local OCR and golden checks are reported separately from mocked providers.

## Related

ADRs 0002, 0008, 0010 (superseded), 0016, 0018, 0021 and 0023.
