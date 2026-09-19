# Process-driven document extraction

Each process PDF upload loads symbols and enforced (`active` and `blocked`) rules
from the active published version in PostgreSQL. Before the first publication it
uses the live definition tables. The plan retains **every declared symbol**, including optional
audit fields and names accessed through computed variables. Static analysis also reports
literal rule references and warns about undeclared symbols. It does not invent a type or
meaning for a field missing from the process definition. No LLM call is needed to discover
the declared field contract.

Inspect it with `GET /processes/{id}/extraction-plan` and `X-User-Id`. The response includes
fields, rule dependencies, warnings and a content fingerprint. A change in a local rule
file takes effect after the definition is loaded and its new version is published
through the existing process lifecycle; this is not a filesystem watcher.

## From an agent proposal to a document value

1. In a discovery session, use `revise` to propose the new symbol and rule together.
   `discuss` answers questions without editing the draft. The symbol declares its name,
   type, description, requirement and optional extraction hints; code alone cannot
   introduce a usable field. The compiler receives the proposed schema and checks
   literal references against it.
2. Review the setup, rules and examples, then prepare the draft. Compilation and the
   historical preview use saved evidence. They do not read PDFs again. Historical cases
   missing a newly introduced required field are reported as not evaluable with available
   historical evidence. That absence alone does not block publication or count as a
   successful validation. Keep the field required when the policy requires it, and include
   proposed-schema examples with the value present and absent.
3. A manager publishes the prepared version. Its snapshot in PostgreSQL is the runtime
   contract for both extraction and rule execution, including the selected models and
   execution effort. Unpublished proposal changes have no effect on active extraction.
4. The next upload, pending duplicate upload or explicit pending re-extraction reads
   that published contract. Deterministic analysis and content fingerprints discover
   the fields without a separate LLM request. Schema changes refresh stale readings;
   unchanged readings and provider requests can be reused.
5. Only accepted, typed readings enter `Instance.symbols`. Rules receive their plain
   values; the engine also receives evidence verification and scan provenance. A missing
   required value or unconfirmed required scan value leads to human review.

The process execution editor is described in [Models and execution effort](process-execution.md).
Changing `.env` remains a deployment change requiring restart; publishing a process
configuration takes effect on the next request without one.

## Historical coverage when the schema grows

Publication compares proposed symbol names with the active published schema. Only newly
introduced required symbols qualify for the historical-evidence exception; making an
existing optional symbol required keeps the normal validation checks.

All rules are still attempted in the validation sandbox. Actual reads of unavailable new
fields are identified separately from ordinary exceptions, including reads from other
instances. Results of rules that can run on the saved evidence remain in the report.
Code errors, invalid outputs, unknown symbols, missing existing required data and conflicts
on evaluable cases still block publication. There is no general exception for `MISSING_DATA`,
`KeyError` or `TypeError`.

A historical case that needs unavailable new data is excluded from unchanged, changed and
conflicting decision counts. It is listed in `not_evaluable`, with its missing symbols and
the rules that did and did not yield evaluable results. `coverage` reports total historical
cases, evaluated cases, not-evaluable cases, and how many incomplete cases retained some
rule results (`partial`) or none (`none`). Zero or partial historical coverage is visible
in the publication panel; it is not a claim that the proposed policy passed on old evidence.

When a published schema gains required symbols, the proposed schema must have acceptance
examples covering every new required field both present and absent, even with no historical
cases. Initial bootstrap publication keeps its existing validation flow. Discovery
proposals carry those examples; manual process drafts can supply `acceptance_examples`.
Present examples must include all required fields; an absent example isolates each new
missing field while retaining the other required values. The examples execute the proposed
rules and required-field policy, and stored rule tests still run. A new document missing
the field must produce the configured human-review
outcome. Tests and examples establish behavior on their inputs; they do not prove arbitrary
untested rule branches correct.

After publication, new uploads and pending re-extractions use the new required schema.
No historical PDF is re-extracted automatically, and no historical decision or evidence
is edited. See [ADR 0030](adr/detail/0030-report-partial-history-for-new-symbols.md).

## Configure a field

Add a symbol to the process definition, for example:

```json
{
  "name": "expires_on",
  "type": "date",
  "description": "The expiry date printed on the document",
  "required": true,
  "extraction": {
    "labels": ["Expiry date", "Fecha de caducidad"],
    "source": "document"
  }
}
```

`extraction` is optional. Labels supplement the symbol name and its human-readable form.
Deterministic matches require a separator (`:`, `#` or `=`); shared labels stay ambiguous.
Its `source` can be `document` (default), `filename`, `text` (whole transcript), or `none`
(leave null, for data supplied elsewhere). Without explicit metadata, `file_id` uses the
filename and `free_text` uses the transcript. Document types are `text`/`string`, `number`,
`integer`, `date` and `boolean`. Numbers remain canonical decimal strings for the existing
rule contract; booleans become JSON booleans. Unsupported types stay null with a warning.

Reload the whole definition with `POST /processes/definition`, or from `backend`:

