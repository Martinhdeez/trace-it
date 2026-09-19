# Process-driven document extraction

Each process PDF upload loads the current symbols and enforced (`active` and `blocked`)
rules from PostgreSQL. The plan retains **every declared symbol**, including optional
audit fields and names accessed through computed variables. Static analysis also reports
literal rule references and warns about undeclared symbols. It does not invent a type or
meaning for a field missing from the process definition. No LLM call is needed to discover
the declared field contract.

Inspect it with `GET /processes/{id}/extraction-plan` and `X-User-Id`. The response includes
fields, rule dependencies, warnings and a content fingerprint. A change in a local rule
file takes effect after the definition is loaded and the new rule is activated through
the existing rule lifecycle; this is not a filesystem watcher.

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
New rules still follow compilation and activation. Definition changes apply to the next
upload or `POST /instances/{id}/extract` without restarting. Existing instances are not
automatically re-extracted. Duplicate uploads do not replace attached evidence, and only
PENDING instances can be re-extracted. Historical decisions remain immutable.

## Invoice compatibility and evidence

The existing invoice-payment symbol contract selects the original invoice adapter. Its
standard symbols, parser, identifier verification and source checks keep their existing
behavior; their extraction hints do not override that adapter. Newly declared symbols
are extracted as an extension. Other processes with symbols use the generic reader.
Processes without symbols and standalone `/v1/extractions` keep their original behavior.

The generic reader first matches labels in native text or OCR. If configured, the existing
Gemini or OpenAI-compatible vision endpoint can locate remaining fields from their
descriptions. It must return exact quotations with line identifiers; values and types are
validated locally. It never evaluates rules or chooses an outcome. `vlm: false` disables
this model assistance as well as visual transcription. No new provider calls are added
to the unchanged invoice pack.

Native text and sufficiently confident local OCR can supply accepted values. Visual
model text alone remains a proposal. Conflicting, invalid and uncertain readings stay
null, with candidates and provenance retained. A required null symbol escalates when the
deterministic engine runs. Semantic interpretation remains model-assisted extraction,
not a guarantee that every arbitrary layout or description can be read. Give explicit
labels when possible. The semantic request is bounded to 50 unresolved fields, 200 lines
and 20,000 transcript characters; information outside those bounds remains missing.
Visual field search stops once every target has a value or a proposal; a proposal stays
unverified. A `text` source still requests transcription of each page that needs it.

Each generic result records `data.extraction_plan`, `data.schema_fields`, and the plan
fingerprint. Invoice ingestion events also record the plan while preserving the existing
invoice result format. Origins continue to use `document:<extraction_id>`.

## Cost and cache behavior

1. Current database rows are read on each request. A bounded, 128-entry process-local
   cache reuses rule analysis when the actual code, status and symbol metadata match.
   It checks actual code content, even if a stored rule hash was not updated. After a
   restart, deterministic analysis runs once again; it does not call a provider.
2. Document results use the PDF, reader configuration and field schema as their cache
   identity. A rule-only change reuses the reading and records the current plan in the
   new result. Changing a field's description, labels, type or source invalidates it.
3. Provider calls have a persistent journal keyed by requested fields, transcript,
   model and prompt. Rule hashes are excluded, so unchanged requests replay without
   another network call. Failed or uncertain provider operations retain the existing
   journal's no-automatic-retry behavior.

Keeping all declared symbols covers computed rule references conservatively. Optional
fields can therefore also trigger reading or model assistance. Mark data that should not
be sought in a PDF with `source: "none"` to avoid that work.

Before serving this version, apply the additive database migration from `backend`:

```bash
uv run alembic upgrade head
```

Migration `0011` adds nullable JSON extraction metadata to symbols. Existing definitions
need no changes. No new provider key is required: the reader uses `GEMINI_API_KEY` with
`TRACEPAY_GEMINI_MODEL`, or `TRACEPAY_VLM_URL`, `TRACEPAY_VLM_MODEL` and the optional
`TRACEPAY_VLM_API_KEY`, as the existing visual reader does.
