# Process models and execution effort

Managers edit **Models and execution effort** on a process page. Choose a preset,
preview its replacement values, and apply it to the editor. Every model and effort
setting remains editable. Manual edits mark the configuration **Custom**.

Save the draft, review its complete contents and validation, and publish with a reason.
Publication includes any other changes already in that process draft. Published settings
stay fixed until another version is published. Changing a use-case default or a deployment
preset does not update a published process. No database migration is needed: the existing
version snapshot holds the configuration.

## Settings

Each agent role has its own model, ordered fallback models, request timeout, output
validation retries, request limit, provider model parameters, and agent effort limits.
The roles are discovery, normalizer, compiler, tester, assistant, decision reviewer, and
learner. Provider-specific reasoning parameters go in `model_settings`; the selected
provider must support them. Compiler `max_attempts`, tester `max_reviews`, and tester
`min_tests` are the existing compilation effort controls.

Document extraction selects the primary and verification OCR weight directories,
visual model, and text judge. OCR, secondary OCR, focused identifier verification,
and source-triggered verification can be enabled separately. DPI, visual and judge
request timeouts, and output token limits are editable. Judge output tokens apply to
the compatible/local adapter; Jev owns its response format. Focused verification needs
OCR and a visual model. Source verification additionally needs focused verification.

A disabled reader stays disabled even when a provider key exists. Reducing verification
can leave more fields unresolved; it never changes evidence acceptance rules. Optional
decision review has a separate enable switch, guidance and overall deadline. Disagreements
still require human approval. Rule findings and engine decisions remain deterministic.

## Local and hosted models

Agents retain the existing `provider:model` identifiers. `local:model-name` selects the
deployment's OpenAI-compatible local server. Set `TRACE_LOCAL_BASE_URL`, default
`http://localhost:11434/v1`; set `LOCAL_LLM_API_KEY` only if the server requires a key.
The endpoint is copied into the process configuration and can be edited before publication.
In containers, use an address reachable from the backend container.
For a deployment without the evaluated cloud OCR committee, set
`TRACEPAY_OCR_PROFILE=experimental` to opt out of its existing startup check.
This deployment check is separate from process presets.

Visual readers support `local:model`, `compatible:model`, and `gemini:model`.
Text judges support `local:model`, `compatible:model`, and `jev:model`.
A blank reader model disables that step. Compatible readers use the process's compatible
endpoint, seeded from `TRACEPAY_VLM_URL`, and `TRACEPAY_VLM_API_KEY`. Gemini and Jev use
`GEMINI_API_KEY` and `TYPESAFE_API_KEY`. Credentials never enter process snapshots.

Local-only mode requires every agent model, fallback, visual reader and text judge to
use `local:` or be disabled where allowed. It sends model calls only to the designated
local server; the deployment operator is responsible for that server's own routing.
It does not disable configured ERP/source connectors. A local provider failure never
switches to a hosted provider. Local OCR uses installed weights without downloading models.

## Presets

Presets are editable recipes, not automatic model rankings or cost guarantees:

| Preset | Agent timeout / retries | Compiler attempts | Extraction |
| --- | --- | --- | --- |
| Lowest cost | 60s / 0 | 1 | Local OCR pair, no visual or text judge, no focused/source verification |
| Fastest | 15s / 0 | 1 | Same reading stages, shorter deadlines |
| Balanced | 60s / 2 | 3 | Existing reader choices, focused and source verification |
| Highest quality | 120s / 4 | 5 | Existing reader choices, focused/source verification, 300 DPI |

Request limits are retries plus one. Presets retain the supplied agent models unless the
deployment provides model mappings in `TRACE_EXECUTION_PRESETS`. This avoids assigning
uninstalled models or claiming an unmeasured model is cheapest or fastest. For example:

```json
{
  "fastest": {
    "agents": {
      "assistant": {"model": "local:your-fast-model"},
      "compiler": {"model": "helmcode:your-code-model", "fallback_models": []}
    }
  },
  "highest_quality": {
    "extraction": {"vision_model": "local:your-vision-model"}
  }
}
```

Use model names available in your deployment. Set the variable to this JSON object.
Preset overrides replace the supplied fields; they do not change domain instructions
unless explicitly included. Local-only validation also applies to preset previews.
A preset with hosted models cannot be applied to a local-only configuration unchanged.

## API and packs

- `GET /processes/{id}/execution` returns editable settings, preset previews, the current
  draft revision and published version ID. It does not create a draft.
- `PUT /processes/{id}/draft` accepts `execution` and `expected_revision`. Send the complete
  settings returned by GET with the desired edits. An omitted execution field retains the
  existing configuration. Null is rejected.
- The existing `/draft/validate` and `/draft/publish` endpoints validate and publish the
  whole candidate. Rollback uses the existing version restore flow.
- A process pack may contain the same `execution` object.
- Discovery accepts execution settings when starting a session. `PUT
  /process-drafts/{id}/execution` accepts `{revision, execution}` and invalidates prior
  reviews and compilation. Discovery pins its settings before making model calls and
  carries them into the published process. Paired reviewer previews use the selected
  draft models for both configurations, including when the previous version used cloud models.

Agent settings remain in `snapshot.agents`; extraction, endpoints, local-only and the
preset label live in `snapshot.execution`. Runtime never looks up a preset by name.
Legacy versions without execution settings retain their extraction behavior; editing
such a version captures explicit settings in its new draft without rewriting history.

## Verification and tracing

Agent traces record the effective configuration hash, requested chain, answering model,
parameters, tokens, latency and provider cost where available. Extraction traces record
an execution hash; cache keys include the reader identities and effective extraction
options. Configured extraction readers share storage and worker capacity without mutating
another process's settings.

Publication validation reruns deterministic rules against saved symbols. It does not
re-extract original documents or prove that a new model improves quality. Use the existing
compiler and OCR evaluation tools to measure changes before choosing deployment mappings.
No automatic optimizer or hard monetary budget is implemented.

OCR mode (`local`, `api`, or `hybrid`) is pinned with the process settings. `local`
mode uses installed OCR only; local server vision calls use `hybrid` or `api` mode.
The selected reader can also use `helmcode:qwen3.6` or `helmcode:gemma4` with the
server's `HELMCODE_API_KEY`. Versioned settings select readers explicitly and do
not inherit additional deployment provider fallbacks. Legacy versions retain
existing deployment behavior until execution settings are saved.
