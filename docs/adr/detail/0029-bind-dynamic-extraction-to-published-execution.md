---
status: accepted
---

# Bind dynamic field extraction to published execution settings and evidence

## Context

Discovery agents propose symbols and compile rules into a manager-approved process
version. Ingestion already reads that snapshot to determine which fields to extract.
Process-specific readers, however, retained the deployment's schema mapper, generic
PDF extraction ignored the secondary OCR switch, and dynamic symbols lost scan origin
before reaching the engine. These gaps broke the contract between configuration,
extraction cost and the scan decision policy.

## Alternatives considered

- Infer a schema with an LLM whenever a rule changes: flexible, but duplicates the
  typed contract already approved in the process and adds cost and ambiguity.
- Retain one deployment mapper for every process: simple, but can select a cloud
  provider for a process configured to use local models.
- Bind each reader to the published process settings: preserves the existing version
  lifecycle, makes provider routing explicit and allows reuse of unchanged evidence.

## Decision

1. Keep declared symbols in the published snapshot as the extraction contract.
   Deterministic rule analysis reports literal dependencies; all declared symbols
   remain available for computed references. No discovery API call is needed at ingestion.
2. Build the schema mapper with the same effective settings as the process's visual
   reader. Respect its endpoint, timeout and output budget. A Helmcode text model is
   used only when explicitly selected for that process; otherwise use its vision model.
   Preserve the mapper's existing 1,500-token ceiling.
3. Include effective mapper settings in extraction identity and respect the secondary
   OCR switch before reading or reusing its lines. Disabled providers stay disabled;
   local-only model routing cannot fall back to deployment cloud keys.
4. Preserve field-level native versus OCR/vision provenance when producing symbols.
   Pass scan verification to the existing engine gates, including additional invoice
   fields and fields read from scanned pages in mixed PDFs. Metadata is not an OCR vote.
5. Apply published changes on the next upload or explicit pending re-extraction.
   Drafts remain inert. Repeated unchanged requests reuse evidence and report no new
   reader calls. Existing decisions and attached historical evidence remain immutable.

## Consequences

The original invoice adapter and its default extraction policy remain in place. Generic
scan fields now reach the same conservative review gates; some cases previously decided
without those gates will require review on future executions. Previous decisions are not
rewritten. Publication previews still evaluate saved symbols, so introducing a required
field can be blocked by missing historical evidence. This change does not automate
historical re-extraction or weaken publication validation.

## Evidence

- `ingestion/tests/test_execution.py`: isolated process mapping, local provider routing,
  request limits and cache identity, with mocked HTTP and no provider credentials.
- `ingestion/tests/test_schema_pdf.py`: primary/secondary effort and reuse of base lines.
- `ingestion/tests/test_schema_provenance.py`: extraction through the engine's scan gates.
- `ingestion/tests/test_schema_api.py`: scripted discovery and compilation, publication,
  new-field extraction, deterministic decision, unchanged-read reuse and preserved history.
- Existing invoice, native golden and PostgreSQL integration suites remain the regression
  checks for the default evaluated case.

## Related

ADRs 0001, 0008, 0024, 0025 and 0027; the [dynamic extraction guide](../../dynamic-extraction.md)
and [process execution guide](../../process-execution.md).