```bash
uv run python -m app.cli load ../processes/my-process.json
```

The loader upserts symbols; omitting an existing symbol does not delete it. Set its
extraction source to `none` to stop reading it, and update any rules that require it.
New rules still follow compilation and publication. Published changes apply to the next
upload or `POST /instances/{id}/extract` without restarting. Unpublished edits cannot
alter an active version. Existing instances are not automatically re-extracted.
Pending duplicate uploads refresh stale evidence and reuse unchanged readings; decided
duplicates retain their attached evidence. Only PENDING instances can be re-extracted.
Historical decisions remain immutable.

## Invoice compatibility and evidence

The existing invoice-payment symbol contract selects the original invoice adapter. Its
standard symbols, parser, identifier verification and source checks keep their existing
behavior; their extraction hints do not override that adapter. Newly declared symbols
are extracted as an extension. Other processes with symbols use the generic reader.
Processes without symbols and standalone `/v1/extractions` keep their original behavior.

The generic reader first matches labels in native text or OCR. If configured, the existing
Gemini, Helmcode or OpenAI-compatible provider can locate remaining fields from their
descriptions. It must return exact quotations with line identifiers; values and types are
validated locally. It never evaluates rules or chooses an outcome. `vlm: false` disables
this model assistance as well as visual transcription. No new provider calls are added
to the unchanged invoice pack.

Native text and sufficiently confident local OCR can supply accepted values. A single
visual model supplies a proposal; in API mode two distinct visual models can corroborate
a value. Conflicting, invalid and uncertain readings stay
null, with candidates and provenance retained. A required null symbol escalates when the
deterministic engine runs. Semantic interpretation remains model-assisted extraction,
not a guarantee that every arbitrary layout or description can be read. Give explicit
labels when possible. The semantic request is bounded to 50 unresolved fields, 200 lines
and 20,000 transcript characters; information outside those bounds remains missing.
Visual field search stops once every target has a value or a proposal; a proposal stays
unverified. A `text` source still requests transcription of each page that needs it.

Each generic result records `data.extraction_plan`, `data.schema_fields`, and the plan
fingerprint. Invoice ingestion events also record the plan while preserving the existing
invoice result format. Native field evidence uses `document:<extraction_id>`; fields read
only through OCR or vision use `scan:<extraction_id>:<verification>` unless verified.
This also applies to a scanned page inside a mixed PDF and to additional invoice fields.
Filename and transcript metadata retain document origins. The scan policy in ADR 0025
therefore reaches the engine for dynamic fields as well as invoice fields.
Generic provenance also records the execution hash, cache key and effective schema mapper
configuration without credentials; extraction spans include the same execution hash.

The schema mapper uses the process's selected visual provider and endpoint. For Helmcode,
an explicitly selected Helmcode text judge supplies its text model; otherwise mapping uses
the selected visual model. A process's disabled readers or local-only routing cannot inherit
cloud fallbacks from deployment keys. Mapping uses the visual timeout and at most
`min(1500, vision_max_tokens)` output tokens. `secondary_ocr: false` skips the secondary
recognizer and its evidence when interpreting generic fields; primary OCR remains available.

## Cost and cache behavior

1. The active version pointer and its snapshot are read on each request (live tables
   before the first publication). A bounded, 128-entry process-local
   cache reuses rule analysis when the actual code, status and symbol metadata match.
   It checks actual code content, even if a stored rule hash was not updated. After a
   restart, deterministic analysis runs once again; it does not call a provider.
2. Document results use the PDF, reader configuration and field schema as their cache
   identity, including effective schema mapping settings. A rule-only change reuses the
   reading and records the current plan in the new result. Changing a field's description,
   labels, type or source invalidates it.
3. Provider calls have a persistent journal keyed by requested fields, transcript,
   model and prompt. Rule hashes are excluded, so unchanged requests replay without
   another network call. Timeouts, dropped connections and rejected successful
   responses remain blocked as uncertain deliveries. Definite HTTP refusals
   (4xx or 503) can be attempted on a later extraction after provider cooldown.

The deployment option `TRACEPAY_OCR_FORCE_RECOMPUTE=1` explicitly bypasses reading,
provider-journal and pending-evidence reuse. Its default is off. It does not authorize
rewriting historical decisions or turn publication previews into OCR runs.

Keeping all declared symbols covers computed rule references conservatively. Optional
fields can therefore also trigger reading or model assistance. Mark data that should not
be sought in a PDF with `source: "none"` to avoid that work.

Before serving this version, apply the additive database migration from `backend`:

```bash
uv run alembic upgrade head
```

Migration `0014` adds nullable JSON extraction metadata to symbols. Existing definitions
need no changes. No new provider key is required: the reader can use `GEMINI_API_KEY` with
`TRACEPAY_GEMINI_MODEL`, or `TRACEPAY_VLM_URL`, `TRACEPAY_VLM_MODEL` and the optional
`TRACEPAY_VLM_API_KEY`, as the existing visual reader does. Helmcode and execution modes
are described in the [provider guide](ingestion/providers-and-modes.md).
